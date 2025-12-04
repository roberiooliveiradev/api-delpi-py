from app.repositories.data_repository import DataRepository
from app.utils.logger import log_info, log_error
from app.core.exceptions import DatabaseConnectionError


def run_dynamic_query(payload: dict) -> dict:
    """
    Serviço de execução da consulta dinâmica.
    Não modifica o payload; toda a lógica está no DataRepository.
    """
    repo = DataRepository()
    log_info("Executando consulta dinâmica genérica (data_service)")

    try:
        return repo.execute_dynamic_query(payload)
    except Exception as e:
        log_error(f"Erro ao executar consulta dinâmica: {e}")
        raise DatabaseConnectionError(str(e))

def run_raw_sql(sql: str) -> dict:
    """
    Executa SQL bruto validado (somente SELECT em tabelas autorizadas).
    """
    log_info("[DATA_SQL] Executando consulta SQL segura")
    repo = DataRepository()
    try:
        return repo.execute_raw_sql_safe(sql)
    except Exception as e:
        log_error(f"[DATA_SQL] Erro na execução: {e}")
        return {"success": False, "message": str(e)}