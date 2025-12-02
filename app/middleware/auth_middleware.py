from fastapi import Request
from fastapi.responses import JSONResponse
import jwt
from app.config import settings

PUBLIC_PATHS = {
    "/", 
    "/docs", 
    "/redoc", 
    "/openapi.json",
    "/system/login"
}

def is_public_path(path: str) -> bool:
    # Caminhos públicos fixos
    if path in PUBLIC_PATHS:
        return True

    # Rota pública para exportação Excel
    if path.startswith("/products/") and path.endswith("/structure/excel"):
        return True

    return False


async def jwt_middleware(request: Request, call_next):
    path = request.url.path

    # Permite caminhos públicos
    if is_public_path(path):
        return await call_next(request)

    # Lê o header Authorization
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Token JWT não informado."}
        )

    token = auth_header.replace("Bearer ", "").strip()

    try:
        jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Token expirado. Gere um novo em docs/system/login."}
        )
    except jwt.InvalidTokenError:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Token inválido."}
        )


    return await call_next(request)
