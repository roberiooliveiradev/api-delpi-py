# app/repositories/product_repository.py
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import BusinessLogicError
from app.utils.logger import log_info, log_error, log_warning

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

    def list_structure(self, code: str, level: int = 1, visited: set[str] | None = None) -> list[dict]:
        """
        Retorna recursivamente a estrutura (BOM) do produto,
        incluindo quantidade e nível hierárquico.
        Protege contra loops infinitos causados por referências circulares.
        """
        if visited is None:
            visited = set()

        # Se já visitamos esse código, interrompe a recursão para evitar loop
        if code in visited:
            log_info(f"Estrutura circular detectada para o produto {code}, interrompendo recursão.")
            return []

        visited.add(code)

        log_info(f"Buscando estrutura (nível {level}) do produto {code}")
        query = """
            SELECT G1_COD, G1_COMP, G1_QUANT, G1_NIV
            FROM SG1010
            WHERE D_E_L_E_T_ = ''
            AND G1_COD = ?
        """
        items = self.execute_query(query, (code,))
        structure = []

        for item in items:
            comp_code = item["G1_COMP"]
            quantity = item["G1_QUANT"]
            level_in_bom = item["G1_NIV"]

            try:
                # Busca os dados do componente
                component = {
                    "parentCode": item["G1_COD"],
                    "componentCode": comp_code,
                    "quantity": quantity,
                    "level": level_in_bom,
                }

                # Busca subcomponentes (recursivo)
                subcomponents = self.list_structure(comp_code, level + 1, visited)
                if subcomponents:
                    component["components"] = subcomponents
                    component["totalNestedComponents"] = len(subcomponents)

                structure.append(component)
            except BusinessLogicError:
                log_info(f"Componente {comp_code} não encontrado, ignorando...")

        # Adiciona a contagem total de componentes no nível atual
        for s in structure:
            s["totalComponentsAtLevel"] = len(structure)

        return structure
    
    def list_parents(self, code: str, level: int = 1, visited: set[str] | None = None) -> list[dict]:
        """
        Recursively returns all parent products (G1_COD) where the given component is used.
        Optimized version returning only SG1010 data, with hierarchical counts.
        """
        if visited is None:
            visited = set()

        if code in visited:
            log_info(f"Circular relationship detected for product {code}, stopping recursion.")
            return []

        visited.add(code)
        log_info(f"Fetching parent products (level {level}) for component {code}")

        query = """
            SELECT G1_COD, G1_COMP, G1_QUANT, G1_NIV
            FROM SG1010
            WHERE D_E_L_E_T_ = ''
            AND G1_COMP = ?
        """
        items = self.execute_query(query, (code,))
        parents = []

        for item in items:
            parent_code = item["G1_COD"]

            parent = {
                "parentCode": parent_code,
                "childCode": item["G1_COMP"],
                "quantity": item["G1_QUANT"],
                "level": item["G1_NIV"],
            }

            # Recursive call for higher-level parents
            higher_parents = self.list_parents(parent_code, level + 1, visited)
            if higher_parents:
                parent["parents"] = higher_parents
                parent["totalNestedParents"] = len(higher_parents)

            parents.append(parent)

        # Add count of parents at this level
        for p in parents:
            p["totalParentsAtLevel"] = len(parents)

        return parents