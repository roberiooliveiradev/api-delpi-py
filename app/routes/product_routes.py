from fastapi import APIRouter, HTTPException, Query
from app.services.product_service import get_product, get_products
from app.core.responses import success_response, error_response
from app.core.exceptions import DatabaseConnectionError
from app.utils.logger import log_info, log_error

router = APIRouter()

@router.get("/", summary="Listagem de produtos com limite")
def products(limit: int = Query(50, ge=1, le=200)):
    """
    Retorna uma lista de produtos com limite opcional (padrão = 10).
    """
    try:
        produtos = get_products(limit)
        return success_response(
            data={"total": len(produtos), "produtos": [p.model_dump(by_alias=True) for p in produtos]},
            message="Listagem realizada com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao listar produtos: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get("/{code}", summary="Consulta produto por código")
def product(code: str):
    try:
        produto = get_product(code)
        return success_response(
            data={"produto": produto.model_dump(by_alias=True)},
            message="Produto localizado com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao consultar produto {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

