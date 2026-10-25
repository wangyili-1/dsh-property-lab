"""Verify fixture I/O and cleanup, recording whether Windows restricts the token."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys

from fixture_directory import fixture_directory


def restricted_token():
    if os.name != "nt":
        return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.IsTokenRestricted.argtypes = [wintypes.HANDLE]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return bool(advapi.IsTokenRestricted(token))
    finally:
        kernel.CloseHandle(token)


def main():
    result = {"python": sys.version.split()[0], "restricted_token": restricted_token()}
    with fixture_directory() as directory:
        if os.name == "nt":
            quoted = str(directory).replace("'", "''")
            command = f"$a=Get-Acl -LiteralPath '{quoted}'; @{{protected=$a.AreAccessRulesProtected;inherited_rules=@($a.Access | Where-Object IsInherited).Count}} | ConvertTo-Json -Compress"
            acl = subprocess.run(["pwsh.exe", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True)
            result["acl"] = json.loads(acl.stdout)
            assert not result["acl"]["protected"]
            assert result["acl"]["inherited_rules"] > 0
        first, second = directory / "first.txt", directory / "second.txt"
        first.write_text("synthetic fixture", encoding="utf-8")
        first.replace(second)
        assert second.read_text(encoding="utf-8") == "synthetic fixture"
        second.unlink()
        result["create_write_rename_read_unlink"] = True
    result["directory_removed"] = not directory.exists()
    assert result["directory_removed"]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
