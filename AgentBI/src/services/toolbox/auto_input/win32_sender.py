from __future__ import annotations

import ctypes
import sys


class UnsupportedDesktopError(RuntimeError):
    pass


class Win32UnicodeSender:
    _INPUT_KEYBOARD = 1
    _KEYEVENTF_KEYUP = 0x0002
    _KEYEVENTF_UNICODE = 0x0004
    _VK_RETURN = 0x0D

    @staticmethod
    def ensure_supported() -> None:
        if sys.platform != "win32":
            raise UnsupportedDesktopError("自动输入仅支持 Windows 桌面会话")

    def send_character(self, character: str) -> None:
        self.ensure_supported()
        if character == "\n":
            self._send_key(self._VK_RETURN, 0, 0)
            self._send_key(self._VK_RETURN, 0, self._KEYEVENTF_KEYUP)
            return
        for offset in range(0, len(character.encode("utf-16-le")), 2):
            unit = int.from_bytes(character.encode("utf-16-le")[offset:offset + 2], "little")
            self._send_key(0, unit, self._KEYEVENTF_UNICODE)
            self._send_key(0, unit, self._KEYEVENTF_UNICODE | self._KEYEVENTF_KEYUP)

    def _send_key(self, virtual_key: int, scan_code: int, flags: int) -> None:
        from ctypes import wintypes

        ULONG_PTR = wintypes.WPARAM

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = (
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            )

        class INPUT_UNION(ctypes.Union):
            _fields_ = (("ki", KEYBDINPUT),)

        class INPUT(ctypes.Structure):
            _anonymous_ = ("union",)
            _fields_ = (("type", wintypes.DWORD), ("union", INPUT_UNION))

        event = INPUT(
            type=self._INPUT_KEYBOARD,
            ki=KEYBDINPUT(virtual_key, scan_code, flags, 0, 0),
        )
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        user32.SendInput.restype = wintypes.UINT
        if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT)) != 1:
            raise ctypes.WinError(ctypes.get_last_error())

