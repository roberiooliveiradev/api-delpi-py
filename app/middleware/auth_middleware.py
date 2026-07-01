import os

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse

from app.middleware.gpt_api_token import request_has_valid_gpt_api_token

PUBLIC_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/system/login",
}


def is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True

    if path.startswith("/products/") and path.endswith("/structure/excel"):
        return True

    return False


def _unauthorized(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"success": False, "message": message},
    )


async def jwt_middleware(request: Request, call_next):
    path = request.url.path

    if is_public_path(path):
        return await call_next(request)

    if request_has_valid_gpt_api_token(request):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return _unauthorized(
            "Token não informado. Use Bearer com GPT_API_TOKEN (agente) "
            "ou JWT de /system/login."
        )

    token = auth_header.replace("Bearer ", "").strip()
    jwt_secret = os.getenv("JWT_SECRET", "secret")

    try:
        jwt.decode(token, jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return _unauthorized(
            "Token JWT expirado. Gere um novo em /system/login "
            "ou use GPT_API_TOKEN no Custom GPT."
        )
    except jwt.InvalidTokenError:
        return _unauthorized(
            "Token inválido. Verifique GPT_API_TOKEN ou JWT de /system/login."
        )

    return await call_next(request)
