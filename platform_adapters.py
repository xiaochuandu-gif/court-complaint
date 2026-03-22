#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台适配器模块
==============
为每个投诉平台编写登录/注册适配器。
每个适配器知道如何在对应平台上：
  1. 检测是否已登录
  2. 自动登录（用户名+密码）
  3. 自动注册（手机号+邮箱）
  4. 判断何时需要手动接管（验证码、人机验证等）
"""

import time
from typing import Optional, Dict, Tuple


class LoginResult:
    """登录/注册操作的结果"""
    SUCCESS = "success"
    NEED_CAPTCHA = "need_captcha"          # 需要输入验证码
    NEED_SMS_CODE = "need_sms_code"        # 需要输入短信验证码
    NEED_MANUAL = "need_manual"            # 需要手动操作
    WRONG_PASSWORD = "wrong_password"      # 密码错误
    ACCOUNT_NOT_FOUND = "account_not_found"  # 账号不存在
    NETWORK_ERROR = "network_error"        # 网络错误
    ALREADY_LOGGED_IN = "already_logged_in"  # 已经登录
    UNKNOWN_ERROR = "unknown_error"        # 未知错误

    def __init__(self, status: str, message: str = "", need_takeover: bool = False):
        self.status = status
        self.message = message
        self.need_takeover = need_takeover

    def is_success(self) -> bool:
        return self.status in (self.SUCCESS, self.ALREADY_LOGGED_IN)


class BasePlatformAdapter:
    """
    平台适配器基类。
    所有平台适配器都继承此类。
    """

    # 平台基本信息（子类覆盖）
    PLATFORM_NAME = ""
    LOGIN_URL = ""
    REGISTER_URL = ""
    HOME_URL = ""
    NEEDS_LOGIN = True  # 是否需要登录才能投诉

    def __init__(self, browser_engine):
        self.browser = browser_engine

    def check_logged_in(self) -> bool:
        """检测当前是否已登录。子类实现。"""
        return False

    def auto_login(self, username: str, password: str) -> LoginResult:
        """自动登录。子类实现。"""
        return LoginResult(LoginResult.UNKNOWN_ERROR, "该平台暂不支持自动登录")

    def auto_register(self, phone: str, email: str, password: str = "") -> LoginResult:
        """自动注册。子类实现。"""
        return LoginResult(LoginResult.UNKNOWN_ERROR, "该平台暂不支持自动注册")

    def navigate_to_complaint(self) -> bool:
        """导航到投诉页面。子类实现。"""
        if self.HOME_URL:
            return self.browser.navigate(self.HOME_URL)
        return False

    def paste_complaint_content(self, content: str) -> bool:
        """粘贴投诉内容到对应的文本框。子类可覆盖。"""
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
        """检测是否已登录：看页面上是否有"登录"链接"""
        try:
            self.browser.navigate(self.HOME_URL, wait_seconds=3)
            source = self.browser.get_page_source()
            # 如果页面上没有"登录"链接，说明已登录
            if source and "登录" not in source:
                return True
            # 更精确：查找登录按钮
            login_btn = self.browser.find_element("xpath", "//p[text()='登录']")
            return login_btn is None
        except Exception:
            return False

    def auto_login(self, username: str, password: str) -> LoginResult:
        """自动登录人民网领导留言板"""
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")

            # 导航到登录页
            if not self.browser.navigate(self.LOGIN_URL, wait_seconds=3):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开登录页面")

            # 查找并填写用户名
            if not self.browser.fill_input("css", "input[placeholder*='登录名']", username):
                # 备选选择器
                if not self.browser.fill_input("css", "input[placeholder*='手机号']", username):
                    return LoginResult(LoginResult.UNKNOWN_ERROR, "找不到用户名输入框")

            self._safe_sleep(0.5)

            # 填写密码
            if not self.browser.fill_input("css", "input[placeholder*='密码']", password):
                if not self.browser.fill_input("css", "input[type='password']", password):
                    return LoginResult(LoginResult.UNKNOWN_ERROR, "找不到密码输入框")

            self._safe_sleep(0.5)

            # 点击登录按钮
            login_clicked = self.browser.click_element("css", "button:has-text('登录')")
            if not login_clicked:
                # 备选：查找所有按钮
                buttons = self.browser.find_elements("css", "button")
                for btn in buttons:
                    try:
                        if "登录" in btn.text:
                            btn.click()
                            login_clicked = True
                            break
                    except Exception:
                        continue

            if not login_clicked:
                return LoginResult(LoginResult.UNKNOWN_ERROR, "找不到登录按钮")

            self._safe_sleep(3)

            # 检查登录结果
            current_url = self.browser.get_current_url()
            source = self.browser.get_page_source()

            # 检查是否有验证码
            if source and ("验证码" in source or "captcha" in source.lower()):
                return LoginResult(LoginResult.NEED_CAPTCHA, "需要输入验证码，请手动完成", need_takeover=True)

            # 检查是否有错误提示
            if source and ("密码错误" in source or "密码不正确" in source):
                return LoginResult(LoginResult.WRONG_PASSWORD, "密码错误")
            if source and ("账号不存在" in source or "用户不存在" in source):
                return LoginResult(LoginResult.ACCOUNT_NOT_FOUND, "账号不存在")

            # 如果 URL 变了（不再是登录页），认为登录成功
            if "login" not in current_url.lower():
                return LoginResult(LoginResult.SUCCESS, "登录成功")

            # 不确定，让用户接管
            return LoginResult(LoginResult.NEED_MANUAL, "登录状态不确定，请手动检查", need_takeover=True)

        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")

    def auto_register(self, phone: str, email: str, password: str = "") -> LoginResult:
        """自动注册人民网领导留言板"""
        try:
            self.browser._report_status(f"正在注册 {self.PLATFORM_NAME}...")

            if not self.browser.navigate(self.REGISTER_URL, wait_seconds=3):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开注册页面")

            # 填写手机号
            if not self.browser.fill_input("css", "input[placeholder*='手机号']", phone):
                return LoginResult(LoginResult.UNKNOWN_ERROR, "找不到手机号输入框")

            self._safe_sleep(0.5)

            # 需要用户手动获取验证码
            return LoginResult(
                LoginResult.NEED_SMS_CODE,
                "已填写手机号，请手动点击获取验证码并完成注册",
                need_takeover=True,
            )

        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"注册异常: {e}")


# ============================================================
# 中央纪委 12388 举报网站适配器
# ============================================================

class CCDI12388Adapter(BasePlatformAdapter):
    """中央纪委国家监委举报网站 (www.12388.gov.cn)"""

    PLATFORM_NAME = "中央纪委国家监委举报网站"
    LOGIN_URL = ""
    HOME_URL = "https://www.12388.gov.cn"
    NEEDS_LOGIN = False  # 无需登录

    def check_logged_in(self) -> bool:
        return True  # 无需登录

    def auto_login(self, username: str, password: str) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "该平台无需登录，可直接举报")

    def navigate_to_complaint(self) -> bool:
        """导航到举报须知页面"""
        return self.browser.navigate("https://www.12388.gov.cn/html/jbxz.html", wait_seconds=3)


# ============================================================
# 中央和国家机关纪检监察工委适配器
# ============================================================

class CCDICentralAdapter(BasePlatformAdapter):
    """中央和国家机关纪检监察工委 (zygjjg.12388.gov.cn)"""

    PLATFORM_NAME = "中央和国家机关纪检监察工委"
    HOME_URL = "https://zygjjg.12388.gov.cn"
    NEEDS_LOGIN = False

    def check_logged_in(self) -> bool:
        return True

    def auto_login(self, username: str, password: str) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "该平台无需登录")


# ============================================================
# 人民法院网上申诉信访平台适配器
# ============================================================

class CourtXFAdapter(BasePlatformAdapter):
    """人民法院网上申诉信访平台 (ssxfpt.court.gov.cn)"""

    PLATFORM_NAME = "人民法院网上申诉信访平台"
    LOGIN_URL = "https://ssxfpt.court.gov.cn"
    HOME_URL = "https://ssxfpt.court.gov.cn"
    NEEDS_LOGIN = True

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.LOGIN_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开登录页面")

            # 法院系统通常需要实名认证，自动化有限
            source = self.browser.get_page_source()
            if source and ("登录" in source or "用户名" in source):
                # 尝试填写
                self.browser.fill_input("css", "input[type='text']", username)
                self._safe_sleep(0.3)
                self.browser.fill_input("css", "input[type='password']", password)
                self._safe_sleep(0.3)

                # 可能有验证码
                return LoginResult(
                    LoginResult.NEED_MANUAL,
                    "已填写账号密码，可能需要验证码，请手动完成登录",
                    need_takeover=True,
                )

            return LoginResult(LoginResult.NEED_MANUAL, "页面结构未知，请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")

    def auto_register(self, phone: str, email: str, password: str = "") -> LoginResult:
        return LoginResult(LoginResult.NEED_MANUAL, "法院平台需要实名认证注册，请手动完成", need_takeover=True)


# ============================================================
# 最高人民法院违纪违法举报中心适配器
# ============================================================

class CourtJubaoAdapter(BasePlatformAdapter):
    """最高人民法院违纪违法举报中心 (jubao.court.gov.cn)"""

    PLATFORM_NAME = "最高人民法院违纪违法举报中心"
    HOME_URL = "https://jubao.court.gov.cn"
    NEEDS_LOGIN = True

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.HOME_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")

            source = self.browser.get_page_source()
            if source and ("登录" in source or "注册" in source):
                # 尝试查找并填写登录表单
                self.browser.fill_input("css", "input[type='text']", username)
                self._safe_sleep(0.3)
                self.browser.fill_input("css", "input[type='password']", password)
                self._safe_sleep(0.3)
                return LoginResult(
                    LoginResult.NEED_MANUAL,
                    "已尝试填写账号密码，请手动检查并完成登录",
                    need_takeover=True,
                )

            return LoginResult(LoginResult.NEED_MANUAL, "请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")


# ============================================================
# 12309 中国检察网适配器
# ============================================================

class Procuratorate12309Adapter(BasePlatformAdapter):
    """12309中国检察网 (www.12309.gov.cn)"""

    PLATFORM_NAME = "12309中国检察网"
    HOME_URL = "https://www.12309.gov.cn"
    NEEDS_LOGIN = True

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.HOME_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")

            source = self.browser.get_page_source()
            if source and ("登录" in source or "用户" in source):
                self.browser.fill_input("css", "input[type='text']", username)
                self._safe_sleep(0.3)
                self.browser.fill_input("css", "input[type='password']", password)
                self._safe_sleep(0.3)
                return LoginResult(
                    LoginResult.NEED_MANUAL,
                    "已尝试填写账号密码，请手动完成登录",
                    need_takeover=True,
                )

            return LoginResult(LoginResult.NEED_MANUAL, "请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")


# ============================================================
# 国家信访局适配器
# ============================================================

class GJXFJAdapter(BasePlatformAdapter):
    """国家信访局网上信访 (wsxf.gjxfj.gov.cn)"""

    PLATFORM_NAME = "国家信访局网上信访"
    HOME_URL = "https://wsxf.gjxfj.gov.cn"
    NEEDS_LOGIN = True

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.HOME_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")

            source = self.browser.get_page_source()
            if source and ("登录" in source or "用户名" in source):
                self.browser.fill_input("css", "input[type='text']", username)
                self._safe_sleep(0.3)
                self.browser.fill_input("css", "input[type='password']", password)
                self._safe_sleep(0.3)
                return LoginResult(
                    LoginResult.NEED_MANUAL,
                    "已尝试填写账号密码，请手动完成登录",
                    need_takeover=True,
                )

            return LoginResult(LoginResult.NEED_MANUAL, "请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")


# ============================================================
# 12337 政法干警举报平台适配器
# ============================================================

class ZhengFaWei12337Adapter(BasePlatformAdapter):
    """12337政法干警违纪违法举报平台 (www.12337.gov.cn)"""

    PLATFORM_NAME = "12337政法干警违纪违法举报平台"
    HOME_URL = "https://www.12337.gov.cn"
    NEEDS_LOGIN = True

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.HOME_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")

            source = self.browser.get_page_source()
            if source and ("登录" in source or "用户" in source):
                self.browser.fill_input("css", "input[type='text']", username)
                self._safe_sleep(0.3)
                self.browser.fill_input("css", "input[type='password']", password)
                self._safe_sleep(0.3)
                return LoginResult(
                    LoginResult.NEED_MANUAL,
                    "已尝试填写账号密码，请手动完成登录",
                    need_takeover=True,
                )

            return LoginResult(LoginResult.NEED_MANUAL, "请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")


# ============================================================
# 司法部网上信访适配器
# ============================================================

class MOJAdapter(BasePlatformAdapter):
    """司法部网上信访 (www.moj.gov.cn)"""

    PLATFORM_NAME = "司法部网上信访"
    HOME_URL = "https://www.moj.gov.cn/hdjl/hdjlwsxf/"
    NEEDS_LOGIN = True

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.HOME_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")
            return LoginResult(LoginResult.NEED_MANUAL, "请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")


# ============================================================
# 全国人大机关网上信访适配器
# ============================================================

class NPCAdapter(BasePlatformAdapter):
    """全国人大机关网上信访 (www.npc.gov.cn)"""

    PLATFORM_NAME = "全国人大机关网上信访"
    HOME_URL = "http://www.npc.gov.cn/wsxf/"
    NEEDS_LOGIN = True

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.HOME_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")

            source = self.browser.get_page_source()
            if source and ("登录" in source or "用户" in source):
                self.browser.fill_input("css", "input[type='text']", username)
                self._safe_sleep(0.3)
                self.browser.fill_input("css", "input[type='password']", password)
                self._safe_sleep(0.3)
                return LoginResult(
                    LoginResult.NEED_MANUAL,
                    "已尝试填写账号密码，请手动完成登录",
                    need_takeover=True,
                )

            return LoginResult(LoginResult.NEED_MANUAL, "请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")


# ============================================================
# 国务院互联网+督查平台适配器
# ============================================================

class GovDuchaAdapter(BasePlatformAdapter):
    """国务院互联网+督查平台 (tousu.www.gov.cn)"""

    PLATFORM_NAME = "国务院互联网+督查平台"
    HOME_URL = "https://tousu.www.gov.cn"
    NEEDS_LOGIN = True

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.HOME_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")

            source = self.browser.get_page_source()
            if source and ("登录" in source or "用户" in source):
                self.browser.fill_input("css", "input[type='text']", username)
                self._safe_sleep(0.3)
                self.browser.fill_input("css", "input[type='password']", password)
                self._safe_sleep(0.3)
                return LoginResult(
                    LoginResult.NEED_MANUAL,
                    "已尝试填写账号密码，请手动完成登录",
                    need_takeover=True,
                )

            return LoginResult(LoginResult.NEED_MANUAL, "请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")


# ============================================================
# 12368 诉讼服务热线适配器（仅电话，无网页登录）
# ============================================================

class Court12368Adapter(BasePlatformAdapter):
    """12368诉讼服务热线"""

    PLATFORM_NAME = "12368诉讼服务热线"
    HOME_URL = "https://www.court.gov.cn"
    NEEDS_LOGIN = False

    def check_logged_in(self) -> bool:
        return True

    def auto_login(self, username: str, password: str) -> LoginResult:
        return LoginResult(LoginResult.ALREADY_LOGGED_IN, "该渠道为电话投诉，无需登录")


# ============================================================
# 通用省级平台适配器
# ============================================================

class GenericProvincialAdapter(BasePlatformAdapter):
    """通用省级平台适配器（省人大信访、省信访局）"""

    NEEDS_LOGIN = True

    def __init__(self, browser_engine, platform_name: str, url: str):
        super().__init__(browser_engine)
        self.PLATFORM_NAME = platform_name
        self.HOME_URL = url

    def auto_login(self, username: str, password: str) -> LoginResult:
        try:
            self.browser._report_status(f"正在登录 {self.PLATFORM_NAME}...")
            if not self.browser.navigate(self.HOME_URL, wait_seconds=5):
                return LoginResult(LoginResult.NETWORK_ERROR, "无法打开页面")

            source = self.browser.get_page_source()
            if source and ("登录" in source or "用户" in source or "注册" in source):
                # 尝试查找并填写
                text_inputs = self.browser.find_elements("css", "input[type='text']")
                pwd_inputs = self.browser.find_elements("css", "input[type='password']")

                if text_inputs:
                    try:
                        text_inputs[0].clear()
                        text_inputs[0].send_keys(username)
                    except Exception:
                        pass
                if pwd_inputs:
                    try:
                        pwd_inputs[0].clear()
                        pwd_inputs[0].send_keys(password)
                    except Exception:
                        pass

                return LoginResult(
                    LoginResult.NEED_MANUAL,
                    "已尝试填写账号密码，请手动完成登录",
                    need_takeover=True,
                )

            return LoginResult(LoginResult.NEED_MANUAL, "请手动登录", need_takeover=True)
        except Exception as e:
            return LoginResult(LoginResult.UNKNOWN_ERROR, f"登录异常: {e}")


# ============================================================
# 适配器注册表
# ============================================================

# 平台名称 -> 适配器类的映射
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
