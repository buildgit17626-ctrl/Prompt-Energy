"""Observed host metadata; recording versions never starts an energy tracker."""

import ctypes
import importlib.metadata
import platform
import struct
import sys
import uuid
import winreg

import psutil


class PowerStatus(ctypes.Structure):
    _fields_ = [
        ("ac", ctypes.c_ubyte),
        ("flag", ctypes.c_ubyte),
        ("percent", ctypes.c_ubyte),
        ("reserved", ctypes.c_ubyte),
        ("life", ctypes.c_ulong),
        ("full", ctypes.c_ulong),
    ]


def host_metadata() -> dict:
    """Preserve actual AC/overlay observations instead of assuming the owner's setting."""
    status = PowerStatus()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetSystemPowerStatus.argtypes = [ctypes.POINTER(PowerStatus)]
    ac = int(status.ac) if kernel.GetSystemPowerStatus(ctypes.byref(status)) else None
    # Overlay API writes a GUID into caller storage (unlike GetActiveScheme).
    guid = (ctypes.c_ubyte * 16)()
    power = ctypes.WinDLL("powrprof")
    power.PowerGetEffectiveOverlayScheme.argtypes = [ctypes.POINTER(ctypes.c_ubyte * 16)]
    power.PowerGetEffectiveOverlayScheme.restype = ctypes.c_ulong
    code = power.PowerGetEffectiveOverlayScheme(ctypes.byref(guid))
    overlay = None
    if code == 0:
        overlay = str(uuid.UUID(bytes_le=bytes(guid)))
    modes = {
        "ded574b5-45a0-4f42-8737-46345c09c238": "Best performance",
        "961cc777-2547-4f9d-8174-7d86181b8a7a": "Better battery",
        "00000000-0000-0000-0000-000000000000": "Balanced",
    }
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
    ) as key:
        cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    libraries = {
        name: importlib.metadata.version(name)
        for name in (
            "numpy",
            "pandas",
            "scipy",
            "matplotlib",
            "codecarbon",
            "psutil",
            "pytest",
            "ruff",
        )
    }
    return {
        "python": platform.python_version(),
        "python_full": sys.version,
        "bits": struct.calcsize("P") * 8,
        "os": platform.platform(),
        "cpu_model": cpu,
        "ram_bytes": psutil.virtual_memory().total,
        "libraries": libraries,
        "ac_line_status": ac,
        "power_overlay_guid": overlay,
        "power_api_result": code,
        "power_mode": modes.get(overlay, f"unknown:{overlay}"),
    }
