#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器自动化引擎
================
基于 Selenium 实现浏览器自动化操作。
支持自动登录、自动注册、手动接管等功能。

依赖：
  pip install selenium webdriver-manager
"""

import time
import threading
import subprocess
import sys
import os
from typing import Optional, Callable

# 尝试导入 selenium，如果未安装则提供安装提示
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException,
        NoSuchElementException,
        WebDriverException,
        ElementNotInteractableException,
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def check_and_install_dependencies():
    """检查并安装必要的依赖"""
    missing = []
    try:
        import selenium
    except ImportError:
        missing.append("selenium")
    try:
        import webdriver_manager
    except ImportError:
        missing.append("webdriver-manager")

    if missing:
        print(f"[BrowserEngine] 正在安装缺少的依赖: {', '.join(missing)}")
        for pkg in missing:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
        print("[BrowserEngine] 依赖安装完成，请重新启动程序。")
        return False
    return True


class BrowserEngine:
    """
    浏览器自动化引擎

    功能：
    - 启动/关闭 Chrome 浏览器
    - 导航到指定 URL
    - 自动填写表单字段
    - 自动点击按钮
    - 等待元素出现
    - 手动接管模式（暂停自动化，让用户操作）
    """

    def __init__(self, headless: bool = False, user_data_dir: Optional[str] = None):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.driver: Optional[webdriver.Chrome] = None
        self._takeover_mode = False
        self._takeover_event = threading.Event()
        self._status_callback: Optional[Callable] = None
        self._running = False

    def set_status_callback(self, callback: Callable):
        """设置状态回调函数，用于向 GUI 报告状态"""
        self._status_callback = callback

    def _report_status(self, message: str, level: str = "info"):
        """报告状态"""
        print(f"[BrowserEngine][{level}] {message}")
        if self._status_callback:
            self._status_callback(message, level)

    def start(self) -> bool:
        """启动浏览器"""
        if not SELENIUM_AVAILABLE:
            self._report_status("Selenium 未安装，请先运行: pip install selenium webdriver-manager", "error")
            return False

        try:
            options = ChromeOptions()

            if self.headless:
                options.add_argument("--headless=new")

            # 通用选项
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--window-size=1280,900")
            options.add_argument("--lang=zh-CN")

            # 用户数据目录（保持登录状态）
            if self.user_data_dir:
                os.makedirs(self.user_data_dir, exist_ok=True)
                options.add_argument(f"--user-data-dir={self.user_data_dir}")

            # 尝试使用 webdriver-manager 自动管理驱动
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception:
                # 回退：直接使用系统 chromedriver
                try:
                    self.driver = webdriver.Chrome(options=options)
                except Exception as e2:
                    self._report_status(f"无法启动 Chrome 浏览器: {e2}", "error")
                    return False

            # 反检测
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
            )

            self._running = True
            self._report_status("浏览器已启动")
            return True

        except Exception as e:
            self._report_status(f"启动浏览器失败: {e}", "error")
            return False

    def stop(self):
        """关闭浏览器"""
        self._running = False
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
        self._report_status("浏览器已关闭")

    def is_running(self) -> bool:
        """检查浏览器是否在运行"""
        if not self._running or not self.driver:
            return False
        try:
            _ = self.driver.title
            return True
        except Exception:
            self._running = False
            return False

    # ---- 导航 ----

    def navigate(self, url: str, wait_seconds: float = 3) -> bool:
        """导航到指定 URL"""
        if not self.is_running():
            return False
        try:
            self._report_status(f"正在打开: {url}")
            self.driver.get(url)
            time.sleep(wait_seconds)
            return True
        except Exception as e:
            self._report_status(f"打开页面失败: {e}", "error")
            return False

    # ---- 元素操作 ----

    def wait_for_element(self, by: str, value: str, timeout: float = 10):
        """等待元素出现"""
        if not self.is_running():
            return None
        try:
            by_map = {
                "id": By.ID,
                "name": By.NAME,
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "class": By.CLASS_NAME,
                "tag": By.TAG_NAME,
                "link_text": By.LINK_TEXT,
                "partial_link": By.PARTIAL_LINK_TEXT,
            }
            selenium_by = by_map.get(by, By.CSS_SELECTOR)
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((selenium_by, value))
            )
            return element
        except TimeoutException:
            return None
        except Exception:
            return None

    def find_element(self, by: str, value: str):
        """查找元素"""
        if not self.is_running():
            return None
        try:
            by_map = {
                "id": By.ID,
                "name": By.NAME,
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "class": By.CLASS_NAME,
            }
            selenium_by = by_map.get(by, By.CSS_SELECTOR)
            return self.driver.find_element(selenium_by, value)
        except (NoSuchElementException, Exception):
            return None

    def find_elements(self, by: str, value: str):
        """查找多个元素"""
        if not self.is_running():
            return []
        try:
            by_map = {
                "id": By.ID,
                "name": By.NAME,
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "class": By.CLASS_NAME,
            }
            selenium_by = by_map.get(by, By.CSS_SELECTOR)
            return self.driver.find_elements(selenium_by, value)
        except Exception:
            return []

    def fill_input(self, by: str, value: str, text: str, clear_first: bool = True) -> bool:
        """填写输入框"""
        element = self.wait_for_element(by, value, timeout=5)
        if element is None:
            return False
        try:
            if clear_first:
                element.clear()
                time.sleep(0.2)
            element.send_keys(text)
            time.sleep(0.3)
            return True
        except (ElementNotInteractableException, Exception) as e:
            self._report_status(f"填写输入框失败: {e}", "warning")
            return False

    def click_element(self, by: str, value: str) -> bool:
        """点击元素"""
        element = self.wait_for_element(by, value, timeout=5)
        if element is None:
            return False
        try:
            element.click()
            time.sleep(0.5)
            return True
        except Exception as e:
            # 尝试 JavaScript 点击
            try:
                self.driver.execute_script("arguments[0].click();", element)
                time.sleep(0.5)
                return True
            except Exception:
                self._report_status(f"点击元素失败: {e}", "warning")
                return False

    def get_page_source(self) -> str:
        """获取页面源码"""
        if not self.is_running():
            return ""
        try:
            return self.driver.page_source
        except Exception:
            return ""

    def get_current_url(self) -> str:
        """获取当前 URL"""
        if not self.is_running():
            return ""
        try:
            return self.driver.current_url
        except Exception:
            return ""

    def get_title(self) -> str:
        """获取页面标题"""
        if not self.is_running():
            return ""
        try:
            return self.driver.title
        except Exception:
            return ""

    def execute_script(self, script: str, *args):
        """执行 JavaScript"""
        if not self.is_running():
            return None
        try:
            return self.driver.execute_script(script, *args)
        except Exception:
            return None

    def switch_to_new_tab(self, url: str) -> bool:
        """在新标签页中打开 URL"""
        if not self.is_running():
            return False
        try:
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(1)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(2)
            return True
        except Exception as e:
            self._report_status(f"打开新标签页失败: {e}", "warning")
            return False

    def close_current_tab(self):
        """关闭当前标签页并切换到上一个"""
        if not self.is_running():
            return
        try:
            self.driver.close()
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[-1])
        except Exception:
            pass

    def get_tab_count(self) -> int:
        """获取标签页数量"""
        if not self.is_running():
            return 0
        try:
            return len(self.driver.window_handles)
        except Exception:
            return 0

    def switch_to_tab(self, index: int) -> bool:
        """切换到指定标签页"""
        if not self.is_running():
            return False
        try:
            handles = self.driver.window_handles
            if 0 <= index < len(handles):
                self.driver.switch_to.window(handles[index])
                return True
            return False
        except Exception:
            return False

    # ---- 手动接管模式 ----

    def enter_takeover_mode(self, reason: str = "需要用户手动操作"):
        """
        进入手动接管模式。
        自动化暂停，用户可以在浏览器中手动操作。
        调用 exit_takeover_mode() 恢复自动化。
        """
        self._takeover_mode = True
        self._takeover_event.clear()
        self._report_status(f"⚠ 手动接管模式: {reason}", "takeover")

    def exit_takeover_mode(self):
        """退出手动接管模式，恢复自动化"""
        self._takeover_mode = False
        self._takeover_event.set()
        self._report_status("✅ 已恢复自动化模式")

    def is_takeover_mode(self) -> bool:
        """检查是否处于手动接管模式"""
        return self._takeover_mode

    def wait_for_takeover_complete(self, timeout: float = 300) -> bool:
        """
        等待手动接管完成。
        返回 True 表示用户已完成操作，False 表示超时。
        """
        return self._takeover_event.wait(timeout=timeout)

    # ---- 截图 ----

    def take_screenshot(self, filepath: str) -> bool:
        """截取当前页面截图"""
        if not self.is_running():
            return False
        try:
            self.driver.save_screenshot(filepath)
            return True
        except Exception:
            return False
