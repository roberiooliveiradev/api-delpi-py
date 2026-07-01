"""Token fixo para Custom GPT / integrações (Bearer ou X-Api-Key)."""

from __future__ import annotations

import os
import secrets

from fastapi import Request

GPT_API_TOKEN_ENV = "GPT_API_TOKEN"


def configured_gpt_api_token() -> str | None:
    value = (os.getenv(GPT_API_TOKEN_ENV) or "").strip()
    return value or None


def extract_presented_api_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "", 1).strip()
        return token or None

    api_key = (request.headers.get("X-Api-Key") or "").strip()
    return api_key or None


def request_has_valid_gpt_api_token(request: Request) -> bool:
    expected = configured_gpt_api_token()
    if not expected:
        return False
    presented = extract_presented_api_token(request)
    if not presented:
        return False
    return secrets.compare_digest(presented, expected)
