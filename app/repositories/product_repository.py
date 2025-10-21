# app/repositories/product_repository.py
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import BusinessLogicError
from app.utils.logger import log_info

class ProductRepository(BaseRepository):
    """
    Repositório responsável por consultas na tabela SB1010 (produtos).
    """

    def get_product_by_code(self, code: str) -> dict:
        log_info(f"Consultando produto {code} no Protheus...")
        query = """
        SELECT 
        *
        FROM SB1010
        WHERE D_E_L_E_T_ = ''
          AND B1_COD = ?
        """
        product = self.execute_one(query, (code,))
        if not product:
            raise BusinessLogicError(f"Produto com código '{code}' não encontrado.")
        return product

    def list_products(self, limit: int = 10) -> list[dict]:
        log_info(f"Buscando até {limit} produtos do Protheus...")
        query = f"""
        SELECT TOP {limit} *
        FROM SB1010
        WHERE D_E_L_E_T_ = ''
        ORDER BY B1_COD
        """
        return self.execute_query(query)
