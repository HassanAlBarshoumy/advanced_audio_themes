# coding: utf-8

# This file is covered by the GNU General Public License.

import ctypes
import ctypes.wintypes
import threading
import time

import wx

from logHandler import log

# Win32 constants
WM_USER = 0x0400
WM_DEVICECHANGE = 0x0219
WM_POWERBROADCAST = 0x0218
WM_TIMER = 0x0113
WM_QUIT = 0x0012
WM_CREATE = 0x0001
WM_DESTROY = 0x0002

DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVTYP_DEVICEINTERFACE = 0x0005
DBT_DEVTYP_VOLUME = 0x0002

PBT_APMPOWERSTATUSCHANGE = 0x000A
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMSUSPEND = 0x0004

# GUID for USB devices (DEVINTERFACE_USB_DEVICE)
GUID_DEVINTERFACE_USB_DEVICE = (
    0xA5DCBF10, 0x6530, 0x11D2,
    0x90, 0x1F, 0x00, 0xC0, 0x4F, 0xB9, 0x51, 0xED
)

# GUID for all device interfaces (allows any device type)
GUID_DEVINTERFACE_ALL = (
    0x4d36e96c, 0xe325, 0x11ce,
    0xbf, 0xc1, 0x08, 0x00, 0x2b, 0xe1, 0x03, 0x18
)

DEVICE_NOTIFY_WINDOW_HANDLE = 0x0000
DEVICE_NOTIFY_ALL_INTERFACE_CLASSES = 0x0004

DBTF_MEDIA = 0x0001
DBTF_NET = 0x0002


class DEV_BROADCAST_HDR(ctypes.Structure):
    _fields_ = [
        ("dbch_size", ctypes.wintypes.DWORD),
        ("dbch_devicetype", ctypes.wintypes.DWORD),
        ("dbch_reserved", ctypes.wintypes.DWORD),
    ]


class DEV_BROADCAST_DEVICEINTERFACE(ctypes.Structure):
    _fields_ = [
        ("dbcc_size", ctypes.wintypes.DWORD),
        ("dbcc_devicetype", ctypes.wintypes.DWORD),
        ("dbcc_reserved", ctypes.wintypes.DWORD),
        ("dbcc_classguid", ctypes.c_byte * 16),
        ("dbcc_name", ctypes.wintypes.WCHAR * 256),
    ]


class DEV_BROADCAST_VOLUME(ctypes.Structure):
    _fields_ = [
        ("dbcv_size", ctypes.wintypes.DWORD),
        ("dbcv_devicetype", ctypes.wintypes.DWORD),
        ("dbcv_reserved", ctypes.wintypes.DWORD),
        ("dbcv_unitmask", ctypes.wintypes.DWORD),
        ("dbcv_flags", ctypes.wintypes.WORD),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.wintypes.DWORD),
        ("Data2", ctypes.wintypes.WORD),
        ("Data3", ctypes.wintypes.WORD),
        ("Data4", ctypes.c_byte * 8),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_int, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p
)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("style", ctypes.wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.wintypes.HINSTANCE),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
        ("hIconSm", ctypes.c_void_p),
    ]


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("Reserved1", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.wintypes.DWORD),
        ("BatteryFullLifeTime", ctypes.wintypes.DWORD),
    ]


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class SystemStatusMonitor:
    _battery_timer_id = 1
    _network_timer_id = 2

    def __init__(self, callback):
        self._callback = lambda *args: wx.CallAfter(callback, *args)
        self._running = False
        self._thread = None
        self._hwnd = None
        self._usb_notify_handle = None
        self._volume_notify_handle = None
        self._last_ac_state = None
        self._last_network_state = None
        self._last_battery_percent = None
        self._battery_check_interval = 30000
        self._network_check_interval = 15000
        self._update_intervals_from_config()

    def _update_intervals_from_config(self):
        try:
            from config import conf
            self._network_check_interval = int(
                conf["audiothemes"].get("sys_network_check_interval", 15)
            ) * 1000
            self._battery_check_interval = int(
                conf["audiothemes"].get("sys_battery_check_interval", 30)
            ) * 1000
        except Exception:
            pass

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def _run(self):
        hinstance = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = WNDPROC(self._window_proc)
        wc.hInstance = hinstance
        wc.lpszClassName = "AudioThemesSystemStatus"
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            log.debugWarning("SystemStatusMonitor: RegisterClassExW failed")
            return

        self._hwnd = user32.CreateWindowExW(
            0, atom, "AudioThemesSystemStatus", 0,
            0, 0, 0, 0,
            0xFFFF,
            0, hinstance, 0
        )
        if not self._hwnd:
            log.debugWarning("SystemStatusMonitor: CreateWindowExW failed")
            return

        self._register_device_notifications()

        self._update_intervals_from_config()
        user32.SetTimer(self._hwnd, self._battery_timer_id, self._battery_check_interval, 0)
        user32.SetTimer(self._hwnd, self._network_timer_id, self._network_check_interval, 0)

        self._check_ac_status()
        self._check_battery_level()
        self._check_network_status()

        msg = ctypes.wintypes.MSG()
        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        self._unregister_device_notifications()
        self._hwnd = None

    def _register_device_notifications(self):
        try:
            from .handler import SpecialProps
            from config import conf
        except Exception:
            return
        use_all_usb = conf["audiothemes"].get("sys_all_usb", True)

        # Register for USB device interface notifications (all USB devices)
        if use_all_usb:
            usb_guid = GUID()
            usb_guid.Data1 = GUID_DEVINTERFACE_USB_DEVICE[0]
            usb_guid.Data2 = GUID_DEVINTERFACE_USB_DEVICE[1]
            usb_guid.Data3 = GUID_DEVINTERFACE_USB_DEVICE[2]
            for i in range(8):
                usb_guid.Data4[i] = GUID_DEVINTERFACE_USB_DEVICE[3 + i]

            dbcc = DEV_BROADCAST_DEVICEINTERFACE()
            dbcc.dbcc_size = ctypes.sizeof(DEV_BROADCAST_DEVICEINTERFACE)
            dbcc.dbcc_devicetype = DBT_DEVTYP_DEVICEINTERFACE
            dbcc.dbcc_reserved = 0
            ctypes.memmove(
                ctypes.byref(dbcc.dbcc_classguid),
                ctypes.byref(usb_guid),
                16
            )
            self._usb_notify_handle = user32.RegisterDeviceNotificationW(
                self._hwnd,
                ctypes.byref(dbcc),
                DEVICE_NOTIFY_WINDOW_HANDLE
            )
            if not self._usb_notify_handle:
                log.debugWarning("SystemStatusMonitor: RegisterDeviceNotificationW (USB) failed")

        # Register for storage volume notifications
        vol_hdr = DEV_BROADCAST_HDR()
        vol_hdr.dbch_size = ctypes.sizeof(DEV_BROADCAST_HDR)
        vol_hdr.dbch_devicetype = DBT_DEVTYP_VOLUME
        vol_hdr.dbch_reserved = 0
        self._volume_notify_handle = user32.RegisterDeviceNotificationW(
            self._hwnd,
            ctypes.byref(vol_hdr),
            DEVICE_NOTIFY_WINDOW_HANDLE
        )
        if not self._volume_notify_handle:
            log.debugWarning("SystemStatusMonitor: RegisterDeviceNotificationW (Volume) failed")

    def _unregister_device_notifications(self):
        if self._usb_notify_handle:
            user32.UnregisterDeviceNotification(self._usb_notify_handle)
            self._usb_notify_handle = None
        if self._volume_notify_handle:
            user32.UnregisterDeviceNotification(self._volume_notify_handle)
            self._volume_notify_handle = None

    def _window_proc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_DEVICECHANGE:
                self._on_device_change(wparam, lparam)
            elif msg == WM_POWERBROADCAST:
                self._on_power_broadcast(wparam, lparam)
            elif msg == WM_TIMER:
                self._on_timer(wparam)
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
        except Exception as e:
            log.debugWarning(f"SystemStatusMonitor: window proc error: {e}")
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _on_device_change(self, wparam, lparam):
        try:
            from .handler import SpecialProps
        except Exception:
            return
        if not lparam:
            return
        try:
            hdr = DEV_BROADCAST_HDR.from_address(lparam)
        except Exception:
            return

        if hdr.dbch_devicetype == DBT_DEVTYP_DEVICEINTERFACE and self._usb_notify_handle:
            if wparam == DBT_DEVICEARRIVAL:
                self._callback(SpecialProps.sys_usb_plug)
            elif wparam == DBT_DEVICEREMOVECOMPLETE:
                self._callback(SpecialProps.sys_usb_unplug)

        elif hdr.dbch_devicetype == DBT_DEVTYP_VOLUME and self._volume_notify_handle:
            if wparam == DBT_DEVICEARRIVAL:
                self._callback(SpecialProps.sys_volume_plug)
            elif wparam == DBT_DEVICEREMOVECOMPLETE:
                self._callback(SpecialProps.sys_volume_unplug)

    def _on_power_broadcast(self, wparam, lparam):
        try:
            from .handler import SpecialProps
        except Exception:
            return

        if wparam == PBT_APMPOWERSTATUSCHANGE:
            self._check_ac_status()
            self._check_battery_level()
        elif wparam == PBT_APMSUSPEND:
            self._callback(SpecialProps.sys_sleep)
        elif wparam == PBT_APMRESUMEAUTOMATIC:
            self._callback(SpecialProps.sys_wake)
            self._check_ac_status()
            self._check_battery_level()
            self._check_network_status()

    def _on_timer(self, timer_id):
        if timer_id == self._battery_timer_id:
            self._check_ac_status()
            self._check_battery_level()
        elif timer_id == self._network_timer_id:
            self._check_network_status()

    def _check_ac_status(self):
        try:
            from .handler import SpecialProps
        except Exception:
            return
        try:
            sps = SYSTEM_POWER_STATUS()
            ret = kernel32.GetSystemPowerStatus(ctypes.byref(sps))
            if not ret:
                return
            ac_state = sps.ACLineStatus
            if self._last_ac_state is None:
                self._last_ac_state = ac_state
                return
            if ac_state != self._last_ac_state:
                self._last_ac_state = ac_state
                if ac_state == 1:
                    self._callback(SpecialProps.sys_ac_plug)
                elif ac_state == 0:
                    self._callback(SpecialProps.sys_ac_unplug)
        except Exception as e:
            log.debugWarning(f"SystemStatusMonitor: _check_ac_status error: {e}")

    def _check_battery_level(self):
        try:
            from .handler import SpecialProps
            from config import conf
        except Exception:
            return
        try:
            sps = SYSTEM_POWER_STATUS()
            ret = kernel32.GetSystemPowerStatus(ctypes.byref(sps))
            if not ret:
                return
            percent = sps.BatteryLifePercent
            if percent == 255:
                return
            low_threshold = int(conf["audiothemes"].get("sys_battery_low_threshold", 20))
            critical_threshold = int(conf["audiothemes"].get("sys_battery_critical_threshold", 10))

            if self._last_battery_percent is not None:
                if percent <= critical_threshold < self._last_battery_percent:
                    self._callback(SpecialProps.sys_battery_critical)
                elif percent <= low_threshold < self._last_battery_percent:
                    self._callback(SpecialProps.sys_battery_low)

            if percent >= 99:
                if sps.ACLineStatus == 1:
                    if self._last_battery_percent is not None and self._last_battery_percent < 99:
                        self._callback(SpecialProps.sys_battery_full)

            self._last_battery_percent = percent
        except Exception as e:
            log.debugWarning(f"SystemStatusMonitor: _check_battery_level error: {e}")

    def _check_network_status(self):
        try:
            from .handler import SpecialProps
        except Exception:
            return
        try:
            INTERNET_CONNECTION_MODEM = 1
            INTERNET_CONNECTION_LAN = 2
            INTERNET_CONNECTION_PROXY = 4
            INTERNET_CONNECTION_RAS = 8
            flags = ctypes.wintypes.DWORD(0)
            result = ctypes.windll.wininet.InternetGetConnectedState(
                ctypes.byref(flags), 0
            )
            connected = bool(result)

            if self._last_network_state is None:
                self._last_network_state = connected
                return

            if connected != self._last_network_state:
                self._last_network_state = connected
                if connected:
                    self._callback(SpecialProps.sys_network_connect)
                else:
                    self._callback(SpecialProps.sys_network_disconnect)
        except Exception as e:
            log.debugWarning(f"SystemStatusMonitor: _check_network_status error: {e}")
