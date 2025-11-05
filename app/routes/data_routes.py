from fastapi import APIRouter, Request
from app.services.data_service import run_dynamic_query
from app.models.data_query_model import DataQueryRequest, FilterGroupInternal
from app.core.responses import success_response, error_response
from app.utils.logger import log_info, log_error

router = APIRouter()


@router.post("/query", summary="Consulta genérica de tabelas com paginação e filtros")
async def query_tables(request: Request, req: DataQueryRequest):
    """
    Executa consultas dinâmicas com suporte a:
    - múltiplas tabelas e aliases (ex: 'SB1010 AS P', 'SB2010 AS E')
    - filtros (operadores =, >, <, LIKE, IN, BETWEEN, IS NULL)
    - agrupamento e agregações
    - ordenação e paginação
    - execução automática configurável (sem confirmação)
    """
    try:
        # Compatível com Pydantic v1/v2
        payload = (
            req.model_dump(exclude_none=True, by_alias=True)
            if hasattr(req, "model_dump")
            else req.dict(exclude_none=True, by_alias=True)
        )

        # 🔹 Reconstrói modelo recursivo de filtros internos (AND/OR)
        if payload.get("filters"):
            try:
                filters_internal = FilterGroupInternal.model_validate(payload["filters"])
                payload["filters"] = filters_internal.model_dump(by_alias=True, exclude_none=True)
            except Exception as e:
                log_error(f"Falha ao validar filtros recursivos: {e}")

        # 🔹 Lê configurações globais do agente
        cfg = request.app.state.agent_config

        # --- Comportamento de execução ---
        if cfg.get("auto_execute_api", True):
            result = run_dynamic_query(payload)
            return success_response(
                data=result,
                message=f"Consulta executada automaticamente — página {result['page']} de {result['pages']}."
            )

        # --- Caso o modo automático esteja desativado ---
        if cfg.get("confirm_before_request", False):
            return success_response(
                data=payload,
                message="Confirma envio manual do JSON antes de executar?"
            )

        # --- Exibe payload antes da execução (modo depuração) ---
        if cfg.get("show_payload_before_execute", False):
            return success_response(
                data=payload,
                message="Visualização do payload antes da execução (modo depuração)."
            )

        # --- Fallback: executa normalmente ---
        result = run_dynamic_query(payload)
        return success_response(
            data=result,
            message=f"Consulta executada com sucesso — página {result['page']} de {result['pages']}."
        )

    except Exception as e:
        log_error(f"Erro ao executar consulta dinâmica: {e}")
        return error_response(str(e))
