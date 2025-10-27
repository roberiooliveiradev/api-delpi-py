from fastapi import APIRouter, HTTPException, Query
from app.services.product_service import get_product, get_products, get_structure, get_parents
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

@router.get("/{code}/structure", summary="Consulta estrutura (BOM) recursiva do produto")
def structure(code: str):
    """
    Retorna a estrutura (BOM) recursiva do produto,
    com nomes de nós padronizados em inglês.
    """
    try:
        result = get_structure(code)
        return success_response(
            data={
                "product": code,
                "totalComponents": result["totalComponents"],
                "components": result["components"]
            },
            message="Estrutura recursiva carregada com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao consultar estrutura do produto {code}: {e}")
        return error_response(f"Erro inesperado: {e}")


@router.get("/{code}/parents", summary="Consulta produtos pai (onde o item é utilizado)")
def parents(code: str):
    """
    Retorna todos os produtos que utilizam o item informado na sua estrutura (recursivo),
    com contagem de pais.
    """
    try:
        result = get_parents(code)
        return success_response(
            data={
                "component": code,
                "totalParents": result["totalParents"],
                "parentProducts": result["parents"]
            },
            message="Listagem de produtos pai realizada com sucesso!"
        )
    except Exception as e:
        log_error(f"Erro ao consultar produtos pai do item {code}: {e}")
        return error_response(f"Erro inesperado: {e}")
