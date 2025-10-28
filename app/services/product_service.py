# app/services/product_service.py
from app.repositories.product_repository import ProductRepository
from app.models.product_model import Product
from app.utils.logger import log_info, log_error
from app.core.exceptions import BusinessLogicError, DatabaseConnectionError

def get_product(code: str) -> Product:
    """
    Busca um produto no Protheus via repositório e retorna um modelo Pydantic.
    """
    repo = ProductRepository()
    log_info(f"Iniciando consulta do produto {code} via repositório")
    try:
        result = repo.get_product_by_code(code)
        return Product(**result)
    except BusinessLogicError as e:
        log_error(str(e))
        raise
    except Exception as e:
        log_error(f"Erro inesperado ao buscar produto {code}: {e}")
        raise DatabaseConnectionError(str(e))


def get_products(limit: int = 10) -> list[Product]:
    """
    Lista produtos do Protheus com limite definido.
    Retorna uma lista de modelos Product.
    """
    repo = ProductRepository()
    log_info(f"Listando até {limit} produtos do Protheus...")
    try:
        results = repo.list_products(limit)
        # Converte cada linha retornada em um objeto Product
        products = [Product(**r) for r in results]
        return products
    except Exception as e:
        log_error(f"Erro ao listar produtos: {e}")
        raise DatabaseConnectionError(str(e))

def get_structure(code: str, max_depth: int = 10, page: int = 1, page_size: int = 50) -> dict:
    repo = ProductRepository()
    log_info(f"Buscando estrutura (CTE) paginada para {code}")
    try:
        return repo.list_structure(code, max_depth, page, page_size)
    except Exception as e:
        log_error(f"Erro ao listar estrutura do produto {code}: {e}")
        raise DatabaseConnectionError(str(e))


def get_parents(code: str, max_depth: int = 10, page: int = 1, page_size: int = 50) -> dict:
    repo = ProductRepository()
    log_info(f"Buscando pais (CTE) paginados para {code}")
    try:
        return repo.list_parents(code, max_depth, page, page_size)
    except Exception as e:
        log_error(f"Erro ao listar produtos pai do item {code}: {e}")
        raise DatabaseConnectionError(str(e))
