#!/usr/bin/env python3
"""HTTP helpers with bounded retry for metadata crawlers."""

import json
import socket
import time
import urllib.error
import urllib.request
from http.client import RemoteDisconnected


DEFAULT_USER_AGENT = "Text2SQL-Paper-Summary/1.0 (mailto:example@example.com)"
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def is_retryable_status(status):
    return status in RETRY_STATUS_CODES


def retry_sleep(attempt, base_delay=1.0, max_delay=30.0):
    delay = min(max_delay, base_delay * (2 ** max(0, attempt - 1)))
    time.sleep(delay)


def request(
    url,
    *,
    method="GET",
    data=None,
    headers=None,
    timeout=20,
    attempts=4,
    base_delay=1.0,
):
    request_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if headers:
        request_headers.update(headers)
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if not is_retryable_status(exc.code) or attempt == attempts:
                raise
        except (urllib.error.URLError, RemoteDisconnected, TimeoutError, socket.timeout) as exc:
            last_error = exc
            if attempt == attempts:
                raise
        retry_sleep(attempt, base_delay=base_delay)
    if last_error:
        raise last_error
    raise RuntimeError(f"request failed without response: {url}")


def get_text(url, *, timeout=20, headers=None, attempts=4, base_delay=1.0):
    return request(
        url,
        timeout=timeout,
        headers=headers,
        attempts=attempts,
        base_delay=base_delay,
    ).decode("utf-8", errors="ignore")


def get_json(url, *, timeout=20, headers=None, attempts=4, base_delay=1.0):
    return json.loads(
        get_text(
            url,
            timeout=timeout,
            headers=headers,
            attempts=attempts,
            base_delay=base_delay,
        )
    )


def post_json(url, payload, *, timeout=30, headers=None, attempts=4, base_delay=1.0):
    body = json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)
    return json.loads(
        request(
            url,
            method="POST",
            data=body,
            headers=merged_headers,
            timeout=timeout,
            attempts=attempts,
            base_delay=base_delay,
        ).decode("utf-8", errors="ignore")
    )
