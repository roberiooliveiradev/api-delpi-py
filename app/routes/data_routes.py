# app/routes/data_routes.py

from fastapi import APIRouter
from app.services.data_service import run_dynamic_query
from app.models.data_query_model import DataQueryRequest, FilterGroupInternal
from app.core.responses import success_response, error_response
from app.utils.logger import log_info, log_error

router = APIRouter()


@router.post("/query", summary="Consulta genérica de tabelas com paginação e filtros")
def query_tables(req: DataQueryRequest):
    """
    Executa consultas dinâmicas com suporte a:
    - múltiplas tabelas
    - filtros (operadores =, >, <, LIKE, IN)
    - ordenação
    - paginação (OFFSET / FETCH)
    """
    try:
        # Compatível com Pydantic v1/v2
        payload = (
            req.model_dump(exclude_none=True, by_alias=True)
            if hasattr(req, "model_dump")
            else req.dict(exclude_none=True, by_alias=True)
        )

        # 🔹 Reconstrói modelo recursivo internamente
        if payload.get("filters"):
            try:
                filters_internal = FilterGroupInternal.model_validate(payload["filters"])
                payload["filters"] = filters_internal.model_dump(by_alias=True, exclude_none=True)
            except Exception as e:
                log_error(f"Falha ao validar filtros recursivos: {e}")

        result = run_dynamic_query(payload)
        return success_response(
            data=result,
            message=f"Consulta executada com sucesso — página {result['page']} de {result['pages']}."
        )

    except Exception as e:
        log_error(f"Erro ao executar consulta dinâmica: {e}")
        return error_response(str(e))
