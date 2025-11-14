# app/services/product_service.py
from app.repositories.product_repository import ProductRepository
from app.models.product_model import Product
from app.utils.logger import log_info, log_error
from app.core.exceptions import BusinessLogicError, DatabaseConnectionError
from typing import Optional

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

def search_products_by_description(
    description: str,
    page: int = 1,
    page_size: int = 50
) -> dict:
    repo = ProductRepository()
    log_info(f"Search only by description (page={page})")
    try:
        return repo.search_by_description(description, page, page_size)
    except Exception as e:
        log_error(f"Erro ao pesquisar produtos por descrição: {e}")
        raise DatabaseConnectionError(str(e))



def search_products_by_params(
    page: int = 1,
    page_size: int = 50,
    code: Optional[str] = None,
    description: Optional[str] = None,
    # group: Optional[str] = None
) -> dict:
    repo = ProductRepository()
    log_info(f"Buscando produtos (page={page}) com filtros aplicados")
    try:
        return repo.search_products(
            page, 
            page_size, 
            code, 
            description, 
            # group
            )
    except Exception as e:
        log_error(f"Erro ao pesquisar produtos: {e}")
        raise DatabaseConnectionError(str(e))


def search_products(
    page: int = 1,
    page_size: int = 50,
    code: Optional[str] = None,
    description: Optional[str] = None,
    group: Optional[str] = None
) -> dict:
    repo = ProductRepository()
    log_info(f"Buscando produtos (page={page}) com filtros aplicados")
    try:
        return repo.search_products(page, page_size, code, description, group)
    except Exception as e:
        log_error(f"Erro ao pesquisar produtos: {e}")
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

def get_suppliers(code: str, page: int = 1, page_size: int = 50) -> dict:
    repo = ProductRepository()
    log_info(f"Buscando fornecedores para {code} (página {page})")
    try:
        return repo.list_suppliers(code, page, page_size)
    except Exception as e:
        log_error(f"Erro ao listar fornecedores para {code}: {e}")
        raise DatabaseConnectionError(str(e))
    
def get_inbound_invoice_items(
    code: str,
    page: int = 1,
    page_size: int = 50,
    issue_date_start: Optional[str] = None,
    issue_date_end: Optional[str] = None,
    supplier: Optional[str] = None,
    branch: Optional[str] = None
) -> dict:
    repo = ProductRepository()
    log_info(f"Buscando NF-es de entrada de {code} (página {page})")
    try:
        return repo.list_inbound_invoice_items(code, page, page_size, issue_date_start, issue_date_end, supplier, branch)
    except Exception as e:
        log_error(f"Erro ao listar NF-es de entrada para {code}: {e}")
        raise DatabaseConnectionError(str(e))


def get_outbound_invoice_items(
    code: str,
    page: int = 1,
    page_size: int = 50,
    issue_date_start: Optional[str] = None,
    issue_date_end: Optional[str] = None,
    customer: Optional[str] = None,
    branch: Optional[str] = None
) -> dict:
    repo = ProductRepository()
    log_info(f"Buscando NF-es de saída de {code} (página {page})")
    try:
        return repo.list_outbound_invoice_items(code, page, page_size, issue_date_start, issue_date_end, customer, branch)
    except Exception as e:
        log_error(f"Erro ao listar NF-es de saída para {code}: {e}")
        raise DatabaseConnectionError(str(e))

def get_stock(
    code: str,
    page: int = 1,
    page_size: int = 50,
    branch: Optional[str] = None,
    location: Optional[str] = None
) -> dict:
    repo = ProductRepository()
    log_info(f"Buscando estoque para {code} (página {page})")

    try:
        return repo.list_stock(code, page, page_size, branch, location)
    except Exception as e:
        log_error(f"Erro ao listar estoque para {code}: {e}")
        raise DatabaseConnectionError(str(e))
