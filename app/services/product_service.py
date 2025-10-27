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

def get_structure(code: str) -> dict:
    """
    Retorna a estrutura (BOM) completa de um produto de forma recursiva,
    incluindo quantidade e nível hierárquico.
    """
    repo = ProductRepository()
    log_info(f"Buscando estrutura recursiva do produto {code}")
    try:
        structure = repo.list_structure(code)
        total = len(structure)
        return {"totalComponents": total, "components": structure}
    except Exception as e:
        log_error(f"Erro ao listar estrutura recursiva do produto {code}: {e}")
        raise DatabaseConnectionError(str(e))

    
def get_parents(code: str) -> dict:
    """
    Retorna recursivamente os produtos pai (Where Used) de forma otimizada,
    incluindo contagem total de pais.
    """
    repo = ProductRepository()
    log_info(f"Buscando produtos pai (Where Used) para o código {code}")
    try:
        parents = repo.list_parents(code)
        total = len(parents)
        return {"totalParents": total, "parents": parents}
    except Exception as e:
        log_error(f"Erro ao listar produtos pai do componente {code}: {e}")
        raise DatabaseConnectionError(str(e))

