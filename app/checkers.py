from __future__ import annotations

import platform
import re
import socket
import subprocess
import time
from dataclasses import dataclass

import requests


@dataclass
class CheckResult:
    is_success: bool
    status: str
    latency_ms: float | None
    http_code: int | None
    error_msg: str | None


def http_check(target: str, timeout_sec: int, keyword: str | None) -> CheckResult:
    start = time.perf_counter()
    try:
        response = requests.get(target, timeout=timeout_sec, allow_redirects=True)
        latency_ms = (time.perf_counter() - start) * 1000
        body = response.text or ""

        if keyword and keyword not in body:
            return CheckResult(
                is_success=False,
                status="abnormal",
                latency_ms=latency_ms,
                http_code=response.status_code,
                error_msg=f"keyword not found: {keyword}",
            )

        status = "online" if latency_ms <= timeout_sec * 1000 else "slow"
        return CheckResult(
            is_success=True,
            status=status,
            latency_ms=latency_ms,
            http_code=response.status_code,
            error_msg=None,
        )
    except requests.RequestException as exc:
        return CheckResult(
            is_success=False,
            status="offline",
            latency_ms=None,
            http_code=None,
            error_msg=str(exc),
        )


def tcp_check(target: str, timeout_sec: int) -> CheckResult:
    if ":" not in target:
        return CheckResult(False, "abnormal", None, None, "target must be host:port")

    host, port_text = target.rsplit(":", 1)
    try:
        port = int(port_text)
    except ValueError:
        return CheckResult(False, "abnormal", None, None, "invalid TCP port")

    start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        sock.connect((host, port))
        latency_ms = (time.perf_counter() - start) * 1000
        status = "online" if latency_ms <= timeout_sec * 1000 else "slow"
        return CheckResult(True, status, latency_ms, None, None)
    except OSError as exc:
        return CheckResult(False, "offline", None, None, str(exc))
    finally:
        sock.close()


def ping_check(target: str, timeout_sec: int) -> CheckResult:
    host = target.strip()
    if not host:
        return CheckResult(False, "abnormal", None, None, "target host is empty")

    timeout_ms = max(1000, int(timeout_sec * 1000))
    if platform.system().lower().startswith("win"):
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        timeout_arg = str(max(1, int(timeout_sec)))
        cmd = ["ping", "-c", "1", "-W", timeout_arg, host]

    start = time.perf_counter()
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec + 2)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(False, "offline", None, None, str(exc))

    latency_ms = (time.perf_counter() - start) * 1000
    output = f"{completed.stdout}\n{completed.stderr}"
    parsed = _parse_ping_latency(output)
    if parsed is not None:
        latency_ms = parsed

    if completed.returncode == 0:
        status = "online" if latency_ms <= timeout_sec * 1000 else "slow"
        return CheckResult(True, status, latency_ms, None, None)
    return CheckResult(False, "offline", None, None, output.strip() or "ping failed")


def zufe_route_check(target: str, timeout_sec: int) -> CheckResult:
    host = (target.strip() or "www.zufe.edu.cn").replace("http://", "").replace("https://", "").strip("/")
    start = time.perf_counter()
    try:
        _, _, ip_list = socket.gethostbyname_ex(host)
    except OSError as exc:
        return CheckResult(False, "offline", None, None, str(exc))

    latency_ms = (time.perf_counter() - start) * 1000
    ips = sorted(set(ip_list))
    if any(ip.startswith("172.") for ip in ips):
        status = "online" if latency_ms <= timeout_sec * 1000 else "slow"
        return CheckResult(True, status, latency_ms, None, f"internal route resolved: {','.join(ips)}")
    if any(ip.startswith("202.") for ip in ips):
        return CheckResult(False, "offline", latency_ms, None, f"external route resolved: {','.join(ips)}")

    return CheckResult(False, "abnormal", latency_ms, None, f"unexpected route resolved: {','.join(ips)}")


def _parse_ping_latency(output: str) -> float | None:
    lower = output.lower()
    if "time<" in lower:
        return 1.0

    match_ms = re.search(r"time[=<]\s*([0-9.]+)\s*ms", lower)
    if match_ms:
        return float(match_ms.group(1))

    match_time = re.search(r"time[=<]\s*([0-9.]+)", lower)
    if match_time:
        return float(match_time.group(1))
    return None


