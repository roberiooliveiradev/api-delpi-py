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
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "text/plain": {
                    "schema": {"type": "string"},
                    "example": "SELECT TOP 3 * FROM SB1010 WHERE D_E_L_E_T_ = '';"
                }
            }
        }
    },
)

async def execute_sql_raw(request: Request):
    """
    Recebe SQL puro (text/plain) — permite colar a query completa no Swagger com quebras de linha.
    """
    try:
        # ✅ Força leitura bruta do corpo como texto (corrige AttributeError)
        sql_text = (await request.body()).decode("utf-8").strip()

        if not sql_text:
            return error_response("Corpo vazio — nenhum SQL foi recebido.")

        result = run_raw_sql(sql_text)
        if result.get("success"):
            return success_response(data=result, message="Consulta SQL executada com sucesso.")
        else:
            return error_response(result.get("message", "Erro na execução."))
    except Exception as e:
        log_error(f"[DATA_SQL] Erro inesperado: {e}")
        return error_response(str(e))

