# app/routes/system_routes.py
from fastapi import APIRouter, HTTPException, Query
from app.services.system_service import get_table, get_tables
from app.core.responses import success_response, error_response
from app.core.exceptions import DatabaseConnectionError
from app.utils.logger import log_info, log_error

from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from app.config import settings

from app.models.system_model import LoginRequest

router = APIRouter()

@router.get("/tables", summary="Listagem de tabelas com paginação")
def tables(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(50, ge=1, le=200, description="Quantidade de registros por página")
):
    """
    Retorna uma lista paginada de tabelas do Protheus.
    """
    try:
        result = get_tables(page=page, limit=limit)
        return success_response(
            data=result,
            message="Listagem paginada realizada com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao listar tabelas: {e}")
        return error_response(f"Erro inesperado: {e}")


@router.get("/tables/{tableName}", summary="Consulta colunas de tabela")
def table(tableName: str):
    try:
        result = get_table(tableName)
        return success_response(
            data=result,
            message="Tabela localizado com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao consultar colunas da tabela {tableName}: {e}")
        return error_response(f"Erro inesperado: {e}")

# Usuário do banco
VALID_USER = settings.DB_USER
VALID_PASS = settings.DB_PASSWORD

@router.post("/login")
def login(data: LoginRequest):
    if data.username != VALID_USER or data.password != VALID_PASS:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    payload = {
        "sub": data.username,
        "exp": datetime.utcnow() + timedelta(hours=8760),
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    return {
        "success": True,
        "message": "Login efetuado com sucesso.",
        "token": token
    }