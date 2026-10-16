"""Minimal Win32 Job Object wrapper; no third-party process-control dependency."""

import ctypes as c
import os
from ctypes import wintypes as w


class BasicLimits(c.Structure):
    _fields_ = [
        ("ProcessTime", c.c_int64),
        ("JobTime", c.c_int64),
        ("Flags", w.DWORD),
        ("MinWorkingSet", c.c_size_t),
        ("MaxWorkingSet", c.c_size_t),
        ("ActiveProcesses", w.DWORD),
        ("Affinity", c.c_size_t),
        ("Priority", w.DWORD),
        ("Scheduling", w.DWORD),
    ]


class IoCounters(c.Structure):
    _fields_ = [
        (name, c.c_uint64)
        for name in ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")
    ]


class ExtendedLimits(c.Structure):
    _fields_ = [
        ("Basic", BasicLimits),
        ("Io", IoCounters),
        ("ProcessMemory", c.c_size_t),
        ("JobMemory", c.c_size_t),
        ("PeakProcessMemory", c.c_size_t),
        ("PeakJobMemory", c.c_size_t),
    ]


class WindowsJob:
    """A single-process job with a commit-memory cap and kill-on-close."""

    def __init__(self, memory_bytes: int) -> None:
        if os.name != "nt":
            raise OSError("The P1 sandbox requires Windows")
        self.api = c.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([c.c_void_p, w.LPCWSTR], w.HANDLE),
            "SetInformationJobObject": ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
            "QueryInformationJobObject": (
                [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p],
                w.BOOL,
            ),
            "OpenProcess": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
            "CloseHandle": ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes = args
            function.restype = result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise c.WinError(c.get_last_error())
        limits = ExtendedLimits()
        # ACTIVE_PROCESS | PROCESS_MEMORY | KILL_ON_JOB_CLOSE; no breakaway.
        limits.Basic.Flags = 0x8 | 0x100 | 0x2000
        limits.Basic.ActiveProcesses = 1
        limits.ProcessMemory = memory_bytes
        if not self.api.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
            error = c.WinError(c.get_last_error())
            self.close()
            raise error

    def assign(self, pid: int) -> None:
        """Attach the worker before its input gate is released."""
        process = self.api.OpenProcess(0x100 | 0x1, False, pid)  # SET_QUOTA | TERMINATE
        if not process:
            raise c.WinError(c.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, process):
                raise c.WinError(c.get_last_error())
        finally:
            self.api.CloseHandle(process)

    def peak_memory(self) -> int:
        """Query the OS-recorded peak committed bytes, including between polls."""
        limits = ExtendedLimits()
        if not self.api.QueryInformationJobObject(
            self.handle,
            9,
            c.byref(limits),
            c.sizeof(limits),
            None,
        ):
            raise c.WinError(c.get_last_error())
        return limits.PeakProcessMemory

    def close(self) -> None:
        """Closing the sole handle terminates any remaining job process."""
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None
