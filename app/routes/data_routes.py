from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse
from app.services.data_service import run_raw_sql
from app.models.data_query_model import DataQueryRequestOpenAPI, RawSqlRequest
from app.core.responses import success_response, error_response
from app.utils.logger import log_info, log_error

router = APIRouter()

@router.post(
    "/sql",
    summary="Executa SQL puro (somente SELECT, com CTE e recursivo permitido).",
    response_class=JSONResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                # 🔹 Opção 1: Envio JSON
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "Instrução SQL bruta (somente SELECT, pode conter quebras de linha)."
                            }
                        },
                        "required": ["sql"]
                    },
                    "example": {
                        "sql": "SELECT TOP 3 * FROM SB1010 WHERE D_E_L_E_T_ = '';"
                    }
                },
                # 🔹 Opção 2: Envio texto puro
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
    Executa SQL puro, aceitando `application/json` (campo 'sql') ou `text/plain`.

    - Permite colar a query diretamente no Swagger.
    - Compatível com agentes que enviam JSON.
    """
    try:
        content_type = request.headers.get("content-type", "").lower()

        # 🔹 1️⃣ JSON → {"sql": "SELECT ..."}
        if "application/json" in content_type:
            payload = await request.json()
            sql_text = payload.get("sql", "").strip() if isinstance(payload, dict) else ""
        
        # 🔹 2️⃣ Texto puro → "SELECT ..."
        else:
            sql_text = (await request.body()).decode("utf-8").strip()

        # 🔒 Validação mínima
        if not sql_text:
            return error_response("Corpo vazio — nenhum SQL foi recebido.")

        # 🔹 Execução segura
        result = run_raw_sql(sql_text)
        if result.get("success"):
            return success_response(data=result, message="Consulta SQL executada com sucesso.")
        else:
            return error_response(result.get("message", "Erro na execução."))

    except Exception as e:
        log_error(f"[DATA_SQL] Erro inesperado: {e}")
        return error_response(str(e))

