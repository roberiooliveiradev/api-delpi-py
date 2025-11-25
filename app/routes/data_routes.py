from fastapi import APIRouter, Request
from app.services.data_service import run_dynamic_query
from app.models.data_query_model import DataQueryRequest
from app.core.responses import success_response, error_response
from app.utils.logger import log_info, log_error

router = APIRouter()


@router.post("/query", summary="Consulta genérica (CTE, aliases, agregações, filtros, paginação)")
async def query_tables(request: Request, req: DataQueryRequest):
    """
    Executa consultas dinâmicas com suporte a:
    - Múltiplas CTEs (WITH ...)
    - Tabelas/CTEs com alias
    - Filtros recursivos (AND/OR)
    - Agrupamento, agregações, auto_aggregate
    - Ordenação e paginação (apenas na consulta principal)
    """
    try:
        if hasattr(req, "model_dump"):
            payload = req.model_dump(exclude_none=True, by_alias=True)
        else:
            payload = req.dict(exclude_none=True, by_alias=True)

        cfg = request.app.state.agent_config

        if cfg.get("auto_execute_api", True):
            result = run_dynamic_query(payload)
            return success_response(
                data=result,
                message="Consulta executada automaticamente."
            )

        if cfg.get("confirm_before_request", False):
            return success_response(
                data=payload,
                message="Confirmar envio desta consulta?"
            )

        if cfg.get("show_payload_before_execute", False):
            return success_response(
                data=payload,
                message="Payload antes da execução."
            )

        result = run_dynamic_query(payload)
        return success_response(
            data=result,
            message="Consulta executada com sucesso."
        )

    except Exception as e:
        log_error(f"Erro ao executar consulta dinâmica: {e}")
        return error_response(str(e))
