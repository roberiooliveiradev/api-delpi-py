from fastapi import APIRouter, HTTPException, Query
from app.services.system_service import (
    get_table,
    get_tables,
    get_columns_table,
    search_table_by_description,  # ✅ importar o novo service
)
from app.core.responses import success_response, error_response
from app.core.exceptions import DatabaseConnectionError, BusinessLogicError
from app.utils.logger import log_info, log_error

from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from app.config import settings

from app.models.system_model import LoginRequest

router = APIRouter()



# ----------------------------
# 🔍 4️⃣ Busca de tabelas por descrição (nova rota)
# ----------------------------
@router.get("/tables/search", summary="Busca tabelas por descrição (SX2)")
def search_tables(
    description: str = Query(..., min_length=2, description="Descrição parcial ou completa da tabela"),
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(20, ge=1, le=200, description="Quantidade de registros por página")
):
    """
    Busca tabelas do Protheus (SX2010) pela descrição (X2_NOME),
    com suporte a múltiplas palavras, variações de LIKE e paginação.
    """
    log_info(f"Iniciando busca de tabelas com descrição semelhante a '{description}' (página {page}, limite {limit})")
    try:
        result = search_table_by_description(description=description, page=page, limit=limit)
        return success_response(
            data=result,
            message="Busca de tabelas realizada com sucesso!"
        )
    except BusinessLogicError as e:
        log_error(f"Nenhuma tabela encontrada para '{description}': {e}")
        return error_response(str(e))
    except DatabaseConnectionError as e:
        log_error(f"Erro de conexão ao buscar tabelas: {e}")
        return error_response(f"Erro de conexão com o banco de dados: {e}")
    except Exception as e:
        log_error(f"Erro inesperado ao buscar tabelas com descrição '{description}': {e}")
        return error_response(f"Erro inesperado: {e}")






# ----------------------------
# 📘 1️⃣ Listagem de tabelas
# ----------------------------
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


# ----------------------------
# 📘 2️⃣ Busca de tabela por nome
# ----------------------------
@router.get("/tables/{tableName}", summary="Consulta informações de tabela")
def table(tableName: str):
    try:
        result = get_table(tableName)
        return success_response(
            data=result,
            message="Tabela localizada com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao consultar informações da tabela {tableName}: {e}")
        return error_response(f"Erro inesperado: {e}")


# ----------------------------
# 📘 3️⃣ Consulta colunas de tabela
# ----------------------------
@router.get("/tables/{tableName}/columns", summary="Consulta colunas de tabela")
def table_columns(tableName: str):
    try:
        result = get_columns_table(tableName)
        return success_response(
            data=result,
            message="Colunas da tabela retornadas com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao consultar colunas da tabela {tableName}: {e}")
        return error_response(f"Erro inesperado: {e}")



# ----------------------------
# 🔐 5️⃣ Login simples
# ----------------------------
VALID_USER = settings.DB_USER
VALID_PASS = settings.DB_PASSWORD

@router.post("/login", summary="Autenticação simples (gera token JWT)")
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
