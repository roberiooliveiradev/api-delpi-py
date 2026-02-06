from fastapi import APIRouter, HTTPException, Query
from app.services.system_service import (
    get_table,
    get_tables,
    get_columns_table,
    get_table_indexes,
    get_table_relations,
    get_table_schema,
    search_columns_in_table,
    search_table_by_description, 
    search_columns_by_description,
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
# Busca de tabela por nome
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
# Consulta colunas de tabela
# ----------------------------
@router.get("/tables/{tableName}/columns", summary="Consulta colunas de tabela com paginação")
def table_columns(
    tableName: str,
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(50, ge=1, le=200, description="Quantidade de registros por página")
):
    """
    Retorna colunas da tabela (SX3010) com suporte à paginação, total e totalPages.
    """
    log_info(f"Consultando colunas da tabela {tableName} (página {page}, limite {limit})")
    try:
        result = get_columns_table(tableName, page, limit)
        return success_response(
            data=result,
            message=f"Colunas da tabela {tableName} retornadas com sucesso!"
        )
    except BusinessLogicError as e:
        log_error(f"Nenhuma coluna encontrada para '{tableName}': {e}")
        return error_response(str(e))
    except Exception as e:
        log_error(f"Erro ao consultar colunas da tabela {tableName}: {e}")
        return error_response(f"Erro inesperado: {e}")
    
# ----------------------------
# Consulta indices
# ----------------------------
@router.get("/tables/{tableName}/indexes", summary="Consulta índices (SIX010)")
def table_indexes(tableName: str):
    try:
        result = get_table_indexes(tableName)
        return success_response(result, "Índices retornados com sucesso!")
    except Exception as e:
        return error_response(str(e))
    
# ----------------------------
# Consulta relacionamentos
# ----------------------------
@router.get("/tables/{tableName}/relations", summary="Consulta relacionamentos (SX9010)")
def table_relations(tableName: str):
    try:
        result = get_table_relations(tableName)
        return success_response(result, "Relacionamentos retornados com sucesso!")
    except Exception as e:
        return error_response(str(e))
    
# ----------------------------
# Consulta schema
# ----------------------------
@router.get("/tables/{tableName}/schema", summary="Schema completo da tabela (SX2, SX3, SIX, SX9)")
def table_schema(tableName: str):
    try:
        result = get_table_schema(tableName)
        return success_response(result, "Schema completo retornado!")
    except Exception as e:
        return error_response(str(e))

# ----------------------------
# Consulta schema
# ----------------------------
@router.get("/tables/{tableName}/columns/search", summary="Buscar colunas por texto")
def search_columns(tableName: str, q: str = Query(..., min_length=2)):
    try:
        result = search_columns_in_table(tableName, q)
        return success_response(result, f"Colunas contendo '{q}' retornadas!")
    except Exception as e:
        return error_response(str(e))

# ----------------------------
# Busca global de colunas por descrição
# ----------------------------
@router.get(
    "/columns/search",
    summary="Busca colunas por descrição (SX3010 + ranking semântico)"
)
def search_columns_global(
    description: str = Query(
        ...,
        min_length=2,
        description="Texto descritivo da coluna (ex: 'Amarração produto fornecedor')"
    ),
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(20, ge=1, le=200, description="Quantidade de registros por página")
):
    """
    Busca colunas em todas as tabelas do Protheus com base na descrição,
    utilizando ranking de similaridade textual.
    """
    log_info(
        f"Iniciando busca global de colunas por descrição '{description}' "
        f"(página {page}, limite {limit})"
    )

    try:
        result = search_columns_by_description(
            description=description,
            page=page,
            limit=limit
        )

        return success_response(
            data=result,
            message="Busca de colunas realizada com sucesso!"
        )

    except BusinessLogicError as e:
        log_error(f"Nenhuma coluna encontrada: {e}")
        return error_response(str(e))
    except DatabaseConnectionError as e:
        log_error(f"Erro de conexão ao buscar colunas: {e}")
        return error_response(f"Erro de conexão com o banco de dados: {e}")
    except Exception as e:
        log_error(f"Erro inesperado ao buscar colunas: {e}")
        return error_response(f"Erro inesperado: {e}")

# ----------------------------
# Login simples
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