# app/routes/system_routes.py
from fastapi import APIRouter, HTTPException, Query
from app.services.system_service import get_table, get_tables
from app.core.responses import success_response, error_response
from app.core.exceptions import DatabaseConnectionError
from app.utils.logger import log_info, log_error

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