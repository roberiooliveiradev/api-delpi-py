from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse
from app.services.data_service import run_dynamic_query, run_raw_sql
from app.models.data_query_model import DataQueryRequestOpenAPI, RawSqlRequest
from app.core.responses import success_response, error_response
from app.utils.logger import log_info, log_error

router = APIRouter()


@router.post("/query", summary="Consulta genérica (CTE, aliases, agregações, filtros, paginação)")
async def query_tables(request: Request, req: DataQueryRequestOpenAPI):
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

@router.post(
    "/sql",
    summary="Executa SQL puro (somente SELECT, com CTE e recursivo permitido).",
    response_class=JSONResponse,
)
async def execute_sql_raw(
    body: str = Body(
        ...,
        media_type="text/plain",
        description="Cole aqui o SQL completo, com quebras de linha e tabs (tipo text/plain).",
        openapi_extra={
            "examples": [
                {
                    "summary": "Exemplo com CTE recursiva",
                    "description": "Consulta hierárquica com WITH RECURSIVE (ou WITH para SQL Server).",
                    "value": """WITH hierarchy AS (
    SELECT B1_COD, B1_GRUPO, 0 AS LEVEL
    FROM SB1010
    WHERE B1_GRUPO = '1008'
  UNION ALL
    SELECT p.B1_COD, p.B1_GRUPO, h.LEVEL + 1
    FROM SB1010 p
    JOIN hierarchy h ON p.B1_GRUPO = h.B1_COD
)
SELECT * FROM hierarchy;"""
                }
            ]
        },
    ),
):
    """
    Recebe SQL puro (text/plain) — permite colar a query completa no Swagger com quebras de linha.
    """
    try:
        result = run_raw_sql(body)
        if result.get("success"):
            return success_response(data=result, message="Consulta SQL executada com sucesso.")
        else:
            return error_response(result.get("message", "Erro na execução."))
    except Exception as e:
        return error_response(str(e))
