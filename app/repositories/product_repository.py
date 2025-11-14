# app/repositories/product_repository.py
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import BusinessLogicError
from app.utils.logger import log_info, log_error
from typing import Optional
from datetime import datetime

class ProductRepository(BaseRepository):
    """
    Repositório responsável por consultas na tabela SG1010 (estrutura) e SB1010 (produtos).
    """

    def get_product_by_code(self, code: str) -> dict:
        log_info(f"Consultando produto {code} no Protheus...")
        query = """
            SELECT *
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

    # -------------------------------
    # 🔹 ESTRUTURA (BOM)
    # -------------------------------
    def list_structure(self, code: str, max_depth: int = 10, page: int = 1, page_size: int = 50) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")
        if not 1 <= max_depth <= 50:
            raise ValueError("max_depth must be between 1 and 50")

        log_info(f"CTE estrutura (parametrizado) for {code} depth={max_depth} page={page} size={page_size}")
        offset = (page - 1) * page_size

        # Contagem total
        count_query = """
            WITH RECURSIVE_BOM AS (
                SELECT G1_COD AS parentCode, G1_COMP AS componentCode, G1_QUANT AS quantity, 1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT c.G1_COD, c.G1_COMP, c.G1_QUANT, p.level + 1
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            )
            SELECT COUNT(*) AS total FROM RECURSIVE_BOM;
        """
        total_row = self.execute_one(count_query, (code, max_depth))
        total_rows = int(total_row["total"] or 0)

        # Dados detalhados com JOIN na SB1010 (descrições)
        data_query = """
            WITH RECURSIVE_BOM AS (
                SELECT G1_COD AS parentCode, G1_COMP AS componentCode, G1_QUANT AS quantity, 1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT c.G1_COD, c.G1_COMP, c.G1_QUANT, p.level + 1
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            )
            SELECT 
                rb.parentCode,
                pdesc.B1_DESC AS parentDesc,
                rb.componentCode,
                cdesc.B1_DESC AS componentDesc,
                rb.quantity,
                rb.level
            FROM RECURSIVE_BOM rb
            LEFT JOIN SB1010 pdesc WITH (NOLOCK)
                ON pdesc.B1_COD = rb.parentCode AND pdesc.D_E_L_E_T_ = ''
            LEFT JOIN SB1010 cdesc WITH (NOLOCK)
                ON cdesc.B1_COD = rb.componentCode AND cdesc.D_E_L_E_T_ = ''
            ORDER BY rb.level, rb.parentCode, rb.componentCode
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
        """
        rows = self.execute_query(data_query, (code, max_depth, offset, page_size))

        data = [
            {
                "parentCode": (r["parentCode"] or "").strip(),
                "parentDesc": (r["parentDesc"] or "").strip(),
                "componentCode": (r["componentCode"] or "").strip(),
                "componentDesc": (r["componentDesc"] or "").strip(),
                "quantity": float(r["quantity"] or 0),
                "level": int(r["level"]),
            }
            for r in rows
        ]

        hierarchy = self._build_hierarchy(data, code, mode="structure")
        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "data": hierarchy,
        }


    # -------------------------------
    # 🔹 PARENTS (WHERE USED)
    # -------------------------------
    def list_parents(self, code: str, max_depth: int = 10, page: int = 1, page_size: int = 50) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")
        if not 1 <= max_depth <= 50:
            raise ValueError("max_depth must be between 1 and 50")

        log_info(f"CTE parents (parametrizado) for {code} depth={max_depth} page={page} size={page_size}")
        offset = (page - 1) * page_size

        # Contagem total
        count_query = """
            WITH RECURSIVE_PARENTS AS (
                SELECT G1_COD AS parentCode, G1_COMP AS childCode, G1_QUANT AS quantity, 1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COMP = ?

                UNION ALL

                SELECT c.G1_COD, p.parentCode, c.G1_QUANT, p.level + 1
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_PARENTS p ON p.parentCode = c.G1_COMP
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            )
            SELECT COUNT(*) AS total FROM RECURSIVE_PARENTS;
        """
        total_row = self.execute_one(count_query, (code, max_depth))
        total_rows = int(total_row["total"] or 0)

        # Dados detalhados com descrições
        data_query = """
            WITH RECURSIVE_PARENTS AS (
                SELECT G1_COD AS parentCode, G1_COMP AS childCode, G1_QUANT AS quantity, 1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COMP = ?

                UNION ALL

                SELECT c.G1_COD, p.parentCode, c.G1_QUANT, p.level + 1
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_PARENTS p ON p.parentCode = c.G1_COMP
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            )
            SELECT 
                rp.parentCode,
                pdesc.B1_DESC AS parentDesc,
                rp.childCode,
                cdesc.B1_DESC AS childDesc,
                rp.quantity,
                rp.level
            FROM RECURSIVE_PARENTS rp
            LEFT JOIN SB1010 pdesc WITH (NOLOCK)
                ON pdesc.B1_COD = rp.parentCode AND pdesc.D_E_L_E_T_ = ''
            LEFT JOIN SB1010 cdesc WITH (NOLOCK)
                ON cdesc.B1_COD = rp.childCode AND cdesc.D_E_L_E_T_ = ''
            ORDER BY rp.level, rp.parentCode
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
        """
        rows = self.execute_query(data_query, (code, max_depth, offset, page_size))

        data = [
            {
                "parentCode": (r["parentCode"] or "").strip(),
                "parentDesc": (r["parentDesc"] or "").strip(),
                "childCode": (r["childCode"] or "").strip(),
                "childDesc": (r["childDesc"] or "").strip(),
                "quantity": float(r["quantity"] or 0),
                "level": int(r["level"]),
            }
            for r in rows
        ]

        hierarchy = self._build_hierarchy(data, code, mode="parents")
        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "data": hierarchy,
        }

    # -------------------------------
    # 🔹 SUPPLIERS
    # -------------------------------
    def list_suppliers(self, code: str, page: int = 1, page_size: int = 50) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        log_info(f"Listando fornecedores de {code}, página {page}, tamanho {page_size}")
        offset = (page - 1) * page_size

        # Contagem total
        count_query = """
            SELECT COUNT(*) AS total
            FROM SA5010 AS SA5
            WHERE SA5.D_E_L_E_T_ = ''
            AND SA5.A5_PRODUTO = ?
        """
        total_row = self.execute_one(count_query, (code,))
        total_rows = int(total_row["total"] or 0)

        # Consulta paginada
        query = """
            SELECT *
            FROM SA5010 AS SA5
            WHERE SA5.D_E_L_E_T_ = ''
            AND SA5.A5_PRODUTO = ?
            ORDER BY SA5.A5_FORNECE
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        data = self.execute_query(query, (code, offset, page_size))

        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "data": data
        }
    
    # -------------------------------
    # 🔹 INBOUND INVOICE ITEMS (Notas Fiscais de Entrada)
    # -------------------------------
    def list_inbound_invoice_items(
        self,
        code: str,
        page: int = 1,
        page_size: int = 50,
        issue_date_start: Optional[str] = None,
        issue_date_end: Optional[str] = None,
        supplier: Optional[str] = None,
        branch: Optional[str] = None
    ) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        offset = (page - 1) * page_size
        log_info(f"Listando NF-es de entrada de {code}, página {page}, filtros aplicados.")

        filters = []
        params = [code]

        if issue_date_start:
            filters.append("SD1.D1_EMISSAO >= ?")
            issue_date_start = self._convert_date_to_protheus(issue_date_start)
            params.append(issue_date_start)
        if issue_date_end:
            filters.append("SD1.D1_EMISSAO <= ?")
            issue_date_end = self._convert_date_to_protheus(issue_date_end)
            params.append(issue_date_end)
        if supplier:
            filters.append("SD1.D1_FORNECE = ?")
            params.append(supplier)
        if branch:
            filters.append("SD1.D1_FILIAL = ?")
            params.append(branch)

        where_clause = " AND ".join(filters)
        if where_clause:
            where_clause = " AND " + where_clause

        # Contagem total
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM SD1010 AS SD1
            WHERE SD1.D_E_L_E_T_ = ''
              AND SD1.D1_COD = ? {where_clause}
        """
        total_row = self.execute_one(count_query, tuple(params))
        total_rows = int(total_row["total"] or 0)

        # Dados paginados
        query = f"""
            SELECT 
                SD1.*,
                SA2.A2_NOME AS supplier_name
            FROM SD1010 AS SD1
            LEFT JOIN SA2010 AS SA2
                ON SA2.A2_COD = SD1.D1_FORNECE AND SA2.D_E_L_E_T_ = ''
            WHERE SD1.D_E_L_E_T_ = ''
              AND SD1.D1_COD = ? {where_clause}
            ORDER BY SD1.D1_EMISSAO DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        params.extend([offset, page_size])
        data = self.execute_query(query, tuple(params))

        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "filters": {
                "issue_date_start": issue_date_start,
                "issue_date_end": issue_date_end,
                "supplier": supplier,
                "branch": branch
            },
            "data": data
        }

    # -------------------------------
    # 🔹 OUTBOUND INVOICE ITEMS (Notas Fiscais de Saída)
    # -------------------------------
    def list_outbound_invoice_items(
        self,
        code: str,
        page: int = 1,
        page_size: int = 50,
        issue_date_start: Optional[str] = None,
        issue_date_end: Optional[str] = None,
        customer: Optional[str] = None,
        branch: Optional[str] = None
    ) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        offset = (page - 1) * page_size
        log_info(f"Listando NF-es de saída de {code}, página {page}, filtros aplicados.")

        filters = []
        params = [code]

        if issue_date_start:
            filters.append("SD2.D2_EMISSAO >= ?")
            issue_date_start = self._convert_date_to_protheus(issue_date_start)
            params.append(issue_date_start)
        if issue_date_end:
            filters.append("SD2.D2_EMISSAO <= ?")
            issue_date_end = self._convert_date_to_protheus(issue_date_end)
            params.append(issue_date_end)
        if customer:
            filters.append("SD2.D2_CLIENTE = ?")
            params.append(customer)
        if branch:
            filters.append("SD2.D2_FILIAL = ?")
            params.append(branch)

        where_clause = " AND ".join(filters)
        if where_clause:
            where_clause = " AND " + where_clause

        # Contagem total
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM SD2010 AS SD2
            WHERE SD2.D_E_L_E_T_ = ''
              AND SD2.D2_COD = ? {where_clause}
        """
        total_row = self.execute_one(count_query, tuple(params))
        total_rows = int(total_row["total"] or 0)

        # Dados paginados
        query = f"""
            SELECT 
                SD2.*,
                SA1.A1_NOME AS customer_name
            FROM SD2010 AS SD2
            LEFT JOIN SA1010 AS SA1
                ON SA1.A1_COD = SD2.D2_CLIENTE AND SA1.D_E_L_E_T_ = ''
            WHERE SD2.D_E_L_E_T_ = ''
              AND SD2.D2_COD = ? {where_clause}
            ORDER BY SD2.D2_EMISSAO DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        params.extend([offset, page_size])
        data = self.execute_query(query, tuple(params))

        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "filters": {
                "issue_date_start": issue_date_start,
                "issue_date_end": issue_date_end,
                "customer": customer,
                "branch": branch
            },
            "data": data
        }


    # -------------------------------
    # 🔹 STOCK (SB2010)
    # -------------------------------
    def list_stock(
        self,
        code: str,
        page: int = 1,
        page_size: int = 50,
        branch: Optional[str] = None,
        location: Optional[str] = None
    ) -> dict:

        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        offset = (page - 1) * page_size
        filters = ["SB2.D_E_L_E_T_ = ''", "SB2.B2_COD = ?"]
        params = [code]

        if branch:
            filters.append("SB2.B2_FILIAL = ?")
            params.append(branch)

        if location:
            filters.append("SB2.B2_LOCAL = ?")
            params.append(location)

        where_clause = " AND ".join(filters)

        # Contagem total
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM SB2010 AS SB2
            WHERE {where_clause}
        """
        total_row = self.execute_one(count_query, tuple(params))
        total_rows = int(total_row["total"] or 0)

        # Dados paginados
        data_query = f"""
            SELECT 
                *
            FROM SB2010 AS SB2
            WHERE {where_clause}
            ORDER BY SB2.B2_FILIAL, SB2.B2_LOCAL
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        params.extend([offset, page_size])
        rows = self.execute_query(data_query, tuple(params))

        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "filters": {
                "branch": branch,
                "location": location
            },
            "data": rows
        }

    def _convert_date_to_protheus(date_str: Optional[str]) -> Optional[str]:
        """
        Converte 'YYYY-MM-DD' → 'YYYYMMDD' (padrão Protheus).
        """
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d")
        except ValueError:
            return None

    def _build_hierarchy(self, rows: list[dict], root_code: str, mode: str = "structure") -> dict:
        """
        Monta a hierarquia em formato JSON aninhado.
        mode:
            - "structure": monta árvore de componentes (pai → filhos)
            - "parents": monta árvore de produtos-pai (filho → pais)
        """
        from collections import defaultdict

        nodes = defaultdict(lambda: {"components": []})
        descriptions = {}

        for row in rows:
            if mode == "structure":
                parent = row["parentCode"]
                child = row["componentCode"]
                parentDesc = row.get("parentDesc") or ""
                childDesc = row.get("componentDesc") or ""
            else:
                # Modo 'parents'
                parent = row["parentCode"]
                child = row["childCode"]
                parentDesc = row.get("parentDesc") or ""
                childDesc = row.get("childDesc") or ""

            descriptions[parent] = parentDesc
            descriptions[child] = childDesc

            nodes[parent]["code"] = parent
            nodes[parent]["description"] = parentDesc
            nodes[parent]["quantity"] = float(row.get("quantity", 0))
            nodes[child]["code"] = child
            nodes[child]["description"] = childDesc
            nodes[child]["quantity"] = float(row.get("quantity", 0))

            # Direção da relação
            if mode == "structure":
                nodes[parent]["components"].append(nodes[child])
            else:
                # No caso dos pais, o filho é quem contém o pai
                nodes[child]["components"].append(nodes[parent])

        return nodes[root_code]
