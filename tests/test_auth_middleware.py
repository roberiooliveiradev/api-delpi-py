"""Autenticação — GPT_API_TOKEN fixo e JWT legado."""

from __future__ import annotations

import os
from unittest.mock import patch

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.auth_middleware import jwt_middleware


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(jwt_middleware)

    @app.get("/")
    def root():
        return {"status": "online"}

    @app.get("/protected")
    def protected():
        return {"success": True}

    return app


def test_public_root_without_token():
    client = TestClient(_build_test_app())
    response = client.get("/")
    assert response.status_code == 200


def test_protected_route_requires_token():
    client = TestClient(_build_test_app())
    response = client.get("/protected")
    assert response.status_code == 401


def test_protected_route_accepts_gpt_api_token_bearer():
    with patch.dict(os.environ, {"GPT_API_TOKEN": "gpt-fixed-token"}, clear=False):
        client = TestClient(_build_test_app())
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer gpt-fixed-token"},
        )
        assert response.status_code == 200


def test_protected_route_accepts_gpt_api_token_x_api_key():
    with patch.dict(os.environ, {"GPT_API_TOKEN": "gpt-fixed-token"}, clear=False):
        client = TestClient(_build_test_app())
        response = client.get(
            "/protected",
            headers={"X-Api-Key": "gpt-fixed-token"},
        )
        assert response.status_code == 200


def test_protected_route_accepts_jwt_when_gpt_token_configured():
    with patch.dict(
        os.environ,
        {"GPT_API_TOKEN": "gpt-fixed-token", "JWT_SECRET": "test-secret"},
        clear=False,
    ):
        token = jwt.encode({"sub": "user"}, "test-secret", algorithm="HS256")
        client = TestClient(_build_test_app())
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


def test_wrong_gpt_token_rejected():
    with patch.dict(os.environ, {"GPT_API_TOKEN": "gpt-fixed-token"}, clear=False):
        client = TestClient(_build_test_app())
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401
