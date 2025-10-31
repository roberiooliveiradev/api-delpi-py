from fastapi import APIRouter, HTTPException, Query
from app.services.product_service import get_product, get_products, get_structure, get_parents, get_teste
from app.core.responses import success_response, error_response
from app.core.exceptions import DatabaseConnectionError
from app.utils.logger import log_info, log_error
from app.repositories.base_repository import BaseRepository

router = APIRouter()

@router.get("/", summary="Listagem de produtos com limite")
def products(limit: int = Query(50, ge=1, le=200)):
    """
    Retorna uma lista de produtos com limite opcional (padrão = 10).
    """
    try:
        products = get_products(limit)
        return success_response(
            data={"total": len(products), "produtos": [p.model_dump(by_alias=True) for p in products]},
            message="Listagem realizada com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao listar produtos: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get("/{code}", summary="Consulta produto por código")
def product(code: str):
    try:
        product = get_product(code)
        return success_response(
            data={"produto": product.model_dump(by_alias=True)},
            message="Produto localizado com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao consultar produto {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get("/{code}/structure", summary="Consulta estrutura (BOM) paginada via CTE")
def structure(
    code: str,
    max_depth: int = Query(10, ge=1, le=15),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500)
):
    """
    Retorna a estrutura (BOM) via CTE com suporte a paginação.
    """
    try:
        result = get_structure(code, max_depth, page, page_size)
        return success_response(
            data=result,
            message=f"Estrutura do produto {code} retornada com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar estrutura do produto {code}: {e}")
        return error_response(f"Erro inesperado: {e}")


@router.get("/{code}/parents", summary="Consulta produtos pai (Where Used) paginada via CTE")
def parents(
    code: str,
    max_depth: int = Query(10, ge=1, le=15),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500)
):
    """
    Retorna produtos pai (Where Used) via CTE com paginação.
    """
    try:
        result = get_parents(code, max_depth, page, page_size)
        return success_response(
            data=result,
            message=f"Produtos pai de {code} retornados com sucesso (página {page}/{result['totalPages']})."
        )
    except Exception as e:
        log_error(f"Erro ao consultar pais do item {code}: {e}")
        return error_response(f"Erro inesperado: {e}")

@router.get("/debug/teste", summary="Isso mostra se o D4_OPERAC realmente coincide com H8_OPER.")
def teste():
    try:
        result = get_teste()
        return success_response(
            data=result,
            message="Busca realizada com sucesso."
        )
    except Exception as e:
        log_error(f"Erro ao consultar. {e}")
        return error_response(f"Erro inesperado: {e}")
