#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号密码管理模块
================
负责各投诉平台的用户名、密码的本地加密存储与读取。
使用 base64 简单编码存储（可升级为 keyring 等更安全方案）。

存储位置：~/.court_complaint/accounts.json
"""

import json
import os
import base64
import hashlib
from typing import Optional, Dict, Any


class AccountManager:
    """管理各投诉平台的账号密码"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".court_complaint")
        self.config_dir = config_dir
        self.accounts_file = os.path.join(self.config_dir, "accounts.json")
        os.makedirs(self.config_dir, exist_ok=True)
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ---- 编码/解码（简单 base64 混淆，非强加密） ----

    @staticmethod
    def _encode(text: str) -> str:
        """简单编码，防止明文存储"""
        return base64.b64encode(text.encode("utf-8")).decode("ascii")

    @staticmethod
    def _decode(encoded: str) -> str:
        """解码"""
        return base64.b64decode(encoded.encode("ascii")).decode("utf-8")

    # ---- 持久化 ----

    def _load(self):
        """从文件加载账号数据"""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, "r", encoding="utf-8") as f:
                    self._accounts = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._accounts = {}
        else:
            self._accounts = {}

    def _save(self):
        """保存账号数据到文件"""
        try:
            with open(self.accounts_file, "w", encoding="utf-8") as f:
                json.dump(self._accounts, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[AccountManager] 保存账号文件失败: {e}")

    # ---- 公开接口 ----

    def get_platform_key(self, platform_name: str) -> str:
        """将平台名称转换为存储键名"""
        return hashlib.md5(platform_name.encode("utf-8")).hexdigest()[:12]

    def save_account(self, platform_name: str, username: str, password: str,
                     phone: str = "", email: str = "", extra: Optional[Dict] = None):
        """保存某个平台的账号信息"""
        key = self.get_platform_key(platform_name)
        self._accounts[key] = {
            "platform": platform_name,
            "username": self._encode(username),
            "password": self._encode(password),
            "phone": self._encode(phone) if phone else "",
            "email": self._encode(email) if email else "",
            "extra": extra or {},
        }
        self._save()

    def get_account(self, platform_name: str) -> Optional[Dict[str, str]]:
        """获取某个平台的账号信息，返回解码后的明文"""
        key = self.get_platform_key(platform_name)
        data = self._accounts.get(key)
        if data is None:
            return None
        result = {
            "platform": data["platform"],
            "username": self._decode(data["username"]),
            "password": self._decode(data["password"]),
        }
        if data.get("phone"):
            result["phone"] = self._decode(data["phone"])
        if data.get("email"):
            result["email"] = self._decode(data["email"])
        if data.get("extra"):
            result["extra"] = data["extra"]
        return result

    def has_account(self, platform_name: str) -> bool:
        """检查某个平台是否已保存账号"""
        key = self.get_platform_key(platform_name)
        return key in self._accounts

    def delete_account(self, platform_name: str) -> bool:
        """删除某个平台的账号"""
        key = self.get_platform_key(platform_name)
        if key in self._accounts:
            del self._accounts[key]
            self._save()
            return True
        return False

    def list_platforms(self) -> list:
        """列出所有已保存账号的平台名称"""
        return [v["platform"] for v in self._accounts.values()]

    def get_all_accounts(self) -> Dict[str, Dict[str, str]]:
        """获取所有平台的账号信息（解码后）"""
        result = {}
        for key, data in self._accounts.items():
            platform = data["platform"]
            result[platform] = {
                "username": self._decode(data["username"]),
                "password": self._decode(data["password"]),
            }
            if data.get("phone"):
                result[platform]["phone"] = self._decode(data["phone"])
            if data.get("email"):
                result[platform]["email"] = self._decode(data["email"])
        return result

    def set_default_credentials(self, phone: str, email: str, default_password: str = ""):
        """设置默认注册信息（手机号、邮箱），用于自动注册"""
        self._accounts["__defaults__"] = {
            "platform": "__defaults__",
            "phone": self._encode(phone),
            "email": self._encode(email),
            "default_password": self._encode(default_password) if default_password else "",
        }
        self._save()

    def get_default_credentials(self) -> Optional[Dict[str, str]]:
        """获取默认注册信息"""
        data = self._accounts.get("__defaults__")
        if data is None:
            return None
        result = {
            "phone": self._decode(data["phone"]) if data.get("phone") else "",
            "email": self._decode(data["email"]) if data.get("email") else "",
        }
        if data.get("default_password"):
            result["default_password"] = self._decode(data["default_password"])
        return result
