# app/repositories/product_repository.py
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import BusinessLogicError
from app.utils.logger import log_info, log_error
from typing import Optional, Union
from datetime import datetime
import math
import json

class ProductRepository(BaseRepository):
    """
    Repositório responsável por consultas na tabela SG1010 (estrutura) e SB1010 (produtos).
    """
    
    def _convert_date_to_protheus(self, date_value: Optional[Union[str, datetime]]) -> Optional[str]:
        """
        Converte vários formatos de data para 'YYYYMMDD' (padrão Protheus).

        Formatos aceitos:
        - datetime
        - 'YYYY-MM-DD'
        - 'YYYY/MM/DD'
        - 'DD/MM/YYYY'
        - 'DD-MM-YYYY'
        - 'YYYYMMDD'
        - ISO completo: 'YYYY-MM-DDTHH:MM:SS'
        - ISO com timezone: 'YYYY-MM-DDTHH:MM:SSZ'
        """

        if not date_value:
            return None

        # Caso já seja datetime
        if isinstance(date_value, datetime):
            return date_value.strftime("%Y%m%d")

        if not isinstance(date_value, str):
            return None

        date_value = date_value.strip()

        # Se já estiver no padrão Protheus
        if date_value.isdigit() and len(date_value) == 8:
            return date_value

        # Lista de formatos conhecidos
        known_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y%m%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in known_formats:
            try:
                parsed = datetime.strptime(date_value, fmt)
                return parsed.strftime("%Y%m%d")
            except ValueError:
                continue

        # Tentativa final: ISO 8601 genérico (Python 3.11+ / compatível)
        try:
            parsed = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            return parsed.strftime("%Y%m%d")
        except Exception:
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

    # -------------------------------
    # 🔹 PRODUCT (SB1010)  
    # -------------------------------
    def get_product_by_code(self, code: str) -> dict:
        log_info(f"Consultando produto {code} no Protheus (SB1010)...")

        sql = """
            SELECT
                -- =====================
                -- IDENTIFICAÇÃO
                -- =====================
                B1_GRUPO     AS group_code,
                B1_COD       AS code,
                B1_DESC      AS description,
                B1_TIPO      AS type,
                B1_SUBGRUP   AS subgroup,
                B1_CODANT    AS previous_code,
                B1_ATIVO     AS active,
                B1_MSBLQL   AS blocked,

                -- =====================
                -- COMERCIAL
                -- =====================
                B1_REFEREN   AS customer_reference,
                B1_REFCANT   AS customer_reference_old,
                B1_PRV1      AS sale_price,
                B1_CONTRAT   AS contractual_product,
                B1_CLASSVE   AS sales_class,

                -- =====================
                -- ENGENHARIA / PRODUÇÃO
                -- =====================
                B1_CODDES    AS drawing_code,
                B1_UM        AS unit,
                B1_SEGUM     AS secondary_unit,
                B1_CONV      AS conversion_factor,
                B1_TIPCONV   AS conversion_type,
                B1_TPMAT     AS material_type,
                B1_LINHA     AS production_line,
                B1_TIPODEC   AS operation_decimal_type,
                B1_REVATU    AS current_revision,
                B1_UREV      AS last_revision_date,
                B1_PESO      AS net_weight,

                -- =====================
                -- ESTOQUE / LOGÍSTICA
                -- =====================
                B1_LOCPAD    AS default_warehouse,
                B1_QE        AS package_quantity,
                B1_CODBAR    AS barcode,
                B1_EMBDELP   AS customer_packaging,
                B1_PRODSBP   AS make_or_buy,

                -- =====================
                -- COMPRAS
                -- =====================
                B1_UCOM      AS last_purchase_date,
                B1_UPRC      AS last_purchase_price,
                B1_TIPE      AS lead_time_type,
                B1_SOLICIT   AS requester_restriction,

                -- =====================
                -- CUSTOS
                -- =====================
                B1_CUSTD     AS standard_cost,
                B1_UCALSTD   AS standard_cost_date,
                B1_MCUSTD   AS cost_currency,
                B1_DATREF   AS cost_reference_date,
                B1_DESPIMP  AS import_expense,

                -- =====================
                -- FISCAL / TRIBUTÁRIO
                -- =====================
                B1_POSIPI   AS ncm_ipi_position,
                B1_ORIGEM   AS origin,
                B1_IMPORT   AS imported_product,
                B1_GRTRIB   AS tax_group,
                B1_TE       AS entry_tes,
                B1_TS       AS exit_tes,
                B1_PICM     AS icms_rate,
                B1_IPI      AS ipi_rate,
                B1_PIS      AS pis_incidence,
                B1_PPIS     AS pis_percent,
                B1_COFINS   AS cofins_incidence,
                B1_PCOFINS  AS cofins_percent,
                B1_CSLL     AS csll_incidence,
                B1_INSS     AS inss_incidence,
                B1_RETOPER  AS retention_by_operation,
                B1_ANUENTE  AS customs_authority,
                B1_MIDIA    AS media_product,
                B1_QTMIDIA  AS media_quantity,
                B1_GRPTI    AS intelligent_tes_group,

                -- =====================
                -- QUALIDADE / PCP
                -- =====================
                B1_YHOHS    AS rohs_indicator,
                B1_RASTRO   AS traceability,
                B1_GARANT   AS warranty_product,
                B1_MRP      AS mrp_considered,
                B1_FLAGSUG  AS suggestion_flag,
                B1_CPOTENC  AS power_control,

                -- =====================
                -- CONTÁBIL
                -- =====================
                B1_CONTA    AS accounting_account,
                B1_CC       AS cost_center,
                B1_APROPRI  AS appropriation_type,

                -- =====================
                -- SISTEMA / CONTROLES DELPI
                -- =====================
                B1_CONINI   AS initial_consumption_date,
                B1_USERLGI  AS created_by,
                B1_USERLGA  AS updated_by,
                B1_YSC      AS mandatory_cc_sc,
                B1_YPC      AS mandatory_cc_pc,
                B1_YPV      AS mandatory_cc_pv,
                B1_YMI      AS mandatory_cc_mi,
                B1_YNFE     AS mandatory_cc_nfe,
                B1_YVLPC    AS approval_validation,
                B1_YCAT     AS delpi_category,
                B1_ZDLPSEG  AS delpi_segment

            FROM SB1010
            WHERE D_E_L_E_T_ = ''
            AND B1_COD = ?
        """

        product = self.execute_one(sql, (code,))

        if not product:
            raise BusinessLogicError(
                f"Produto com código '{code}' não encontrado."
            )

        return {
            "success": True,
            "data": product
        }
    

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
        desc_clean = description.strip()
        terms = [t for t in desc_clean.split() if t]

        # -----------------------------
        # WHERE simples (OR)
        # -----------------------------
        where_clauses = ["SB1.D_E_L_E_T_ = ''"]
        where_terms = []
        params = []

        for t in terms:
            where_terms.append(
                "SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ?"
            )
            params.append(f"%{t}%")

        where_clauses.append("(" + " OR ".join(where_terms) + ")")
        where_sql = " AND ".join(where_clauses)

        # -----------------------------
        # SCORE claro e barato
        # -----------------------------
        score_parts = [
            "CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 50 ELSE 0 END"
        ]
        score_params = [f"%{desc_clean}%"]

        for t in terms:
            score_parts.append(
                "CASE WHEN SB1.B1_DESC COLLATE Latin1_General_CI_AI LIKE ? THEN 10 ELSE 0 END"
            )
            score_params.append(f"%{t}%")

        score_sql = " + ".join(score_parts)

        # -----------------------------
        # COUNT
        # -----------------------------
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM SB1010 SB1
            WHERE {where_sql}
        """
        total = int(self.execute_one(count_sql, tuple(params))["total"] or 0)

        # -----------------------------
        # DATA
        # -----------------------------
        sql = f"""
            SELECT
                SB1.B1_GRUPO     AS group_code,
                SB1.B1_COD       AS code,
                SB1.B1_DESC      AS description,
                SB1.B1_UM        AS unit,
                SB1.B1_TIPO      AS type,
                SB1.B1_SUBGRUP   AS subgroup,
                SB1.B1_CODANT    AS previous_code,
                SB1.B1_ATIVO     AS active,
                SB1.B1_MSBLQL    AS blocked,
                ({score_sql})    AS relevance_score
            FROM SB1010 SB1
            WHERE {where_sql}
            ORDER BY relevance_score DESC, SB1.B1_DESC, SB1.B1_COD
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        rows = self.execute_query(
            sql,
            tuple(score_params + params + [offset, page_size])
        )

        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "description": description,
            "results": rows
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
                -- Filtra apenas itens válidos pela data final
                AND G1_FIM > CONVERT(CHAR(8), GETDATE(), 112)

                UNION ALL

                SELECT 
                    c.G1_COD AS parentCode,
                    c.G1_COMP AS componentCode,
                    c.G1_QUANT AS quantity,
                    p.level + 1 AS level
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
                -- Filtra novamente na recursão
                AND c.G1_FIM > CONVERT(CHAR(8), GETDATE(), 112)
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
                -- Filtra apenas itens válidos pela data final
                AND G1_FIM > CONVERT(CHAR(8), GETDATE(), 112)

                UNION ALL

                SELECT 
                    c.G1_COD AS parentCode,
                    c.G1_COMP AS componentCode,
                    c.G1_QUANT AS quantity,
                    p.level + 1 AS level
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < 50
                -- Filtra novamente na recursão
                AND c.G1_FIM > CONVERT(CHAR(8), GETDATE(), 112)
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
    def list_suppliers(
        self,
        code: str,
        page: int = 1,
        page_size: int = 50
    ) -> dict:

        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        offset = (page - 1) * page_size

        count_sql = """
            SELECT COUNT(*) AS total
            FROM SA5010
            WHERE D_E_L_E_T_ = ''
            AND A5_PRODUTO = ?
        """

        total = int(self.execute_one(count_sql, (code,))["total"] or 0)

        sql = """ 
            WITH LAST_PURCHASE AS (
                SELECT
                    C7.C7_PRODUTO,
                    C7.C7_FORNECE,
                    C7.C7_LOJA,
                    C7.C7_PRECO,
                    C7.C7_EMISSAO,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            C7.C7_PRODUTO,
                            C7.C7_FORNECE,
                            C7.C7_LOJA
                        ORDER BY
                            C7.C7_EMISSAO DESC
                    ) AS rn
                FROM SC7010 C7
                WHERE
                    C7.D_E_L_E_T_ = ''
                    AND C7.C7_PRODUTO = ?
            ),

            REAL_LEAD_TIME AS (
                SELECT
                    C7.C7_PRODUTO,
                    C7.C7_FORNECE,
                    C7.C7_LOJA,
                    COUNT(*) AS amostra,
                    AVG(DATEDIFF(DAY, C7.C7_EMISSAO, SD1.D1_EMISSAO)) AS lead_time_medio,
                    MIN(DATEDIFF(DAY, C7.C7_EMISSAO, SD1.D1_EMISSAO)) AS lead_time_min,
                    MAX(DATEDIFF(DAY, C7.C7_EMISSAO, SD1.D1_EMISSAO)) AS lead_time_max
                FROM SC7010 C7
                INNER JOIN SD1010 SD1
                    ON SD1.D1_PEDIDO  = C7.C7_NUM
                AND SD1.D1_FORNECE = C7.C7_FORNECE
                AND SD1.D1_LOJA    = C7.C7_LOJA
                AND SD1.D1_COD     = C7.C7_PRODUTO
                AND SD1.D_E_L_E_T_ = ''
                WHERE
                    C7.D_E_L_E_T_ = ''
                    AND C7.C7_PRODUTO = ?
                GROUP BY
                    C7.C7_PRODUTO,
                    C7.C7_FORNECE,
                    C7.C7_LOJA
            )

            SELECT
                -- PRODUTO
                SB1.B1_COD            AS produto,
                SB1.B1_DESC           AS descricao_produto,
                SB1.B1_UM             AS unidade,

                -- FORNECEDOR
                SA5.A5_FORNECE        AS fornecedor,
                SA5.A5_LOJA           AS loja,
                SA2.A2_NOME           AS fornecedor_nome,

                -- CÓDIGOS DO PRODUTO NO FORNECEDOR
                SA5.A5_CODPRF         AS part_number,
                SA5.A5_CODPRCA        AS codigo_catalogo,
                SA5.A5_CODBAR         AS codigo_barras,

                -- LEAD TIMES
                SA5.A5_LEAD_T         AS lead_time_cadastrado,
                RLT.lead_time_medio   AS lead_time_real_medio,
                RLT.lead_time_min     AS lead_time_real_min,
                RLT.lead_time_max     AS lead_time_real_max,
                RLT.amostra           AS amostra_lead_time_real,

                -- PREÇO
                LP.C7_PRECO           AS ultimo_preco,
                LP.C7_EMISSAO         AS data_ultimo_preco

            FROM SA5010 SA5
            INNER JOIN SB1010 SB1
                ON SB1.B1_COD = SA5.A5_PRODUTO
            AND SB1.D_E_L_E_T_ = ''

            LEFT JOIN SA2010 SA2
                ON SA2.A2_COD = SA5.A5_FORNECE
            AND SA2.A2_LOJA = SA5.A5_LOJA
            AND SA2.D_E_L_E_T_ = ''

            LEFT JOIN LAST_PURCHASE LP
                ON LP.C7_PRODUTO = SA5.A5_PRODUTO
            AND LP.C7_FORNECE = SA5.A5_FORNECE
            AND LP.C7_LOJA = SA5.A5_LOJA
            AND LP.rn = 1

            LEFT JOIN REAL_LEAD_TIME RLT
                ON RLT.C7_PRODUTO = SA5.A5_PRODUTO
            AND RLT.C7_FORNECE = SA5.A5_FORNECE
            AND RLT.C7_LOJA = SA5.A5_LOJA

            WHERE
                SA5.D_E_L_E_T_ = ''
                AND SA5.A5_PRODUTO = ?

            ORDER BY
                SA5.A5_FORNECE
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        rows = self.execute_query(
            sql,
            (code, code, code, offset, page_size)
        )

        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "data": rows
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

        filters = []
        params = [code]

        if issue_date_start:
            issue_date_start = self._convert_date_to_protheus(issue_date_start)
            filters.append("SD1.D1_EMISSAO >= ?")
            params.append(issue_date_start)

        if issue_date_end:
            issue_date_end = self._convert_date_to_protheus(issue_date_end)
            filters.append("SD1.D1_EMISSAO <= ?")
            params.append(issue_date_end)

        if supplier:
            filters.append("SD1.D1_FORNECE = ?")
            params.append(supplier)

        if branch:
            filters.append("SD1.D1_FILIAL = ?")
            params.append(branch)

        where_extra = ""
        if filters:
            where_extra = " AND " + " AND ".join(filters)

        # COUNT
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM SD1010 SD1
            WHERE SD1.D_E_L_E_T_ = ''
            AND SD1.D1_COD = ? {where_extra}
        """

        total = int(self.execute_one(count_sql, tuple(params))["total"] or 0)

        # DATA
        data_sql = f"""
            SELECT
                SD1.D1_FILIAL        AS filial,
                SD1.D1_DOC           AS nota,
                SD1.D1_SERIE         AS serie,
                SD1.D1_ITEM          AS item,
                SD1.D1_EMISSAO       AS data_emissao,

                SD1.D1_COD           AS produto,
                SB1.B1_DESC          AS descricao_produto,
                SB1.B1_UM            AS unidade,

                SD1.D1_FORNECE       AS fornecedor,
                SA2.A2_NOME          AS fornecedor_nome,

                SD1.D1_QUANT         AS quantidade,
                CASE 
                    WHEN SD1.D1_QUANT <> 0 
                    THEN SD1.D1_TOTAL / SD1.D1_QUANT 
                    ELSE 0 
                END                  AS preco_unitario,
                SD1.D1_TOTAL         AS valor_total

            FROM SD1010 SD1
            INNER JOIN SB1010 SB1
                ON SB1.B1_COD = SD1.D1_COD
            AND SB1.D_E_L_E_T_ = ''
            LEFT JOIN SA2010 SA2
                ON SA2.A2_COD = SD1.D1_FORNECE
            AND SA2.A2_LOJA = SD1.D1_LOJA
            AND SA2.D_E_L_E_T_ = ''
            WHERE SD1.D_E_L_E_T_ = ''
            AND SD1.D1_COD = ? {where_extra}
            ORDER BY SD1.D1_EMISSAO DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        rows = self.execute_query(
            data_sql,
            tuple(params + [offset, page_size])
        )

        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "filters": {
                "issue_date_start": issue_date_start,
                "issue_date_end": issue_date_end,
                "supplier": supplier,
                "branch": branch
            },
            "data": rows
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
        log_info(f"Listando NF-es de saída do produto {code}")

        filters = []
        params = [code]

        if issue_date_start:
            issue_date_start = self._convert_date_to_protheus(issue_date_start)
            filters.append("SD2.D2_EMISSAO >= ?")
            params.append(issue_date_start)

        if issue_date_end:
            issue_date_end = self._convert_date_to_protheus(issue_date_end)
            filters.append("SD2.D2_EMISSAO <= ?")
            params.append(issue_date_end)

        if customer:
            filters.append("SD2.D2_CLIENTE = ?")
            params.append(customer)

        if branch:
            filters.append("SD2.D2_FILIAL = ?")
            params.append(branch)

        where_extra = ""
        if filters:
            where_extra = " AND " + " AND ".join(filters)

        # -----------------------------
        # COUNT
        # -----------------------------
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM SD2010 SD2
            WHERE SD2.D_E_L_E_T_ = ''
            AND SD2.D2_COD = ? {where_extra}
        """

        total = int(self.execute_one(count_sql, tuple(params))["total"] or 0)

        # -----------------------------
        # DATA
        # -----------------------------
        data_sql = f"""
            SELECT
                SD2.D2_FILIAL        AS filial,
                SD2.D2_DOC           AS nota,
                SD2.D2_SERIE         AS serie,
                SD2.D2_ITEM          AS item,
                SD2.D2_EMISSAO       AS data_emissao,

                SD2.D2_COD           AS produto,
                SB1.B1_DESC          AS descricao_produto,
                SB1.B1_UM            AS unidade,

                SD2.D2_CLIENTE       AS cliente,
                SA1.A1_NOME          AS cliente_nome,

                SD2.D2_QUANT         AS quantidade,
                SD2.D2_PRCVEN        AS preco_unitario,
                (SD2.D2_QUANT * SD2.D2_PRCVEN) AS valor_total

            FROM SD2010 SD2
            INNER JOIN SB1010 SB1
                ON SB1.B1_COD = SD2.D2_COD
            AND SB1.D_E_L_E_T_ = ''
            LEFT JOIN SA1010 SA1
                ON SA1.A1_COD = SD2.D2_CLIENTE
            AND SA1.A1_LOJA = SD2.D2_LOJA
            AND SA1.D_E_L_E_T_ = ''
            WHERE SD2.D_E_L_E_T_ = ''
            AND SD2.D2_COD = ? {where_extra}
            ORDER BY SD2.D2_EMISSAO DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        rows = self.execute_query(
            data_sql,
            tuple(params + [offset, page_size])
        )

        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "filters": {
                "issue_date_start": issue_date_start,
                "issue_date_end": issue_date_end,
                "customer": customer,
                "branch": branch
            },
            "data": rows
        }


    # -------------------------------
    # 🔹 STOCK + LOCALIZAÇÃO FÍSICA (SB2010 + SBZ010)
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

        filters = [
            "SB2.D_E_L_E_T_ = ''",
            "SB2.B2_COD = ?"
        ]
        params = [code]

        if branch:
            filters.append("SB2.B2_FILIAL = ?")
            params.append(branch)

        if location:
            filters.append("SB2.B2_LOCAL = ?")
            params.append(location)

        where_clause = " AND ".join(filters)

        # -------------------------------
        # 🔹 TOTAL (SB2010)
        # -------------------------------
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM SB2010 SB2
            WHERE {where_clause}
        """

        total = int(
            self.execute_one(count_sql, tuple(params))["total"] or 0
        )

        # -------------------------------
        # 🔹 DADOS DE ESTOQUE + SBZ
        # -------------------------------
        data_sql = f"""
            SELECT
                SB2.B2_COD        AS produto,
                SB2.B2_FILIAL     AS filial,
                SB2.B2_LOCAL      AS armazem,
                SB2.B2_QATU       AS saldo,
                SB2.B2_QEMP       AS empenhado,
                SB2.B2_RESERVA    AS reservado,
                (SB2.B2_QATU - SB2.B2_QEMP - SB2.B2_RESERVA) AS disponivel,

                -- LOCALIZAÇÃO FÍSICA REAL (SBZ)
                SBZ.BZ_MPLOCAL    AS localizacao_fisica,
                SBZ.BZ_LOCPAD     AS armazem_padrao,
                SBZ.BZ_CUSTO      AS centro_custo,
                SBZ.BZ_GALPAO     AS galpao

            FROM SB2010 SB2
            LEFT JOIN SBZ010 SBZ
                ON  SBZ.BZ_COD    = SB2.B2_COD
                AND SBZ.BZ_FILIAL = SB2.B2_FILIAL

            WHERE {where_clause}
            ORDER BY SB2.B2_FILIAL, SB2.B2_LOCAL
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        rows = self.execute_query(
            data_sql,
            tuple(params + [offset, page_size])
        )

        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
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

        log_info(
            f"Listando roteiro e componentes vinculados de {code} (depth={max_depth}), "
            f"página {page}, tamanho {page_size}"
        )

        sg2_filters = ["SG2.D_E_L_E_T_ = ''"]
        sg2_params: list = []

        if branch:
            sg2_filters.append("SG2.G2_FILIAL = ?")
            sg2_params.append(branch)

        where_clause = " AND ".join(sg2_filters)

        # ==============================================================
        # 🔹 COUNT TOTAL DE REGISTROS (SG2010 + SGF010 + SB1010 + SG1010)
        # ==============================================================
        count_query = f"""
            WITH RECURSIVE_BOM AS (
                SELECT G1_COD AS parentCode, G1_COMP AS componentCode, 1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT c.G1_COD, c.G1_COMP, p.level + 1
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            ),
            CODES AS (
                SELECT ? AS productCode, 0 AS level
                UNION
                SELECT DISTINCT componentCode AS productCode, level FROM RECURSIVE_BOM
            )
            SELECT COUNT(*) AS total
            FROM SG2010 AS SG2
            INNER JOIN CODES ON CODES.productCode = SG2.G2_PRODUTO
            LEFT JOIN SGF010 AS SGF
                ON SGF.GF_FILIAL = SG2.G2_FILIAL
            AND SGF.GF_PRODUTO = SG2.G2_PRODUTO
            AND SGF.GF_ROTEIRO = SG2.G2_CODIGO
            AND SGF.GF_OPERAC = SG2.G2_OPERAC
            AND SGF.D_E_L_E_T_ = ''
            LEFT JOIN SB1010 AS SB1
            ON SB1.B1_COD = SGF.GF_COMP
            AND SB1.D_E_L_E_T_ = ''
            WHERE {where_clause}
        """

        count_params = [code, max_depth, code] + sg2_params
        total_row = self.execute_one(count_query, tuple(count_params))
        total_rows = int(total_row["total"] or 0)

        # ==============================================================
        # 🔹 CONSULTA PRINCIPAL: OPERAÇÕES + COMPONENTES + DESCRIÇÃO (SG2010 + SGF010 + SB1010)
        # ==============================================================
        data_query = f"""
            WITH RECURSIVE_BOM AS (
                SELECT G1_COD AS parentCode, G1_COMP AS componentCode, 1 AS level
                FROM SG1010 WITH (NOLOCK)
                WHERE D_E_L_E_T_ = '' AND G1_COD = ?

                UNION ALL

                SELECT c.G1_COD, c.G1_COMP, p.level + 1
                FROM SG1010 c WITH (NOLOCK)
                INNER JOIN RECURSIVE_BOM p ON p.componentCode = c.G1_COD
                WHERE c.D_E_L_E_T_ = '' AND p.level < ?
            ),
            CODES AS (
                SELECT ? AS productCode, NULL AS parentCode, 0 AS level
                UNION ALL
                SELECT DISTINCT componentCode AS productCode, parentCode, level FROM RECURSIVE_BOM
            )
            SELECT 
                SG2.*,
                SG2.G2_DESCRI AS operationDescription,
                SG2.G2_TEMPAD AS standardTimeInHours_Thousands,
                SG2.G2_SETUP AS setupInHours,
                SGF.GF_COMP AS componentCode,
                SB1.B1_DESC AS componentDescription,
                SGF.GF_TRT AS componentSeq,
                CODES.level AS bomLevel
            FROM SG2010 AS SG2
            INNER JOIN CODES ON CODES.productCode = SG2.G2_PRODUTO
            LEFT JOIN SGF010 AS SGF
                ON SGF.GF_FILIAL = SG2.G2_FILIAL
            AND SGF.GF_PRODUTO = SG2.G2_PRODUTO
            AND SGF.GF_ROTEIRO = SG2.G2_CODIGO
            AND SGF.GF_OPERAC = SG2.G2_OPERAC
            AND SGF.D_E_L_E_T_ = ''
            LEFT JOIN SB1010 AS SB1
            ON SB1.B1_COD = SGF.GF_COMP
            AND SB1.D_E_L_E_T_ = ''
            WHERE {where_clause}
            ORDER BY CODES.level, SG2.G2_PRODUTO, SG2.G2_OPERAC, SGF.GF_TRT
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
            "filters": {"branch": branch, "max_depth": max_depth},
            "data": rows
        }


    # -------------------------------
    # 🔹 INSPECTION DEFINITION (QP6 / QP7 / QP8)
    # -------------------------------
    def list_inspection_definition(
        self,
        code: str,
        max_depth: int = 10
    ) -> dict:
        """
        Retorna a DEFINIÇÃO de inspeção (QP6, QP7, QP8) de um produto
        e de seus componentes conforme a SG1010.

        ⚠️ NÃO retorna:
            - histórico
            - resultados
            - não conformidades
        """

        # -------------------------------
        # Validações
        # -------------------------------
        if not code:
            raise ValueError("code must be provided")

        if max_depth < 1 or max_depth > 20:
            raise ValueError("max_depth must be between 1 and 20")

        # ============================================================
        # SQL — definição de inspeção com revisão controlada
        # ============================================================
        sql = """
        DECLARE
            @product_code NVARCHAR(20) = ?,
            @max_depth INT = ?;

        -- ============================================================
        -- Estrutura de produto (SG1010)
        -- ============================================================
        WITH BOM_RECURSIVE AS (
            SELECT
                G1.G1_COD  AS root_code,
                G1.G1_COMP AS product_code,
                1          AS level
            FROM SG1010 G1 WITH (NOLOCK)
            WHERE G1.D_E_L_E_T_ = ''
            AND G1.G1_COD = @product_code

            UNION ALL

            SELECT
                B.root_code,
                G1.G1_COMP,
                B.level + 1
            FROM SG1010 G1 WITH (NOLOCK)
            INNER JOIN BOM_RECURSIVE B
                ON B.product_code = G1.G1_COD
            WHERE G1.D_E_L_E_T_ = ''
            AND B.level < @max_depth
        ),

        PRODUCT_SCOPE AS (
            SELECT @product_code AS product_code, 0 AS level
            UNION
            SELECT product_code, level FROM BOM_RECURSIVE
        ),

        -- ============================================================
        -- Revisão ATIVA por produto (QP6)
        -- ============================================================
        ACTIVE_QP6 AS (
            SELECT
                QP6_PRODUT AS product_code,
                MAX(QP6_REVI) AS revision
            FROM QP6010
            WHERE D_E_L_E_T_ = ''
            GROUP BY QP6_PRODUT
        ),

        -- ============================================================
        -- Apenas produtos com definição de inspeção válida
        -- ============================================================
        INSPECTION_SCOPE AS (
            SELECT
                P.product_code AS productCode,
                P.level,
                R.revision
            FROM PRODUCT_SCOPE P
            INNER JOIN ACTIVE_QP6 R
                ON R.product_code = P.product_code
        )

        -- ============================================================
        -- JSON final
        -- ============================================================
        SELECT
        (
            SELECT
                COUNT(*) AS total,
                (
                    SELECT
                        I.productCode,
                        I.level,

                        CASE
                            WHEN EXISTS (
                                SELECT 1 FROM QP7010
                                WHERE D_E_L_E_T_ = ''
                                AND QP7_PRODUT = I.productCode
                                AND QP7_REVI = I.revision
                            )
                            OR EXISTS (
                                SELECT 1 FROM QP8010
                                WHERE D_E_L_E_T_ = ''
                                AND QP8_PRODUT = I.productCode
                                AND QP8_REVI = I.revision
                            )
                            THEN CAST(1 AS BIT)
                            ELSE CAST(0 AS BIT)
                        END AS hasInspection,

                        -- =========================
                        -- QP6 — Cabeçalho
                        -- =========================
                        (
                            SELECT
                                QP6.QP6_PRODUT AS productCode,
                                QP6.QP6_REVI   AS revision,
                                QP6.QP6_REVINV AS reviewInvalid,
                                QP6.QP6_DESCPO AS description,
                                QP6.QP6_DTCAD  AS createdAt,
                                QP6.QP6_DTINI  AS startDate,
                                QP6.QP6_CADR   AS createdBy,
                                QP6.QP6_PTOLER AS tolerancePercent,
                                QP6.QP6_TIPO   AS inspectionType,
                                QP6.QP6_DOCOBR AS requiresDocument,
                                QP6.QP6_SITPRD AS productStatus,
                                QP6.QP6_DESSTP AS statusDescription,
                                QP6.QP6_UNMED1 AS unit
                            FROM QP6010 QP6 WITH (NOLOCK)
                            WHERE QP6.D_E_L_E_T_ = ''
                            AND QP6.QP6_PRODUT = I.productCode
                            AND QP6.QP6_REVI = I.revision
                            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
                        ) AS qp6,

                        -- =========================
                        -- QP7 — Ensaios mensuráveis
                        -- =========================
                        (
                            SELECT
                                QP7.QP7_PRODUT AS productCode,
                                QP7.QP7_REVI   AS revision,
                                QP7.QP7_ENSAIO AS testCode,
                                QP7.QP7_LABOR  AS labor,
                                QP7.QP7_SEQLAB AS sequence,
                                QP7.QP7_UNIMED AS unit,
                                QP7.QP7_MINMAX AS minMaxType,
                                QP7.QP7_NOMINA AS nominalValue,
                                QP7.QP7_LIE    AS lowerSpecLimit,
                                QP7.QP7_LSE    AS upperSpecLimit,
                                QP7.QP7_LIC    AS lowerControlLimit,
                                QP7.QP7_LSC    AS upperControlLimit,
                                QP7.QP7_CODREC AS reactionCode,
                                QP7.QP7_OPERAC AS operation,
                                QP7.QP7_ENSOBR AS mandatory,
                                QP7.QP7_CERTIF AS certification
                            FROM QP7010 QP7 WITH (NOLOCK)
                            WHERE QP7.D_E_L_E_T_ = ''
                            AND QP7.QP7_PRODUT = I.productCode
                            AND QP7.QP7_REVI = I.revision
                            FOR JSON PATH
                        ) AS qp7,

                        -- =========================
                        -- QP8 — Ensaios textuais
                        -- =========================
                        (
                            SELECT
                                QP8.QP8_PRODUT AS productCode,
                                QP8.QP8_REVI   AS revision,
                                QP8.QP8_ENSAIO AS testCode,
                                QP8.QP8_LABOR  AS labor,
                                QP8.QP8_SEQLAB AS sequence,
                                QP8.QP8_TEXTO  AS text,
                                QP8.QP8_CODREC AS reactionCode,
                                QP8.QP8_OPERAC AS operation,
                                QP8.QP8_ENSOBR AS mandatory,
                                QP8.QP8_CERTIF AS certification
                            FROM QP8010 QP8 WITH (NOLOCK)
                            WHERE QP8.D_E_L_E_T_ = ''
                            AND QP8.QP8_PRODUT = I.productCode
                            AND QP8.QP8_REVI = I.revision
                            FOR JSON PATH
                        ) AS qp8

                    FROM INSPECTION_SCOPE I
                    ORDER BY I.level, I.productCode
                    FOR JSON PATH
                ) AS data
            FROM INSPECTION_SCOPE
            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
        ) AS data;
        """

        # ============================================================
        # Execução
        # ============================================================
        params = (code, max_depth)
        result = self.execute_json(sql, params)

        return {
            "success": True,
            "total": result.get("total", 0),
            "data": result.get("data", [])
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
        """
        Retorna a estrutura completa de inspeção de um produto (QP6, QP7, QP8)
        incluindo seus componentes da árvore SG1010, em formato JSON hierárquico.

        Args:
            code (str): Código do produto principal.
            page (int): Página da consulta (não aplicável na estrutura hierárquica).
            page_size (int): Tamanho de página (não aplicável neste formato).
            max_depth (int): Profundidade máxima da recursão na SG1010.

        Returns:
            dict: Estrutura JSON completa contendo produto, componentes e inspeções.
        """

        # Validações básicas
        if not code:
            raise ValueError("code must be provided")
        if max_depth < 1 or max_depth > 20:
            raise ValueError("max_depth must be between 1 and 20")

        # ============================================================
        # Query SQL única — retorna JSON hierárquico completo
        # ============================================================
        sql = """
        DECLARE 
            @code NVARCHAR(20) = ?, 
            @depth INT = ?, 
            @offset INT = ?, 
            @page_size INT = ?;

        WITH RECURSIVE_BOM AS (
            SELECT 
                G1_COD AS parentCode,
                G1_COMP AS productCode,
                1 AS level
            FROM SG1010 WITH (NOLOCK)
            WHERE D_E_L_E_T_ = '' AND G1_COD = @code

            UNION ALL

            SELECT 
                C.G1_COD,
                C.G1_COMP,
                P.level + 1
            FROM SG1010 C WITH (NOLOCK)
            INNER JOIN RECURSIVE_BOM P 
                ON P.productCode = C.G1_COD
            WHERE C.D_E_L_E_T_ = '' 
            AND P.level < @depth
        ),
        CODES AS (
            SELECT @code AS productCode, NULL AS parentCode, 0 AS level
            UNION ALL
            SELECT productCode, parentCode, level FROM RECURSIVE_BOM
        ),
        TOTAL AS (
            SELECT COUNT(*) AS totalCount FROM CODES
        )
        SELECT 
            (
                SELECT 
                    (SELECT totalCount FROM TOTAL) AS total, -- total real
                    (
                        SELECT 
                            CODES.productCode AS product,
                            CODES.parentCode,
                            CODES.level,

                            -- =========================
                            -- QP6 (Cabeçalho da Inspeção)
                            -- =========================
                            (
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
                                    QP6.QP6_UNMED1
                                FROM QP6010 QP6 WITH (NOLOCK)
                                WHERE QP6.D_E_L_E_T_ = ''
                                AND QP6.QP6_PRODUT = CODES.productCode
                                FOR JSON PATH, INCLUDE_NULL_VALUES
                            ) AS QP6,

                            -- =========================
                            -- QP7 (Ensaios Mensuráveis)
                            -- =========================
                            (
                                SELECT
                                    QP7.QP7_PRODUT,
                                    QP7.QP7_REVI,
                                    QP7.QP7_ENSAIO,
                                    QP7.QP7_LABOR,
                                    QP7.QP7_SEQLAB,
                                    QP7.QP7_UNIMED,
                                    QP7.QP7_MINMAX,
                                    QP7.QP7_NOMINA,
                                    QP7.QP7_LIE,
                                    QP7.QP7_LSE,
                                    QP7.QP7_LIC,
                                    QP7.QP7_LSC,
                                    QP7.QP7_CODREC,
                                    QP7.QP7_OPERAC,
                                    QP7.QP7_ENSOBR,
                                    QP7.QP7_CERTIF
                                FROM QP7010 QP7 WITH (NOLOCK)
                                WHERE QP7.D_E_L_E_T_ = ''
                                AND QP7.QP7_PRODUT = CODES.productCode
                                FOR JSON PATH, INCLUDE_NULL_VALUES
                            ) AS QP7,

                            -- =========================
                            -- QP8 (Ensaios Textuais)
                            -- =========================
                            (
                                SELECT
                                    QP8.QP8_PRODUT,
                                    QP8.QP8_REVI,
                                    QP8.QP8_ENSAIO,
                                    QP8.QP8_LABOR,
                                    QP8.QP8_SEQLAB,
                                    QP8.QP8_TEXTO,
                                    QP8.QP8_CODREC,
                                    QP8.QP8_OPERAC,
                                    QP8.QP8_ENSOBR,
                                    QP8.QP8_CERTIF
                                FROM QP8010 QP8 WITH (NOLOCK)
                                WHERE QP8.D_E_L_E_T_ = ''
                                AND QP8.QP8_PRODUT = CODES.productCode
                                FOR JSON PATH, INCLUDE_NULL_VALUES
                            ) AS QP8

                        FROM CODES
                        ORDER BY CODES.level, CODES.productCode
                        OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY
                        FOR JSON PATH, INCLUDE_NULL_VALUES
                    ) AS data
                FOR JSON PATH, WITHOUT_ARRAY_WRAPPER, INCLUDE_NULL_VALUES
            ) AS data; -- Mantém alias fixo


        """
        # ============================================================
        #  Execução e tratamento do retorno
        # ============================================================
        offset = (page - 1) * page_size
        params = (code, max_depth, offset, page_size)
        result = self.execute_json(sql, params)
        total = result.get("total", 0)
        data_json = result.get("data", [])
        # ============================================================
        #  Monta resposta final
        # ============================================================
        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "data": data_json
        }
    

    # -------------------------------
    # 🔹 CUSTOMERS (SA7010/SA1010) 
    # -------------------------------
    def list_customers(self, code: str, page: int = 1, page_size: int = 50) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        offset = (page - 1) * page_size

        count_sql = """
            SELECT COUNT(*) AS total
            FROM SA7010
            WHERE D_E_L_E_T_ = ''
            AND A7_PRODUTO = ?
        """

        total = int(self.execute_one(count_sql, (code,))["total"] or 0)

        sql = """
            WITH LAST_SALE AS (
                SELECT
                    SD2.D2_COD        AS productCode,
                    SD2.D2_CLIENTE   AS customerCode,
                    SD2.D2_LOJA      AS store,
                    MAX(SD2.D2_EMISSAO) AS lastSaleDate,
                    SUM(SD2.D2_QUANT)   AS totalQuantity,
                    AVG(SD2.D2_PRCVEN)  AS averagePrice
                FROM SD2010 SD2
                WHERE SD2.D_E_L_E_T_ = ''
                AND SD2.D2_COD = ?
                GROUP BY
                    SD2.D2_COD,
                    SD2.D2_CLIENTE,
                    SD2.D2_LOJA
            )

            SELECT
                -- Product
                SB1.B1_COD      AS productCode,
                SB1.B1_DESC     AS productDescription,
                SB1.B1_UM       AS unit,

                -- Customer
                SA1.A1_COD      AS customerCode,
                SA1.A1_LOJA     AS store,
                SA1.A1_NOME     AS customerName,
                SA1.A1_MSBLQL   AS blocked,

                -- Product x Customer
                SA7.A7_CODCLI   AS customerProductCode,
                SA7.A7_DESCCLI  AS customerProductDescription,

                -- Registered price
                SA7.A7_PRECO01  AS registeredPrice,
                SA7.A7_DTREF01  AS registeredPriceDate,

                -- Sales info
                LS.averagePrice AS lastSalePrice,
                LS.lastSaleDate,
                LS.totalQuantity

            FROM SA7010 SA7
            INNER JOIN SA1010 SA1
                ON SA1.A1_COD = SA7.A7_CLIENTE
            AND SA1.A1_LOJA = SA7.A7_LOJA
            AND SA1.D_E_L_E_T_ = ''

            INNER JOIN SB1010 SB1
                ON SB1.B1_COD = SA7.A7_PRODUTO
            AND SB1.D_E_L_E_T_ = ''

            LEFT JOIN LAST_SALE LS
                ON LS.productCode = SA7.A7_PRODUTO
            AND LS.customerCode = SA7.A7_CLIENTE
            AND LS.store = SA7.A7_LOJA

            WHERE
                SA7.D_E_L_E_T_ = ''
                AND SA7.A7_PRODUTO = ?

            ORDER BY SA1.A1_NOME
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        rows = self.execute_query(sql, (code, code, offset, page_size))

        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "data": rows
        }


    # -------------------------------
    # 🔹 PURCHASES (SC7010/SA2010) 
    # -------------------------------
    def list_purchases(self, code: str, page: int = 1, page_size: int = 50) -> dict:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 500:
            raise ValueError("page_size must be between 1 and 500")

        offset = (page - 1) * page_size

        count_sql = """
            SELECT COUNT(DISTINCT C7.C7_NUM) AS total
            FROM SC7010 C7
            WHERE C7.D_E_L_E_T_ = ''
            AND C7.C7_PRODUTO = ?
        """

        total = int(self.execute_one(count_sql, (code,))["total"] or 0)

        sql = """
            SELECT
                C7.C7_NUM        AS orderNumber,
                C7.C7_FILIAL     AS branch,
                C7.C7_EMISSAO    AS issueDate,
                C7.C7_FORNECE    AS supplierCode,
                C7.C7_LOJA       AS store,
                SA2.A2_NOME      AS supplierName,
                C7.C7_PRODUTO    AS productCode,
                SUM(C7.C7_QUANT) AS orderedQuantity,
                AVG(C7.C7_PRECO) AS unitPrice
            FROM SC7010 C7
            LEFT JOIN SA2010 SA2
                ON SA2.A2_COD = C7.C7_FORNECE
            AND SA2.A2_LOJA = C7.C7_LOJA
            AND SA2.D_E_L_E_T_ = ''
            WHERE
                C7.D_E_L_E_T_ = ''
                AND C7.C7_PRODUTO = ?
            GROUP BY
                C7.C7_NUM,
                C7.C7_FILIAL,
                C7.C7_EMISSAO,
                C7.C7_FORNECE,
                C7.C7_LOJA,
                SA2.A2_NOME,
                C7.C7_PRODUTO
            ORDER BY C7.C7_EMISSAO DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        rows = self.execute_query(sql, (code, offset, page_size))

        return {
            "success": True,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
            "data": rows
        }


    # -------------------------------
    # 🔹 SALES SUMMARY
    # -------------------------------
    def get_sales_summary(self, code: str) -> dict:
        """
        Resumo consolidado de vendas realizadas.
        Base: SD2010
        """
        product_sql = """
            SELECT B1_COD, B1_DESC, B1_UM
            FROM SB1010
            WHERE D_E_L_E_T_ = ''
            AND B1_COD = ?
        """
        product = self.execute_one(product_sql, (code,))

        sales_sql = """
            SELECT
                SUM(D2_QUANT)          AS totalQuantity,
                SUM(D2_TOTAL)          AS totalValue,
                AVG(D2_PRCVEN)         AS averagePrice,
                COUNT(DISTINCT D2_DOC) AS documents,
                MIN(D2_EMISSAO)        AS firstSale,
                MAX(D2_EMISSAO)        AS lastSale
            FROM SD2010
            WHERE D_E_L_E_T_ = ''
            AND D2_COD = ?
        """

        summary = self.execute_one(sales_sql, (code,))

        return {
            "success": True,
            "product": {
                "code": code,
                "description": product["B1_DESC"] if product else None,
                "unit": product["B1_UM"] if product else None
            },
            "summary": {
                "totalQuantity": float(summary["totalQuantity"] or 0),
                "totalValue": float(summary["totalValue"] or 0),
                "averagePrice": float(summary["averagePrice"] or 0),
                "documents": int(summary["documents"] or 0),
                "firstSale": summary["firstSale"],
                "lastSale": summary["lastSale"]
            }
        }
    

    def get_sales_open_orders(self, code: str) -> dict:
        """
        Carteira de pedidos de venda (itens em aberto).
        Base: SC6010
        """

        sql = """
            SELECT
                SUM(C6_QTDVEN)                AS openQuantity,
                SUM(C6_QTDVEN * C6_PRCVEN)    AS openValue,
                COUNT(DISTINCT C6_NUM)        AS orders
            FROM SC6010
            WHERE D_E_L_E_T_ = ''
            AND C6_PRODUTO = ?
            AND C6_QTDVEN > 0
        """

        row = self.execute_one(sql, (code,))

        return {
            "success": True,
            "openOrders": {
                "quantity": float(row["openQuantity"] or 0),
                "value": float(row["openValue"] or 0),
                "orders": int(row["orders"] or 0)
            }
        }


    def get_sales_billing(self, code: str) -> dict:
        """
        Resumo de faturamento financeiro por produto.
        Base: SD2010 (itens faturados)
        """

        sql = """
            SELECT
                SUM(D2_TOTAL)          AS billedValue,
                COUNT(DISTINCT D2_DOC) AS documents,
                MIN(D2_EMISSAO)        AS firstBilling,
                MAX(D2_EMISSAO)        AS lastBilling
            FROM SD2010
            WHERE D_E_L_E_T_ = ''
            AND D2_COD = ?
        """

        row = self.execute_one(sql, (code,))

        return {
            "success": True,
            "billing": {
                "value": float(row["billedValue"] or 0),
                "documents": int(row["documents"] or 0),
                "firstBilling": row["firstBilling"],
                "lastBilling": row["lastBilling"]
            }
        }
    

    def get_product_pricing(self, code: str) -> dict:
        """
        Retorna os preços comerciais do produto.

        Bases REAIS:
        - DA1010 → preços por produto
        - DA0010 → descrição da tabela de preço
        - SB1010 → descrição e unidade do produto
        """

        # -------------------------------------------------
        # Produto
        # -------------------------------------------------
        product_sql = """
            SELECT B1_COD, B1_DESC, B1_UM
            FROM SB1010
            WHERE D_E_L_E_T_ = ''
            AND B1_COD = ?
        """
        product = self.execute_one(product_sql, (code,))

        if not product:
            return {"success": False, "message": f"Product {code} not found"}

        pricing_sql = """
            SELECT
                DA1.DA1_CODTAB AS tableCode,
                DA0.DA0_DESCRI AS tableDescription,
                DA1.DA1_PRCVEN AS salePrice,
                DA1.DA1_PRCMAX AS maxPrice,
                DA1.DA1_VLRDES AS discountValue,
                DA1.DA1_PERDES AS discountPercent,
                DA1.DA1_QTDLOT AS lotQuantity,
                DA1.DA1_ESTADO AS state,
                DA1.DA1_TPOPER AS operationType,
                DA1.DA1_MOEDA  AS currency,
                DA1.DA1_DATVIG AS validFrom,
                DA1.DA1_ATIVO  AS active
            FROM DA1010 DA1
            INNER JOIN DA0010 DA0
                ON DA0.DA0_FILIAL = DA1.DA1_FILIAL
            AND DA0.DA0_CODTAB = DA1.DA1_CODTAB
            AND DA0.D_E_L_E_T_ = ''
            WHERE DA1.D_E_L_E_T_ = ''
            AND DA1.DA1_CODPRO = ?
            ORDER BY DA1.DA1_CODTAB, DA1.DA1_DATVIG DESC
        """

        rows = self.execute_query(pricing_sql, (code,))

        return {
            "success": True,
            "product": {
                "code": product["B1_COD"],
                "description": product["B1_DESC"],
                "unit": product["B1_UM"]
            },
            "prices": rows
        }
