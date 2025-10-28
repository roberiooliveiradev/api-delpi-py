# app/services/system_service.py

from app.repositories.system_repository import SystemRepository
from app.models.product_model import Product
from app.utils.logger import log_info, log_error
from app.core.exceptions import BusinessLogicError, DatabaseConnectionError

def get_table(tableName: str) -> dict:
    """
    Busca uma tabela no Protheus via repositório.
    """
    repo = SystemRepository()
    log_info(f"Iniciando consulta a tabela {tableName} via repositório")
    try:
        result = repo.get_columns_table(tableName)
        return result
    except BusinessLogicError as e:
        log_error(str(e))
        raise
    except Exception as e:
        log_error(f"Erro inesperado ao buscar tabela {tableName}: {e}")
        raise DatabaseConnectionError(str(e))


def get_tables(page: int = 1, limit: int = 10) -> list[dict]:
    """
    Lista tabelas do Protheus com suporte à paginação.
    """
    repo = SystemRepository()
    offset = (page - 1) * limit
    log_info(f"Listando tabelas (página {page}, limite {limit})...")
    try:
        results = repo.get_all_tables(limit, offset)
        return {
            "page": page,
            "limit": limit,
            "results": results
        }
    except Exception as e:
        log_error(f"Erro ao listar tabelas: {e}")
        raise DatabaseConnectionError(str(e))
