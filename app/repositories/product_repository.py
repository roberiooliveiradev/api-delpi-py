# app/repositories/product_repository.py
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import BusinessLogicError
from app.utils.logger import log_info, log_error
from typing import Optional
from datetime import datetime
import math
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
    # 🔹 SEACH PRODUCTS BY DESCRIPTION 
    # -------------------------------
    def search_by_description(
        self,
        description: str,
        page: int = 1,
        page_size: int = 50,
    ):
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")
        if not description:
            raise ValueError("Description cannot be empty")

        offset = (page - 1) * page_size

        # ------------------------------
        # Preparação
        # ------------------------------
        desc_clean = description.strip()
        terms = [t.strip() for t in desc_clean.split() if t.strip()]
        desc_length = len(desc_clean)

        # Padrao composto: CABO%PP%PT
        pattern = "%".join(terms) if len(terms) > 1 else desc_clean

        # =====================================================
        # WHERE otimizado + case/acento insensitive
        # =====================================================
        where_clauses = ["SB1.D_E_L_E_T_ = ''"]
        where_params = []

        # 1) Padrão composto (somente se houver mais de um termo)
        if len(terms) > 1:
            where_clauses.append("SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ?")
            where_params.append(f"%{pattern}%")

        # 2) Todos os termos (AND)
        for t in terms:
            where_clauses.append("SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ?")
            where_params.append(f"%{t}%")

        where_sql = " AND ".join(where_clauses)

        # =====================================================
        # SCORE (Ranking otimizado + case-insensitive)
        # =====================================================
        score_parts = []
        score_params = []

        # 1) Frase completa
        score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 50 ELSE 0 END")
        score_params.append(f"%{desc_clean}%")

        if len(terms) > 1:
            # 2) Padrão composto — CABO%PP%PT
            score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 40 ELSE 0 END")
            score_params.append(f"%{pattern}%")

            # 3) Pesos individuais
            for t in terms:
                score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 25 ELSE 0 END")
                score_params.append(f"{t} %")

                score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 15 ELSE 0 END")
                score_params.append(f"% {t} %")

                score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 5 ELSE 0 END")
                score_params.append(f"%{t}%")

            # Similaridade normalizada
            score_parts.append(
                f"""
                CAST(
                    CASE 
                        WHEN LEN(SB1.B1_DESC) = 0 THEN 0
                        ELSE ROUND(
                            10 * (
                                1.0 - ABS(LEN(SB1.B1_DESC) - {desc_length}) /
                                (CASE 
                                    WHEN LEN(SB1.B1_DESC) > {desc_length} THEN LEN(SB1.B1_DESC)
                                    ELSE {desc_length}
                                END)
                            ), 
                        0)
                    END
                AS INT)
                """
            )

        else:
            # Caso apenas 1 termo
            term = terms[0]

            score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 30 ELSE 0 END")
            score_params.append(f"{term} %")

            score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 20 ELSE 0 END")
            score_params.append(f"% {term} %")

            score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 10 ELSE 0 END")
            score_params.append(f"%{term}%")

            score_parts.append(
                f"""
                CAST(
                    CASE 
                        WHEN LEN(SB1.B1_DESC) = 0 THEN 0
                        ELSE ROUND(
                            10 * (
                                1.0 - ABS(LEN(SB1.B1_DESC) - {len(term)}) /
                                (CASE 
                                    WHEN LEN(SB1.B1_DESC) > {len(term)} THEN LEN(SB1.B1_DESC)
                                    ELSE {len(term)}
                                END)
                            ), 
                        0)
                    END
                AS INT)
                """
            )

        score_sql = " + ".join(score_parts)

        # =====================================================
        # COUNT
        # =====================================================
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM SB1010 AS SB1
            WHERE {where_sql}
        """
        total_rows = int(self.execute_one(count_sql, tuple(where_params))["total"] or 0)

        # =====================================================
        # RESULT QUERY
        # =====================================================
        sql = f"""
            SELECT 
                SB1.B1_COD,
                SB1.B1_DESC,
                SB1.B1_GRUPO,
                SB1.B1_TIPO,
                SB1.B1_UM,
                SB1.B1_ATIVO,
                ({score_sql}) AS relevance_score
            FROM SB1010 AS SB1
            WHERE {where_sql}
            ORDER BY relevance_score DESC, SB1.B1_COD ASC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        final_params = score_params + where_params + [offset, page_size]
        rows = self.execute_query(sql, tuple(final_params))

        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "description": description,
            "results": rows
        }

    # -------------------------------
    # 🔹 SEACH PRODUCTS BY CODE, DESCRIPTION OR GROUP
    # -------------------------------
    def search_products(
        self,
        page: int = 1,
        page_size: int = 50,
        code: Optional[str] = None,
        description: Optional[str] = None,
        group: Optional[str] = None
    ) -> dict:

        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        offset = (page - 1) * page_size

        # ============================================================
        # 🔹 WHERE BASE
        # ============================================================
        where_clauses = ["SB1.D_E_L_E_T_ = ''"]
        where_params: list[str] = []

        if code:
            where_clauses.append("SB1.B1_COD LIKE ?")
            where_params.append(f"%{code}%")

        # ============================================================
        # 🔹 DESCRIÇÃO (mesma lógica do search_by_description)
        # ============================================================
        terms = []
        desc_clean = None
        desc_length = 0

        if description:
            desc_clean = description.strip()
            terms = [t.strip() for t in desc_clean.split() if t.strip()]
            desc_length = len(desc_clean)

            pattern = "%".join(terms) if len(terms) > 1 else desc_clean

            #
            # ATENÇÃO: lógica corrigida
            #
            # Antes: tudo era AND → isso mata qualquer pesquisa
            # Agora: agrupamos corretamente em (A OR B OR C)
            #
            phrase_match = "SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ?"
            where_params.append(f"%{desc_clean}%")

            # todos os termos (AND)
            term_clauses = []
            for t in terms:
                term_clauses.append("SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ?")
                where_params.append(f"%{t}%")

            all_terms_match = "(" + " AND ".join(term_clauses) + ")"

            # padrão composto (opcional, não obrigatório)
            pattern_match = "SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ?"
            where_params.append(f"%{pattern}%")

            #
            # FINAL: a descrição agora funciona corretamente
            #
            where_clauses.append(
                "("
                f"{phrase_match} OR "
                f"{all_terms_match} OR "
                f"{pattern_match}"
                ")"
            )

        if group:
            where_clauses.append("SB1.B1_GRUPO = ?")
            where_params.append(group)

        where_sql = " AND ".join(where_clauses)

        # ============================================================
        # 🔹 COUNT
        # ============================================================
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM SB1010 AS SB1
            WHERE {where_sql}
        """
        total_rows = int(self.execute_one(count_sql, tuple(where_params))["total"] or 0)

        # ============================================================
        # 🔹 SCORE (mesma lógica do search_by_description)
        # ============================================================
        score_parts = []
        score_params = []

        enable_score = bool(description and terms)

        if enable_score:

            # 1) Frase inteira
            score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 50 ELSE 0 END")
            score_params.append(f"%{desc_clean}%")

            # 2) Padrão composto
            if len(terms) > 1:
                pattern = "%".join(terms)
                score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 40 ELSE 0 END")
                score_params.append(f"%{pattern}%")

            # 3) Pesos por termo
            for t in terms:
                score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 25 ELSE 0 END")
                score_params.append(f"{t} %")

                score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 15 ELSE 0 END")
                score_params.append(f"% {t} %")

                score_parts.append("CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 5 ELSE 0 END")
                score_params.append(f"%{t}%")

            # 4) Similaridade (normalização por tamanho)
            score_parts.append(
                f"""
                CAST(
                    CASE 
                        WHEN LEN(SB1.B1_DESC) = 0 THEN 0
                        ELSE ROUND(
                            10 * (
                                1.0 - ABS(LEN(SB1.B1_DESC) - {desc_length}) /
                                (CASE 
                                    WHEN LEN(SB1.B1_DESC) > {desc_length} THEN LEN(SB1.B1_DESC)
                                    ELSE {desc_length}
                                END)
                            ), 
                        0)
                    END
                AS INT)
                """
            )

        score_sql = " + ".join(score_parts) if enable_score else "0"

        # ============================================================
        # 🔹 RESULT QUERY
        # ============================================================
        final_sql = f"""
            SELECT 
                SB1.B1_COD,
                SB1.B1_DESC,
                SB1.B1_GRUPO,
                SB1.B1_TIPO,
                SB1.B1_ATIVO,
                SB1.B1_UM,
                ({score_sql}) AS relevance_score
            FROM SB1010 AS SB1
            WHERE {where_sql}
            ORDER BY relevance_score DESC, SB1.B1_COD ASC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        final_params = (
            score_params + where_params + [offset, page_size]
            if enable_score else
            where_params + [offset, page_size]
        )

        rows = self.execute_query(final_sql, tuple(final_params))

        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "filters": {
                "code": code,
                "description": description,
                "group": group
            },
            "params": final_params,
            "data": rows
        }

    # -------------------------------
    # 🔹 STRUCTURE (BOM)
    # -------------------------------
    def list_structure(self, code: str, max_depth: int = 5, page: int = 1, page_size: int = 100):
        """
        Retorna a estrutura (BOM) do produto em formato hierárquico,
        incluindo tipo de produto (B1_TIPO) e unidade de medida (B1_UM).
        Compatível com SQL Server.
        """

        data_query = """
            WITH RECURSIVE_BOM AS (
                SELECT 
                    G1_COD AS parentCode,
                    G1_COMP AS componentCode,
                    G1_QUANT AS quantity,
                    1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT 
                    c.G1_COD AS parentCode,
                    c.G1_COMP AS componentCode,
                    c.G1_QUANT AS quantity,
                    p.level + 1 AS level
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            )
            SELECT 
                rb.parentCode,
                pdesc.B1_DESC AS parentDesc,
                pdesc.B1_TIPO AS parentType,
                pdesc.B1_UM AS parentUM,
                rb.componentCode,
                cdesc.B1_DESC AS componentDesc,
                cdesc.B1_TIPO AS componentType,
                cdesc.B1_UM AS componentUM,
                rb.quantity,
                rb.level
            FROM RECURSIVE_BOM rb
            LEFT JOIN SB1010 pdesc WITH (NOLOCK)
                ON pdesc.B1_COD = rb.parentCode AND pdesc.D_E_L_E_T_ = ''
            LEFT JOIN SB1010 cdesc WITH (NOLOCK)
                ON cdesc.B1_COD = rb.componentCode AND cdesc.D_E_L_E_T_ = ''
            ORDER BY rb.level, rb.parentCode, rb.componentCode;
        """

        rows = self.execute_query(data_query, (code, max_depth))

        # Monta estrutura hierárquica
        items = {}
        for r in rows:
            comp = {
                "code": r["componentCode"],
                "description": r["componentDesc"],
                "type": r["componentType"],
                "unit": r["componentUM"],
                "quantity": float(r["quantity"]) if r["quantity"] is not None else 0.0,
                "components": []
            }

            parent_code = r["parentCode"]
            if parent_code not in items:
                items[parent_code] = {
                    "code": parent_code,
                    "description": r["parentDesc"],
                    "type": r["parentType"],
                    "unit": r["parentUM"],
                    "quantity": 1.0,
                    "components": []
                }
            items[parent_code]["components"].append(comp)
            items[comp["code"]] = comp

        root = items.get(code, {
            "code": code,
            "description": None,
            "type": None,
            "unit": None,
            "quantity": 1.0,
            "components": []
        })

        # Paginação somente no nível raiz
        root_components = [items[c["code"]] for c in root["components"]] if "components" in root else []
        offset = (page - 1) * page_size
        root["components"] = root_components[offset: offset + page_size]

        return {
            "success": True,
            "total": len(root_components),
            "page": page,
            "pageSize": page_size,
            "totalPages": math.ceil(len(root_components) / page_size),
            "data": root
        }
    
    # -------------------------------
    # 🔹 STRUCTURE (BOM) - FULL
    # -------------------------------
    def list_structure_full(self, code: str):
        """
        Retorna a estrutura (BOM) do produto em formato hierárquico,
        incluindo tipo de produto (B1_TIPO) e unidade de medida (B1_UM).
        Compatível com SQL Server.
        """

        data_query = """
            WITH RECURSIVE_BOM AS (
                SELECT 
                    G1_COD AS parentCode,
                    G1_COMP AS componentCode,
                    G1_QUANT AS quantity,
                    1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT 
                    c.G1_COD AS parentCode,
                    c.G1_COMP AS componentCode,
                    c.G1_QUANT AS quantity,
                    p.level + 1 AS level
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < 50
            )
            SELECT 
                rb.parentCode,
                pdesc.B1_DESC AS parentDesc,
                pdesc.B1_TIPO AS parentType,
                pdesc.B1_UM AS parentUM,
                rb.componentCode,
                cdesc.B1_DESC AS componentDesc,
                cdesc.B1_TIPO AS componentType,
                cdesc.B1_UM AS componentUM,
                rb.quantity,
                rb.level
            FROM RECURSIVE_BOM rb
            LEFT JOIN SB1010 pdesc WITH (NOLOCK)
                ON pdesc.B1_COD = rb.parentCode AND pdesc.D_E_L_E_T_ = ''
            LEFT JOIN SB1010 cdesc WITH (NOLOCK)
                ON cdesc.B1_COD = rb.componentCode AND cdesc.D_E_L_E_T_ = ''
            ORDER BY rb.level, rb.parentCode, rb.componentCode;
        """

        rows = self.execute_query(data_query, (code,))

        # Monta estrutura hierárquica
        items = {}
        for r in rows:
            comp = {
                "code": r["componentCode"],
                "description": r["componentDesc"],
                "type": r["componentType"],
                "unit": r["componentUM"],
                "quantity": float(r["quantity"]) if r["quantity"] is not None else 0.0,
                "components": []
            }

            parent_code = r["parentCode"]
            if parent_code not in items:
                items[parent_code] = {
                    "code": parent_code,
                    "description": r["parentDesc"],
                    "type": r["parentType"],
                    "unit": r["parentUM"],
                    "quantity": 1.0,
                    "components": []
                }
            items[parent_code]["components"].append(comp)
            items[comp["code"]] = comp

        root = items.get(code, {
            "code": code,
            "description": None,
            "type": None,
            "unit": None,
            "quantity": 1.0,
            "components": []
        })

        # Paginação somente no nível raiz
        root_components = [items[c["code"]] for c in root["components"]] if "components" in root else []

        return {
            "success": True,
            "total": len(root_components),
            "page": None,
            "pageSize": None,
            "totalPages": None,
            "data": root
        }


    # -------------------------------
    # 🔹 PARENTS (WHERE USED)
    # -------------------------------
    def list_parents(self, code: str, max_depth: int = 10, page: int = 1, page_size: int = 50) -> dict:
        """
        Retorna os produtos pais (WHERE USED) em formato hierárquico.
        Inclui tipo de produto (B1_TIPO) e unidade de medida (B1_UM).
        Compatível com SQL Server.
        Mantém quantidades originais (G1_QUANT).
        """

        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")
        if not 1 <= max_depth <= 50:
            raise ValueError("max_depth must be between 1 and 50")

        log_info(f"Consultando pais (WHERE USED) de {code}, depth={max_depth}, page={page}, size={page_size}")

        # =====================================================
        # 🔹 CTE recursiva sem paginação interna
        # =====================================================
        data_query = """
            WITH RECURSIVE_PARENTS AS (
                SELECT 
                    G1_COD AS parentCode,
                    G1_COMP AS childCode,
                    G1_QUANT AS quantity,
                    1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COMP = ?

                UNION ALL

                SELECT 
                    c.G1_COD AS parentCode,
                    c.G1_COMP AS childCode,
                    c.G1_QUANT AS quantity,
                    p.level + 1 AS level
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_PARENTS p ON p.parentCode = c.G1_COMP
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            )
            SELECT 
                rp.parentCode,
                pdesc.B1_DESC AS parentDesc,
                pdesc.B1_TIPO AS parentType,
                pdesc.B1_UM AS parentUM,
                rp.childCode,
                cdesc.B1_DESC AS childDesc,
                cdesc.B1_TIPO AS childType,
                cdesc.B1_UM AS childUM,
                rp.quantity,
                rp.level
            FROM RECURSIVE_PARENTS rp
            LEFT JOIN SB1010 pdesc WITH (NOLOCK)
                ON pdesc.B1_COD = rp.parentCode AND pdesc.D_E_L_E_T_ = ''
            LEFT JOIN SB1010 cdesc WITH (NOLOCK)
                ON cdesc.B1_COD = rp.childCode AND cdesc.D_E_L_E_T_ = ''
            ORDER BY rp.level, rp.parentCode, rp.childCode;
        """

        rows = self.execute_query(data_query, (code, max_depth))

        # =====================================================
        # 🔹 Monta estrutura hierárquica (filho → pais)
        # =====================================================
        items = {}
        for r in rows:
            parent = {
                "code": r["parentCode"],
                "description": r["parentDesc"],
                "type": r["parentType"],
                "unit": r["parentUM"],
                "quantity": float(r["quantity"]) if r["quantity"] is not None else 0.0,
                "parents": []
            }

            child_code = r["childCode"]
            if child_code not in items:
                items[child_code] = {
                    "code": child_code,
                    "description": r["childDesc"],
                    "type": r["childType"],
                    "unit": r["childUM"],
                    "quantity": 1.0,
                    "parents": []
                }

            # adiciona o pai dentro do campo "parents"
            items[child_code]["parents"].append(parent)
            items[parent["code"]] = parent  # adiciona o pai ao índice global

        # =====================================================
        # 🔹 Produto raiz (filho consultado)
        # =====================================================
        root = items.get(code, {
            "code": code,
            "description": None,
            "type": None,
            "unit": None,
            "quantity": 1.0,
            "parents": []
        })

        # Paginação somente no primeiro nível
        root_parents = [items[p["code"]] for p in root["parents"]] if "parents" in root else []
        offset = (page - 1) * page_size
        root["parents"] = root_parents[offset: offset + page_size]

        return {
            "success": True,
            "total": len(root_parents),
            "page": page,
            "pageSize": page_size,
            "totalPages": math.ceil(len(root_parents) / page_size),
            "data": root
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

    # -------------------------------
    # 🔹 GUIDE (SG2010)
    # -------------------------------
    def list_guide(
        self,
        code: str,
        page: int = 1,
        page_size: int = 50,
        branch: Optional[str] = None,
        max_depth: int = 10
    ) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")
        
        offset = (page - 1) * page_size

        # =====================================================
        # 🔹 COMPONENTES: produto + componentes (SG1010)
        # =====================================================
        log_info(
            f"Listando roteiro de {code} e componentes (depth={max_depth}), "
            f"página {page}, tamanho {page_size}"
        )

        # Filtros que se aplicam à tabela SG2010
        sg2_filters = ["SG2.D_E_L_E_T_ = ''"]
        sg2_params: list = []

        if branch:
            sg2_filters.append("SG2.G2_FILIAL = ?")
            sg2_params.append(branch)

        where_clause = " AND ".join(sg2_filters)

        # ------------------------
        # Count
        # ------------------------
        count_query = f"""
            WITH RECURSIVE_BOM AS (
                SELECT 
                    G1_COD AS parentCode,
                    G1_COMP AS componentCode,
                    G1_QUANT AS quantity,
                    1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT 
                    c.G1_COD,
                    c.G1_COMP,
                    c.G1_QUANT,
                    p.level + 1
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p 
                    ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            ),
            CODES AS (
                -- Produto raiz
                SELECT ? AS productCode, 0 AS level
                UNION
                -- Componentes do BOM
                SELECT DISTINCT componentCode AS productCode, level
                FROM RECURSIVE_BOM
            )
            SELECT COUNT(*) AS total
            FROM SG2010 AS SG2
            INNER JOIN CODES
                ON CODES.productCode = SG2.G2_PRODUTO
            WHERE {where_clause}
        """
        count_params = [code, max_depth, code] + sg2_params
        total_row = self.execute_one(count_query, tuple(count_params))
        total_rows = int(total_row["total"] or 0)

        # ------------------------
        # Dados paginados
        # ------------------------
        data_query = f"""
            WITH RECURSIVE_BOM AS (
                SELECT 
                    G1_COD AS parentCode,
                    G1_COMP AS componentCode,
                    G1_QUANT AS quantity,
                    1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT 
                    c.G1_COD,
                    c.G1_COMP,
                    c.G1_QUANT,
                    p.level + 1
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p 
                    ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            ),
            CODES AS (
                SELECT 
                    ? AS productCode,
                    NULL AS parentCode,
                    0 AS level

                UNION ALL

                SELECT 
                    DISTINCT componentCode AS productCode,
                    parentCode,
                    level
                FROM RECURSIVE_BOM
            )

            SELECT 
                SG2.*,
                CODES.parentCode,
                CODES.level AS bomLevel
            FROM SG2010 AS SG2
            INNER JOIN CODES
                ON CODES.productCode = SG2.G2_PRODUTO
            WHERE {where_clause}
            ORDER BY 
                CODES.level,        -- nível no BOM (0 = produto pai)
                SG2.G2_PRODUTO,
                SG2.G2_OPERAC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        data_params = [code, max_depth, code] + sg2_params + [offset, page_size]
        rows = self.execute_query(data_query, tuple(data_params))

        return {
            "success": True,
            "total": total_rows,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total_rows + page_size - 1) // page_size,
            "filters": {
                "branch": branch,
                "max_depth": max_depth
            },
            "data": rows
        }

    # -------------------------------
    # 🔹 INSPECTION (QP6/QP7/QP8) 
    # -------------------------------
    def list_inspection(
        self,
        code: str,
        page: int = 1,
        page_size: int = 50,
        max_depth: int = 10
    ) -> dict:

        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 e 500")

        offset = (page - 1) * page_size

        # ============================================================
        # 1) Obter árvore completa via SG1 (produto + componentes)
        # ============================================================
        cte = """
            WITH RECURSIVE_BOM AS (
                SELECT 
                    G1_COD AS parentCode,
                    G1_COMP AS componentCode,
                    1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT 
                    C.G1_COD,
                    C.G1_COMP,
                    P.level + 1
                FROM SG1010 C WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM P 
                    ON P.componentCode = C.G1_COD
                WHERE C.D_E_L_E_T_ = '' AND P.level < ?
            ),

            CODES AS (
                SELECT 
                    ? AS productCode,
                    NULL AS parentCode,
                    0 AS level

                UNION ALL

                SELECT DISTINCT 
                    componentCode AS productCode,
                    parentCode,
                    level
                FROM RECURSIVE_BOM
            )
        """

        # ============================================================
        # 2) Trazer apenas os produtos que realmente têm QP6
        # ============================================================
        qp6_sql = f"""
            {cte}
            SELECT 
                QP6.QP6_PRODUT,
                QP6.QP6_REVI,
                QP6.QP6_REVINV,
                QP6.QP6_DESCPO,
                QP6.QP6_DTCAD,
                QP6.QP6_DTINI,
                QP6.QP6_CADR,
                QP6.QP6_PTOLER,
                QP6.QP6_TIPO,
                QP6.QP6_DOCOBR,
                QP6.QP6_SITPRD,
                QP6.QP6_DESSTP,
                QP6.QP6_DESSTP,
                QP6.QP6_UNMED1,
                CODES.level,
                CODES.parentCode
            FROM QP6010 QP6 WITH (NOLOCK)
            INNER JOIN CODES 
                ON CODES.productCode = QP6.QP6_PRODUT
            WHERE QP6.D_E_L_E_T_ = ''
            ORDER BY CODES.level, QP6.QP6_PRODUT
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
        """

        qp6_rows = self.execute_query(
            qp6_sql,
            (code, max_depth, code, offset, page_size)
        )

        # Se nada encontrado, retorno vazio
        if not qp6_rows:
            return {
                "success": True,
                "total": 0,
                "page": page,
                "pageSize": page_size,
                "totalPages": 0,
                "data": []
            }

        # Lista de produtos encontrados na QP6
        products = [row["QP6_PRODUT"] for row in qp6_rows]

        # ============================================================
        # 3) Contagem total (QP6 + BOM)
        # ============================================================
        count_sql = f"""
            {cte}
            SELECT COUNT(*) AS total
            FROM QP6010 QP6 WITH (NOLOCK)
            INNER JOIN CODES 
                ON CODES.productCode = QP6.QP6_PRODUT
            WHERE QP6.D_E_L_E_T_ = ''
        """

        total = self.execute_one(count_sql, (code, max_depth, code))["total"]

        # ============================================================
        # 4) Buscar ensaios QP7 (somente desses produtos)
        # ============================================================
        qp7_sql = f"""
            SELECT 
                QP7_PRODUT,
                QP7_REVI,
                QP7_ENSAIO,
                QP7_LABOR,
                QP7_SEQLAB,
                QP7_UNIMED,
                QP7_MINMAX,
                QP7_NOMINA,
                QP7_LIE,
                QP7_LSE,
                QP7_LIC,
                QP7_LSC,
                QP7_CODREC,
                QP7_OPERAC,
                QP7_ENSOBR,
                QP7_CERTIF
            FROM QP7010 WITH (NOLOCK)
            WHERE D_E_L_E_T_ = ''
            AND QP7_PRODUT IN ({','.join(['?'] * len(products))})
        """

        qp7_rows = self.execute_query(qp7_sql, tuple(products))

        # Agrupar por produto
        qp7_map = {}
        for row in qp7_rows:
            qp7_map.setdefault(row["QP7_PRODUT"], []).append(row)

        # ============================================================
        # 5) Buscar ensaios QP8 (somente desses produtos)
        # ============================================================
        qp8_sql = f"""
            SELECT 
                QP8_PRODUT,
                QP8_REVI,
                QP8_ENSAIO,
                QP8_LABOR,
                QP8_SEQLAB,
                QP8_TEXTO,
                QP8_CODREC,
                QP8_OPERAC,
                QP8_ENSOBR,
                QP8_CERTIF
            FROM QP8010 WITH (NOLOCK)
            WHERE D_E_L_E_T_ = ''
            AND QP8_PRODUT IN ({','.join(['?'] * len(products))})
        """

        qp8_rows = self.execute_query(qp8_sql, tuple(products))

        # Agrupar por produto
        qp8_map = {}
        for row in qp8_rows:
            qp8_map.setdefault(row["QP8_PRODUT"], []).append(row)

        # ============================================================
        # 6) Montar resposta final
        # ============================================================
        final = []
        for row in qp6_rows:
            prod = row["QP6_PRODUT"]

            final.append({
                "product": prod,
                "level": row["level"],
                "parentCode": row["parentCode"],

                # Cabeçalho único
                "QP6": row,

                # Ensaios separados
                "QP7": qp7_map.get(prod, []),
                "QP8": qp8_map.get(prod, []),
            })

        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "data": final
        }

    # -------------------------------
    # 🔹 CUSTOMERS (SA7010/SA1010) 
    # -------------------------------
    def list_customers(self, code: str, page: int = 1, page_size: int = 50) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        log_info(f"Listando clientes amarrados ao produto {code}, página {page}, tamanho {page_size}")
        offset = (page - 1) * page_size

        # Contagem total
        count_query = """
            SELECT COUNT(*) AS total
            FROM SA7010 AS SA7
            INNER JOIN SA1010 AS SA1
                ON SA1.A1_COD = SA7.A7_CLIENTE
            AND SA1.A1_LOJA = SA7.A7_LOJA
            AND SA1.D_E_L_E_T_ = ''
            WHERE SA7.D_E_L_E_T_ = ''
            AND SA7.A7_PRODUTO = ?
        """
        total_row = self.execute_one(count_query, (code,))
        total_rows = int(total_row["total"] or 0)

        # Consulta paginada
        query = """
            SELECT 
                SA1.A1_COD,
                SA1.A1_NOME,
                SA1.A1_NREDUZ,
                SA1.A1_MSBLQL,
                SA1.A1_LOJA,
                SA7.A7_PRODUTO,
                SA7.A7_CODCLI,
                SA7.A7_DESCCLI,
                SA7.A7_PRECO01,
                SA7.A7_DTREF01,
                SA7.A7_PRECO02,
                SA7.A7_DTREF02,
                SA7.A7_PRECO03,
                SA7.A7_DTREF03,
                SA7.A7_PRECO04,
                SA7.A7_DTREF04,
                SA7.A7_PRECO05,
                SA7.A7_DTREF05,
                SA7.A7_PRECO06,
                SA7.A7_DTREF06,
                SA7.A7_PRECO07,
                SA7.A7_DTREF07,
                SA7.A7_PRECO08,
                SA7.A7_DTREF08,
                SA7.A7_PRECO09,
                SA7.A7_DTREF09
            FROM SA7010 AS SA7
            INNER JOIN SA1010 AS SA1
                ON SA1.A1_COD = SA7.A7_CLIENTE
            AND SA1.A1_LOJA = SA7.A7_LOJA
            AND SA1.D_E_L_E_T_ = ''
            WHERE SA7.D_E_L_E_T_ = ''
            AND SA7.A7_PRODUTO = ?
            ORDER BY SA7.A7_CLIENTE, SA7.A7_LOJA
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
