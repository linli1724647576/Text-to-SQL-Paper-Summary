#!/usr/bin/env python3
"""OpenAlex API helpers shared by crawlers."""

import os
import urllib.parse

from http_utils import get_json


OPENALEX_API_BASE = "https://api.openalex.org"


def openalex_api_key():
    return os.environ.get("OPENALEX_API_KEY", "").strip()


def openalex_url(endpoint, params=None):
    query = dict(params or {})
    api_key = openalex_api_key()
    if api_key:
        query["api_key"] = api_key
    return endpoint + ("?" + urllib.parse.urlencode(query) if query else "")


def sanitize_openalex_url(url):
    parsed = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    sanitized = [("api_key", "REDACTED") if key == "api_key" else (key, value) for key, value in pairs]
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode(sanitized),
            parsed.fragment,
        )
    )


def get_openalex_json(endpoint, params=None, *, timeout=20):
    url = openalex_url(endpoint, params)
    try:
        return get_json(url, timeout=timeout)
    except Exception as exc:
        raise RuntimeError(f"OpenAlex request failed: {sanitize_openalex_url(url)}: {exc}") from None


def abstract_from_inverted_index(index):
    if not index:
        return ""
    positions = []
    for word, offsets in index.items():
        for offset in offsets:
            positions.append((offset, word))
    return " ".join(word for _, word in sorted(positions))
