# -*- coding: utf-8 -*-
"""platform_compat.py — لایه‌ی سازگاری پلتفرم برای نسخه‌ی مک IAS Viewer.

این ریپو (IAS-Viewer-MAC) همان کد IAS-CMS است با حداقل تغییرات برای macOS.
همه‌ی تفاوت‌های پلتفرم این‌جا متمرکز شده تا سینک بعدی با ریپوی ویندوز ساده بماند:

- is_macos() / is_windows(): تشخیص پلتفرم
- get_app_bundle_path(): مسیر IAS Viewer.app در حالت frozen
- macos_hwid(): شناسه‌ی سخت‌افزاری مک (IOPlatformUUID)
- macos_total_ram_gb(): حافظه‌ی کل سیستم از روی sysctl
- macos_keychain_set/get(): ذخیره‌ی امن رمز در Keychain (جایگزین DPAPI)
- macos_msgbox(): دیالوگ خطا با osascript (جایگزین MessageBoxW)
- macos_open(): باز کردن فایل/پوشه با Finder (جایگزین os.startfile)

این ماژول عمداً هیچ وابستگی خارجی ندارد (فقط کتابخانه‌ی استاندارد پایتون).
"""

import os
import shutil
import subprocess
import sys


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return os.name == "nt"


def get_app_bundle_path() -> str | None:
    """مسیر پوشه‌ی IAS Viewer.app در حالت frozen؛ در غیر این صورت None."""
    if not is_macos():
        return None
    try:
        exe = os.path.abspath(sys.executable)
        p = exe
        # .../IAS Viewer.app/Contents/MacOS/IAS Viewer
        while True:
            parent = os.path.dirname(p)
            if not parent or parent == p:
                return None
            if parent.endswith(".app"):
                return parent
            p = parent
    except Exception:
        return None


def macos_hwid() -> str | None:
    """شناسه‌ی یکتای سخت‌افزار مک (IOPlatformUUID)؛ None اگر نشد."""
    if not is_macos():
        return None
    try:
        out = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        for line in out.splitlines():
            if "IOPlatformUUID" in line:
                # "IOPlatformUUID" = "XXXXXXXX-XXXX-..."
                parts = line.split("=", 1)
                if len(parts) == 2:
                    uuid = parts[1].strip().strip('"')
                    if uuid:
                        return "MAC-" + uuid.upper()
    except Exception:
        pass
    return None


def macos_total_ram_gb() -> float | None:
    """حافظه‌ی فیزیکی کل (گیگابایت) روی مک؛ None اگر نشد."""
    if not is_macos():
        return None
    try:
        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return int(out) / (1024 ** 3)
    except Exception:
        return None


_KEYCHAIN_SERVICE = "IASViewer"


def _security() -> str | None:
    if not is_macos():
        return None
    return shutil.which("security")


def macos_keychain_available() -> bool:
    return _security() is not None


def macos_keychain_set(account: str, secret: str) -> bool:
    """ذخیره‌ی رمز در Keychain کاربر جاری. True اگر موفق بود."""
    sec = _security()
    if not sec:
        return False
    try:
        r = subprocess.run(
            [sec, "add-generic-password", "-U",
             "-s", _KEYCHAIN_SERVICE, "-a", account, "-w", secret],
            capture_output=True, timeout=15,
        )
        return r.returncode == 0
    except Exception:
        return False


def macos_keychain_get(account: str) -> str | None:
    """خواندن رمز از Keychain کاربر جاری؛ None اگر پیدا نشد."""
    sec = _security()
    if not sec:
        return None
    try:
        r = subprocess.run(
            [sec, "find-generic-password",
             "-s", _KEYCHAIN_SERVICE, "-a", account, "-w"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            val = r.stdout.strip()
            return val if val else None
    except Exception:
        pass
    return None


def macos_keychain_delete(account: str) -> bool:
    sec = _security()
    if not sec:
        return False
    try:
        r = subprocess.run(
            [sec, "delete-generic-password",
             "-s", _KEYCHAIN_SERVICE, "-a", account],
            capture_output=True, timeout=15,
        )
        return r.returncode == 0
    except Exception:
        return False


def macos_msgbox(text: str, title: str = "IAS Viewer") -> None:
    """نمایش دیالوگ خطا روی مک (جایگزین MessageBoxW)."""
    if not is_macos():
        return
    try:
        # نقل‌قول برای AppleScript
        t = str(text).replace("\\", "\\\\").replace('"', '\\"')
        ti = str(title).replace("\\", "\\\\").replace('"', '\\"')
        subprocess.run(
            ["osascript", "-e",
             f'display dialog "{t}" with title "{ti}" buttons {{"باشه"}} '
             f'default button "باشه" with icon stop'],
            capture_output=True, timeout=30,
        )
    except Exception:
        pass


def macos_open(path: str) -> bool:
    """باز کردن فایل/پوشه با برنامه‌ی پیش‌فرض مک (جایگزین os.startfile)."""
    if not is_macos():
        return False
    try:
        r = subprocess.run(["open", path], capture_output=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False
