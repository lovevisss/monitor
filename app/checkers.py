from __future__ import annotations

import socket
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

