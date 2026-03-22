#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台适配器模块 v2.1
====================
为每个投诉平台编写登录/注册适配器。
每个适配器实现完整的闭环流程：
  1. 检测是否已登录
  2. 自动登录（用户名+密码）
  3. 验证登录是否成功
  4. 如登录失败（无账号），自动注册
  5. 注册成功后保存账号密码
  6. 注册后自动登录并确认成功
  7. 需要手动接管时（验证码等），暂停等待用户操作
  8. 最终返回明确的登录成功/失败状态
"""

import time
import random
import string
from typing import Optional, Dict, Tuple, Callable


class LoginResult:
    """登录/注册操作的结果"""
    SUCCESS = "success"
    NEED_CAPTCHA = "need_captcha"
    NEED_SMS_CODE = "need_sms_code"
    NEED_MANUAL = "need_manual"
    NEED_REGISTER = "need_register"
    WRONG_PASSWORD = "wrong_password"
    ACCOUNT_NOT_FOUND = "account_not_found"
    NETWORK_ERROR = "network_error"
    ALREADY_LOGGED_IN = "already_logged_in"
    REGISTER_SUCCESS = "register_success"
    UNKNOWN_ERROR = "unknown_error"

    def __init__(self, status: str, message: str = "", need_takeover: bool = False,
                 registered_username: str = "", registered_password: str = ""):
        self.status = status
        self.message = message
        self.need_takeover = need_takeover
        # 注册成功时携带新账号信息
        self.registered_username = registered_username
        self.registered_password = registered_password

    def is_success(self) -> bool:
        return self.status in (self.SUCCESS, self.ALREADY_LOGGED_IN)

    def is_register_success(self) -> bool:
        return self.status == self.REGISTER_SUCCESS


def generate_password(length: int = 12) -> str:
    """生成随机安全密码"""
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%"
    # 确保每种字符至少一个
    pwd = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
        random.choice(special),
    ]
    all_chars = lower + upper + digits + special
    pwd += [random.choice(all_chars) for _ in range(length - 4)]
    random.shuffle(pwd)
    return "".join(pwd)


class BasePlatformAdapter:
    """
    平台适配器基类。
    所有平台适配器都继承此类，并实现完整的注册->登录->确认闭环。
    """

    PLATFORM_NAME = ""
    LOGIN_URL = ""
    REGISTER_URL = ""
    HOME_URL = ""
    NEEDS_LOGIN = True

    # 最大重试次数
    MAX_LOGIN_RETRIES = 3
    MAX_REGISTER_RETRIES = 2

    def __init__(self, browser_engine):
        self.browser = browser_engine
        self._account_save_callback: Optional[Callable] = None

    def set_account_save_callback(self, callback: Callable):
        """
        设置账号保存回调。
        callback(platform_name, username, password) -> None
        注册成功后自动调用此回调保存账号。
        """
        self._account_save_callback = callback

    def _save_account(self, username: str, password: str):
        """通过回调保存账号"""
        if self._account_save_callback:
            self._account_save_callback(self.PLATFORM_NAME, username, password)

    # ---- 核心闭环方法 ----

    def login_or_register(self, username: str = "", password: str = "",
                          phone: str = "", email: str = "",
                          default_password: str = "") -> LoginResult:
        """
        完整的登录/注册闭环。
        流程：
        1. 检测是否已登录 -> 如果是，直接返回成功
        2. 如果有账号密码，尝试自动登录
        3. 登录成功 -> 返回成功
        4. 登录失败（账号不存在） -> 尝试自动注册
        5. 注册成功 -> 保存账号 -> 用新账号登录
        6. 登录成功 -> 返回成功
        7. 任何步骤需要手动接管 -> 返回 need_takeover，等待用户操作后重新验证
        """
        self.browser._report_status(f"[{self.PLATFORM_NAME}] 开始登录/注册流程...")

        # 步骤1：检测是否已登录
        if self.check_logged_in():
            self.browser._report_status(f"[{self.PLATFORM_NAME}] 已经登录")
            return LoginResult(LoginResult.ALREADY_LOGGED_IN, "已经登录，无需重复操作")

        # 步骤2：如果有账号密码，尝试登录
        if username and password:
            for attempt in range(1, self.MAX_LOGIN_RETRIES + 1):
                self.browser._report_status(
                    f"[{self.PLATFORM_NAME}] 尝试登录 (第{attempt}次)...")
                result = self.auto_login(username, password)

                if result.is_success():
                    # 登录成功，验证一下
                    if self._verify_login_success():
                        self.browser._report_status(
                            f"[{self.PLATFORM_NAME}] 登录成功！")
                        return LoginResult(LoginResult.SUCCESS, "登录成功")
                    else:
                        self.browser._report_status(
                            f"[{self.PLATFORM_NAME}] 登录后验证失败，重试...")
                        continue

                if result.need_takeover:
                    # 需要手动接管（验证码等），返回让主程序处理
                    return result

                if result.status == LoginResult.ACCOUNT_NOT_FOUND:
                    # 账号不存在，跳出登录循环，进入注册流程
                    self.browser._report_status(
                        f"[{self.PLATFORM_NAME}] 账号不存在，将尝试注册...")
                    break

                if result.status == LoginResult.WRONG_PASSWORD:
                    self.browser._report_status(
                        f"[{self.PLATFORM_NAME}] 密码错误")
                    # 密码错误不重试，直接返回
                    return result

                if result.status == LoginResult.NETWORK_ERROR:
                    self.browser._report_status(
                        f"[{self.PLATFORM_NAME}] 网络错误")
                    return result

                # 其他错误，重试
                self._safe_sleep(2)

        # 步骤3：尝试注册
        if phone:
            reg_password = default_password or generate_password()
            self.browser._report_status(
                f"[{self.PLATFORM_NAME}] 开始自动注册...")

            for attempt in range(1, self.MAX_REGISTER_RETRIES + 1):
                self.browser._report_status(
                    f"[{self.PLATFORM_NAME}] 注册尝试 (第{attempt}次)...")
                reg_result = self.auto_register(phone, email, reg_password)

                if reg_result.is_register_success():
                    # 注册成功！保存账号
                    new_user = reg_result.registered_username or phone
                    new_pass = reg_result.registered_password or reg_password
                    self._save_account(new_user, new_pass)
                    self.browser._report_status(
                        f"[{self.PLATFORM_NAME}] 注册成功，账号已保存，正在登录...")

                    # 用新账号登录
                    login_result = self.auto_login(new_user, new_pass)
                    if login_result.is_success() or self._verify_login_success():
                        self.browser._report_status(
                            f"[{self.PLATFORM_NAME}] 注册后登录成功！")
                        return LoginResult(LoginResult.SUCCESS, "注册并登录成功")
                    elif login_result.need_takeover:
                        return login_result
                    else:
                        self.browser._report_status(
                            f"[{self.PLATFORM_NAME}] 注册后登录失败: {login_result.message}")
                        return login_result

                if reg_result.need_takeover:
                    # 注册需要手动接管（短信验证码等）
                    # 返回特殊结果，让主程序处理接管后再回来验证
                    reg_result.registered_username = phone
                    reg_result.registered_password = reg_password
                    return reg_result

                # 注册失败，重试
                self._safe_sleep(2)

        # 步骤4：无法自动完成，需要手动
        self.browser._report_status(
            f"[{self.PLATFORM_NAME}] 无法自动登录/注册，需要手动操作")
        return LoginResult(
            LoginResult.NEED_MANUAL,
            "无法自动完成登录/注册，请手动操作",
            need_takeover=True,
        )

    def post_takeover_verify(self, username: str = "", password: str = "") -> LoginResult:
        """
        手动接管完成后的验证。
        检查用户手动操作后是否已成功登录。
        如果登录成功且有新账号信息，保存账号。
        """
        self._safe_sleep(2)

        if self._verify_login_success():
            # 登录成功，保存账号
            if username and password:
                self._save_account(username, password)
            self.browser._report_status(
                f"[{self.PLATFORM_NAME}] 手动操作后验证：登录成功！")
            return LoginResult(LoginResult.SUCCESS, "登录成功")

        # 再等一下重试
        self._safe_sleep(3)
        if self._verify_login_success():
            if username and password:
                self._save_account(username, password)
            self.browser._report_status(
                f"[{self.PLATFORM_NAME}] 手动操作后验证：登录成功！")
            return LoginResult(LoginResult.SUCCESS, "登录成功")

        self.browser._report_status(
            f"[{self.PLATFORM_NAME}] 手动操作后验证：未检测到登录成功")
        return LoginResult(LoginResult.UNKNOWN_ERROR, "未检测到登录成功状态")

    # ---- 子类需要实现的方法 ----

    def check_logged_in(self) -> bool:
        """检测当前是否已登录。子类实现。"""
        return False

    def auto_login(self, username: str, password: str) -> LoginResult:
        """自动登录。子类实现。"""
        return LoginResult(LoginResult.UNKNOWN_ERROR, "该平台暂不支持自动登录")

    def auto_register(self, phone: str, email: str, password: str = "") -> LoginResult:
        """自动注册。子类实现。"""
        return LoginResult(LoginResult.UNKNOWN_ERROR, "该平台暂不支持自动注册")

    def _verify_login_success(self) -> bool:
        """
        验证登录是否真正成功。子类应覆盖此方法。
        默认实现：检查页面上是否还有"登录"按钮。
        """
        try:
            self._safe_sleep(1)
            source = self.browser.get_page_source()
            url = self.browser.get_current_url()
            if not source:
                return False
            # 通用判断：如果不在登录页，且页面没有明显的登录表单
            if "login" in url.lower() or "signin" in url.lower():
                return False
            return True
        except Exception:
            return False

    def navigate_to_complaint(self) -> bool:
        """导航到投诉页面。子类实现。"""
        if self.HOME_URL:
            return self.browser.navigate(self.HOME_URL)
        return False

    def _safe_sleep(self, seconds: float):
        """安全等待"""
        time.sleep(seconds)


# ============================================================
# 人民网领导留言板适配器
# ============================================================

class PeopleLeaderAdapter(BasePlatformAdapter):
    """人民网领导留言板 (liuyan.people.com.cn)"""

    PLATFORM_NAME = "人民网领导留言板"
    LOGIN_URL = "https://liuyan.people.com.cn/login"
    REGISTER_URL = "https://liuyan.people.com.cn/signUp"
    HOME_URL = "https://liuyan.people.com.cn"
    NEEDS_LOGIN = True

    def check_logged_in(self) -> bool:
        try:
            self.browser.navigate(self.HOME_URL, wait_seconds=3)
            source = self.browser.get_page_source()
            if not source:
                return False
            # 如果页面上有"退出"或"个人中心"等字样，说明已登录
            if "退出" in source or "个人中心" in source:
                return True
            # 如果还有"登录"链接，说明未登录
            login_el = self.browser.find_element("xpath", "//p[text()='登录']")
            return login_el is None
        except Exception:
            return False

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.LOGIN_URL, wait_seconds=3):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开登录页面")

            self._safe_sleep(1)

            # 点击"密码登录"标签（如果有）
            try:
                pwd_tab = self.browser.find_element("xpath", "//div[contains(text(),'密码登录')]")
                if pwd_tab:
                    pwd_tab.click()
                    self._safe_sleep(0.5)
            except Exception:
                pass

            # 填写用户名（手机号/邮箱/登录名）
            filled_user = self.browser.fill_input("css", "input[placeholder*='登录名']", username)
            if not filled_user:
                filled_user = self.browser.fill_input("css", "input[placeholder*='手机号']", username)
            if not filled_user:
                filled_user = self.browser.fill_input("css", "input[type='text']", username)
            if not filled_user:
                return LoginResult(LoginResult.UNKNOWN_ERROR, "找不到用户名输入框")

            self._safe_sleep(0.5)

            # 填写密码
            filled_pwd = self.browser.fill_input("css", "input[placeholder*='密码']", password)
            if not filled_pwd:
                filled_pwd = self.browser.fill_input("css", "input[type='password']", password)
            if not filled_pwd:
                return LoginResult(LoginResult.UNKNOWN_ERROR, "找不到密码输入框")

            self._safe_sleep(0.5)

            # 点击登录按钮
            login_clicked = self.browser.click_element("xpath", "//button[contains(text(),'登录')]")
            if not login_clicked:
                login_clicked = self.browser.click_element("css", "button[type='submit']")
            if not login_clicked:
                buttons = self.browser.find_elements("css", "button")
                for btn in buttons:
                    try:
                        if "登录" in btn.text and "注册" not in btn.text:
                            btn.click()
                            login_clicked = True
                            break
                    except Exception:
                        continue

            if not login_clicked:
                return LoginResult(LoginResult.NEED_MANUAL,
                                   "已填写账号密码，请手动点击登录按钮", need_takeover=True)

            self._safe_sleep(3)

            # 检查登录结果
            source = self.browser.get_page_source()
            current_url = self.browser.get_current_url()

            if source:
                # 检查验证码
                if "验证码" in source and "captcha" in source.lower():
                    return LoginResult(LoginResult.NEED_CAPTCHA,
                                       "需要输入验证码，请手动完成", need_takeover=True)
                # 检查密码错误
                if "密码错误" in source or "密码不正确" in source or "账号或密码" in source:
                    return LoginResult(LoginResult.WRONG_PASSWORD, "密码错误")
                # 检查账号不存在
                if "账号不存在" in source or "用户不存在" in source or "未注册" in source:
                    return LoginResult(LoginResult.ACCOUNT_NOT_FOUND, "账号不存在，需要注册")

            # 如果URL不再是登录页，认为登录成功
            if "login" not in current_url.lower():
                return LoginResult(LoginResult.SUCCESS, "登录成功")

            return LoginResult(LoginResult.NEED_MANUAL,
                               "登录状态不确定，请手动检查", need_takeover=True)

        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")

    def auto_register(self, phone: str, email: str, password: str = "") -> LoginResult:
        try:
            self.browser._report_status(f"正在注册 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.REGISTER_URL, wait_seconds=3):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开注册页面")

            self._safe_sleep(1)

            # 填写手机号
            filled = self.browser.fill_input("css", "input[placeholder*='手机号']", phone)
            if not filled:
                filled = self.browser.fill_input("css", "input[type='text']", phone)
            if not filled:
                return LoginResult(LoginResult.UNKNOWN_ERROR, "找不到手机号输入框")

            self._safe_sleep(0.5)

            # 勾选同意协议
            try:
                checkbox = self.browser.find_element("css", "label input[type='checkbox']")
                if checkbox and not checkbox.is_selected():
                    checkbox.click()
                    self._safe_sleep(0.3)
            except Exception:
                # 尝试点击 label
                try:
                    label = self.browser.find_element("css", "label")
                    if label:
                        label.click()
                        self._safe_sleep(0.3)
                except Exception:
                    pass

            # 点击获取验证码
            sms_clicked = self.browser.click_element("xpath", "//button[contains(text(),'获取验证码')]")
            if not sms_clicked:
                sms_clicked = self.browser.click_element("xpath", "//button[contains(text(),'验证码')]")

            if sms_clicked:
                self.browser._report_status(
                    f"[{self.PLATFORM_NAME}] 已点击获取验证码，等待用户输入短信验证码...")

            # 需要用户输入短信验证码并完成后续注册步骤
            return LoginResult(
                LoginResult.NEED_SMS_CODE,
                f"已填写手机号 {phone} 并点击获取验证码。\n"
                f"请在浏览器中：\n"
                f"1. 输入收到的短信验证码\n"
                f"2. 点击【下一步】\n"
                f"3. 设置密码（建议使用: {password}）\n"
                f"4. 完成注册\n"
                f"完成后点击【继续】",
                need_takeover=True,
                registered_username=phone,
                registered_password=password,
            )

        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"注册异常: {e}")

    def _verify_login_success(self) -> bool:
        try:
            source = self.browser.get_page_source()
            url = self.browser.get_current_url()
            if not source:
                return False
            # 已登录标志
            if "退出" in source or "个人中心" in source:
                return True
            # 不在登录/注册页
            if "login" not in url.lower() and "signup" not in url.lower() and "signUp" not in url:
                # 检查是否还有登录按钮
                login_el = self.browser.find_element("xpath", "//p[text()='登录']")
                return login_el is None
            return False
        except Exception:
            return False


# ============================================================
# 中央纪委 12388 举报网站适配器（无需登录）
# ============================================================

class CCDI12388Adapter(BasePlatformAdapter):
    PLATFORM_NAME = "中央纪委国家监委举报网站"
    HOME_URL = "https://www.12388.gov.cn"
    NEEDS_LOGIN = False

    def check_logged_in(self) -> bool:
        return True

    def auto_login(self, username: str, password: str) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "该平台无需登录，可直接举报")

    def login_or_register(self, **kwargs) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "该平台无需登录")

    def navigate_to_complaint(self) -> bool:
        return self.browser.navigate("https://www.12388.gov.cn/html/jbxz.html", wait_seconds=3)


# ============================================================
# 中央和国家机关纪检监察工委适配器（无需登录）
# ============================================================

class CCDICentralAdapter(BasePlatformAdapter):
    PLATFORM_NAME = "中央和国家机关纪检监察工委"
    HOME_URL = "https://zygjjg.12388.gov.cn"
    NEEDS_LOGIN = False

    def check_logged_in(self) -> bool:
        return True

    def auto_login(self, username: str, password: str) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "该平台无需登录")

    def login_or_register(self, **kwargs) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "该平台无需登录")


# ============================================================
# 12368 诉讼服务热线适配器（仅电话）
# ============================================================

class Court12368Adapter(BasePlatformAdapter):
    PLATFORM_NAME = "12368诉讼服务热线"
    HOME_URL = "https://www.court.gov.cn"
    NEEDS_LOGIN = False

    def check_logged_in(self) -> bool:
        return True

    def auto_login(self, username: str, password: str) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "该渠道为电话投诉，无需登录")

    def login_or_register(self, **kwargs) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "电话渠道无需登录")


# ============================================================
# 通用政府网站适配器（用于大多数需要登录的平台）
# ============================================================

class GenericGovAdapter(BasePlatformAdapter):
    """
    通用政府网站适配器。
    实现通用的登录/注册逻辑：
    - 尝试查找并填写登录表单
    - 尝试查找注册入口并填写注册表单
    - 遇到无法自动化的情况时请求手动接管
    - 手动接管完成后验证登录状态
    """

    def __init__(self, browser_engine, platform_name: str = "",
                 login_url: str = "", register_url: str = "", home_url: str = ""):
        super().__init__(browser_engine)
        if platform_name:
            self.PLATFORM_NAME = platform_name
        if login_url:
            self.LOGIN_URL = login_url
        if register_url:
            self.REGISTER_URL = register_url
        if home_url:
            self.HOME_URL = home_url

    def check_logged_in(self) -> bool:
        try:
            url = self.HOME_URL or self.LOGIN_URL
            if not url:
                return False
            self.browser.navigate(url, wait_seconds=3)
            source = self.browser.get_page_source()
            if not source:
                return False
            # 通用判断：有"退出"/"注销"/"个人中心"等字样
            for keyword in ["退出", "注销", "个人中心", "我的", "用户中心"]:
                if keyword in source:
                    return True
            return False
        except Exception:
            return False

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            url = self.LOGIN_URL or self.HOME_URL
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(url, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")

            source = self.browser.get_page_source()
            if not source:
                return LoginResult(LoginResult.NETWORK_ERROR, "页面加载失败")

            # 尝试查找并填写登录表单
            filled_user = False
            filled_pwd = False

            # 尝试多种选择器填写用户名
            for selector in [
                "input[placeholder*='用户名']",
                "input[placeholder*='手机号']",
                "input[placeholder*='账号']",
                "input[placeholder*='登录']",
                "input[name='username']",
                "input[name='loginName']",
                "input[name='account']",
                "input[type='text']",
            ]:
                if self.browser.fill_input("css", selector, username):
                    filled_user = True
                    break

            self._safe_sleep(0.3)

            # 尝试多种选择器填写密码
            for selector in [
                "input[placeholder*='密码']",
                "input[name='password']",
                "input[name='pwd']",
                "input[type='password']",
            ]:
                if self.browser.fill_input("css", selector, password):
                    filled_pwd = True
                    break

            if filled_user and filled_pwd:
                self._safe_sleep(0.5)

                # 尝试点击登录按钮
                login_clicked = False
                for selector in [
                    "//button[contains(text(),'登录')]",
                    "//button[contains(text(),'登 录')]",
                    "//input[@type='submit']",
                    "//a[contains(text(),'登录')]",
                ]:
                    if self.browser.click_element("xpath", selector):
                        login_clicked = True
                        break

                if not login_clicked:
                    # 尝试 CSS 选择器
                    for selector in [
                        "button[type='submit']",
                        "input[type='submit']",
                        ".login-btn",
                        "#loginBtn",
                    ]:
                        if self.browser.click_element("css", selector):
                            login_clicked = True
                            break

                self._safe_sleep(3)

                # 检查结果
                new_source = self.browser.get_page_source()
                new_url = self.browser.get_current_url()

                if new_source:
                    if "密码错误" in new_source or "密码不正确" in new_source:
                        return LoginResult(LoginResult.WRONG_PASSWORD, "密码错误")
                    if "账号不存在" in new_source or "用户不存在" in new_source or "未注册" in new_source:
                        return LoginResult(LoginResult.ACCOUNT_NOT_FOUND, "账号不存在")
                    if "验证码" in new_source:
                        return LoginResult(LoginResult.NEED_CAPTCHA,
                                           "需要输入验证码，请手动完成", need_takeover=True)

                # 如果离开了登录页，可能成功
                if login_clicked and "login" not in new_url.lower():
                    return LoginResult(LoginResult.SUCCESS, "登录可能成功")

                return LoginResult(LoginResult.NEED_MANUAL,
                                   "已填写账号密码，请手动检查并完成登录",
                                   need_takeover=True)

            # 无法填写表单
            return LoginResult(LoginResult.NEED_MANUAL,
                               "无法自动填写登录表单，请手动登录",
                               need_takeover=True)

        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")

    def auto_register(self, phone: str, email: str, password: str = "") -> LoginResult:
        try:
            reg_url = self.REGISTER_URL
            if not reg_url:
                # 尝试在当前页面找注册链接
                source = self.browser.get_page_source()
                if source:
                    reg_link = self.browser.find_element("xpath", "//a[contains(text(),'注册')]")
                    if reg_link:
                        try:
                            reg_link.click()
                            self._safe_sleep(3)
                        except Exception:
                            pass
                    else:
                        return LoginResult(LoginResult.NEED_MANUAL,
                                           "找不到注册入口，请手动注册",
                                           need_takeover=True)
                else:
                    return LoginResult(LoginResult.NETWORK_ERROR, "页面加载失败")
            else:
                if not self.browser.navigate(reg_url, wait_seconds=5):
                    return LoginResult(LoginResult.NETWORK_ERROR, "无法打开注册页面")

            self._safe_sleep(1)

            # 尝试填写注册表单
            # 手机号
            for selector in [
                "input[placeholder*='手机']",
                "input[name='phone']",
                "input[name='mobile']",
                "input[name='tel']",
            ]:
                if self.browser.fill_input("css", selector, phone):
                    break

            self._safe_sleep(0.3)

            # 邮箱
            if email:
                for selector in [
                    "input[placeholder*='邮箱']",
                    "input[name='email']",
                    "input[type='email']",
                ]:
                    if self.browser.fill_input("css", selector, email):
                        break

            self._safe_sleep(0.3)

            # 密码
            if password:
                pwd_inputs = self.browser.find_elements("css", "input[type='password']")
                for inp in pwd_inputs:
                    try:
                        inp.clear()
                        inp.send_keys(password)
                        self._safe_sleep(0.2)
                    except Exception:
                        continue

            # 尝试点击获取验证码
            sms_clicked = False
            for text in ['获取验证码', '发送验证码', '获取短信', '发送短信']:
                if self.browser.click_element("xpath", f"//button[contains(text(),'{text}')]"):
                    sms_clicked = True
                    break
                if self.browser.click_element("xpath", f"//a[contains(text(),'{text}')]"):
                    sms_clicked = True
                    break
                if self.browser.click_element("xpath", f"//span[contains(text(),'{text}')]"):
                    sms_clicked = True
                    break

            msg = f"已尝试填写注册信息（手机号: {phone}）。\n"
            if sms_clicked:
                msg += "已点击获取验证码。\n"
            msg += "请在浏览器中完成注册流程：\n"
            msg += f"1. 输入短信验证码\n"
            msg += f"2. 设置密码（建议: {password}）\n"
            msg += f"3. 完成注册并登录\n"
            msg += f"完成后点击【继续】"

            return LoginResult(
                LoginResult.NEED_SMS_CODE,
                msg,
                need_takeover=True,
                registered_username=phone,
                registered_password=password,
            )

        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"注册异常: {e}")

    def _verify_login_success(self) -> bool:
        try:
            self._safe_sleep(1)
            source = self.browser.get_page_source()
            url = self.browser.get_current_url()
            if not source:
                return False
            # 有退出/注销等字样
            for keyword in ["退出", "注销", "个人中心", "我的", "用户中心"]:
                if keyword in source:
                    return True
            # 不在登录/注册页
            if "login" not in url.lower() and "register" not in url.lower() and "signup" not in url.lower():
                return True
            return False
        except Exception:
            return False


# ============================================================
# 各平台具体适配器（继承通用适配器，设置特定URL）
# ============================================================

class CourtJubaoAdapter(GenericGovAdapter):
    """最高人民法院违纪违法举报中心"""
    PLATFORM_NAME = "最高人民法院违纪违法举报中心"
    HOME_URL = "https://jubao.court.gov.cn"
    NEEDS_LOGIN = True


class CourtXFAdapter(GenericGovAdapter):
    """人民法院网上申诉信访平台"""
    PLATFORM_NAME = "人民法院网上申诉信访平台"
    LOGIN_URL = "https://ssxfpt.court.gov.cn"
    HOME_URL = "https://ssxfpt.court.gov.cn"
    NEEDS_LOGIN = True


class Procuratorate12309Adapter(GenericGovAdapter):
    """12309中国检察网"""
    PLATFORM_NAME = "12309中国检察网"
    HOME_URL = "https://www.12309.gov.cn"
    NEEDS_LOGIN = True


class GJXFJAdapter(GenericGovAdapter):
    """国家信访局网上信访"""
    PLATFORM_NAME = "国家信访局网上信访"
    HOME_URL = "https://wsxf.gjxfj.gov.cn"
    NEEDS_LOGIN = True


class ZhengFaWei12337Adapter(GenericGovAdapter):
    """12337政法干警违纪违法举报平台"""
    PLATFORM_NAME = "12337政法干警违纪违法举报平台"
    HOME_URL = "https://www.12337.gov.cn"
    NEEDS_LOGIN = True


class MOJAdapter(GenericGovAdapter):
    """司法部网上信访"""
    PLATFORM_NAME = "司法部网上信访"
    HOME_URL = "https://www.moj.gov.cn/hdjl/hdjlwsxf/"
    NEEDS_LOGIN = True


class NPCAdapter(GenericGovAdapter):
    """全国人大机关网上信访"""
    PLATFORM_NAME = "全国人大机关网上信访"
    HOME_URL = "http://www.npc.gov.cn/wsxf/"
    NEEDS_LOGIN = True


class GovDuchaAdapter(GenericGovAdapter):
    """国务院互联网+督查平台"""
    PLATFORM_NAME = "国务院互联网+督查平台"
    HOME_URL = "https://tousu.www.gov.cn"
    NEEDS_LOGIN = True


# ============================================================
# 通用省级平台适配器
# ============================================================

class GenericProvincialAdapter(GenericGovAdapter):
    """通用省级平台适配器（省人大信访、省信访局）"""

    def __init__(self, browser_engine, platform_name: str, url: str):
        super().__init__(browser_engine, platform_name=platform_name, home_url=url)


# ============================================================
# 适配器注册表
# ============================================================

ADAPTER_REGISTRY = {
    "最高人民法院违纪违法举报中心": CourtJubaoAdapter,
    "人民法院网上申诉信访平台": CourtXFAdapter,
    "12368诉讼服务热线": Court12368Adapter,
    "12309中国检察网": Procuratorate12309Adapter,
    "中央纪委国家监委举报网站": CCDI12388Adapter,
    "中央和国家机关纪检监察工委": CCDICentralAdapter,
    "全国人大机关网上信访": NPCAdapter,
    "国家信访局网上信访": GJXFJAdapter,
    "司法部网上信访": MOJAdapter,
    "12337政法干警违纪违法举报平台": ZhengFaWei12337Adapter,
    "人民网领导留言板": PeopleLeaderAdapter,
    "国务院互联网+督查平台": GovDuchaAdapter,
}


def get_adapter(platform_name: str, browser_engine) -> BasePlatformAdapter:
    """
    根据平台名称获取对应的适配器实例。
    如果没有专用适配器，返回通用适配器。
    """
    adapter_class = ADAPTER_REGISTRY.get(platform_name)
    if adapter_class:
        return adapter_class(browser_engine)

    # 省级平台使用通用适配器
    return GenericProvincialAdapter(browser_engine, platform_name, "")
