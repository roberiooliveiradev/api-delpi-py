from app.repositories.base_repository import BaseRepository
from app.utils.logger import log_info, log_error
import re
from typing import Dict, Any, List, Tuple, Optional, Set


class DataRepository(BaseRepository):
    """
    Repositório para consultas dinâmicas (rota /data/query).

    - Suporta múltiplas CTEs (WITH cte1 AS (...), cte2 AS (...), ...).
    - Tudo que funciona na consulta principal funciona dentro das CTEs.
    - CTEs NUNCA paginam.
    """

    ALLOWED_OPERATORS = {
        "=", ">", "<", ">=", "<=", "<>",
        "LIKE", "NOT LIKE",
        "IN", "NOT IN",
        "BETWEEN",
        "IS NULL", "IS NOT NULL",
    }

    ALLOWED_JOIN_TYPES = {"INNER", "LEFT", "RIGHT", "FULL"}

    SAFE_IDENTIFIER = re.compile(
        r"^[A-Za-z0-9_.()\s]+(AS\s+[A-Za-z0-9_]+)?$",
        re.IGNORECASE,
    )

    ALLOWED_SQL_FUNCTIONS = {
        "TRIM", "LTRIM", "RTRIM", "UPPER", "LOWER", "LEN",
        "CAST", "CONVERT",
        "SUM", "COUNT", "MIN", "MAX", "AVG",
    }

    SAFE_KEYS = {
        "with", "tables", "columns", "joins", "filters",
        "order_by", "group_by", "aggregates", "having",
        "rollup", "cube", "auto_aggregate", "aliases",
        "page", "page_size",
    }

    # ======================================================
    # 🔹 ENTRYPOINT PRINCIPAL
    # ======================================================
    def execute_dynamic_query(self, payload: dict) -> dict:
        try:
            main_payload = self._sanitize_payload(payload, allow_with=True)

            with_blocks = main_payload.get("with") or {}
            with_sql, cte_names = self._build_with_clause(with_blocks)

            main_sql, pagination = self._build_select_sql(
                main_payload, for_cte=False, cte_names=cte_names
            )

            final_sql = with_sql + main_sql
            log_info(f"[DATA_QUERY] SQL gerado: {final_sql}")

            rows = self.execute_query(final_sql)
            return {
                "success": True,
                "sql": final_sql,
                "data": rows,
                **pagination,
                "total": len(rows),
                "pages": 1,
            }

        except Exception as e:
            log_error(f"[DATA_QUERY] ERRO: {repr(e)}")
            return {"success": False, "message": f"{e}"}

    # ======================================================
    # 🔹 SANITIZAÇÃO DE PAYLOAD
    # ======================================================
    def _sanitize_payload(self, payload: Any, allow_with: bool) -> Dict[str, Any]:
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump(exclude_none=True, by_alias=True)
        elif hasattr(payload, "dict"):
            payload = payload.dict(exclude_none=True, by_alias=True)

        cleaned = {k: v for k, v in payload.items() if k in self.SAFE_KEYS}

        if not allow_with:
            cleaned.pop("with", None)

        # Paginação automática segura
        if cleaned.get("page") is None:
            cleaned["page"] = 1
        if cleaned.get("page_size") is None:
            cleaned["page_size"] = 100

        cleaned.setdefault("aggregates", {})
        cleaned.setdefault("group_by", [])

        return cleaned

    # ======================================================
    # 🔹 BLOCO WITH (MÚLTIPLAS CTEs)
    # ======================================================
    def _build_with_clause(self, with_blocks: Any) -> Tuple[str, Set[str]]:
        if not with_blocks:
            return "", set()

        cte_names: Set[str] = set(with_blocks.keys())
        cte_clauses: List[str] = []

        for cte_name, cte_payload in with_blocks.items():
            cte_sql = self._build_cte_sql(cte_payload, cte_names)
            cte_clauses.append(f"{cte_name} AS ({cte_sql})")

        return f"WITH {', '.join(cte_clauses)} ", cte_names

    # ======================================================
    # 🔹 CTE builder
    # ======================================================
    def _build_cte_sql(self, payload: dict, cte_names: Set[str]) -> str:
        cleaned = self._sanitize_payload(payload, allow_with=False)
        cleaned["page"] = None
        cleaned["page_size"] = None
        sql, _ = self._build_select_sql(cleaned, for_cte=True, cte_names=cte_names)
        return sql

    # ======================================================
    # 🔹 SELECT principal + HAVING fix
    # ======================================================
    def _build_select_sql(
        self, payload: Dict[str, Any], for_cte: bool, cte_names: Set[str]
    ) -> Tuple[str, Dict[str, Optional[int]]]:

        tables = payload.get("tables") or []
        columns = payload.get("columns") or ["*"]
        joins = payload.get("joins") or []
        filters = payload.get("filters")
        order_by = payload.get("order_by") or []
        group_by = payload.get("group_by") or []
        aggregates = payload.get("aggregates") or {}
        having = payload.get("having") or {}
        aliases = payload.get("aliases") or {}
        rollup = payload.get("rollup", False)
        cube = payload.get("cube", False)
        auto_aggregate = payload.get("auto_aggregate", False)

        page = payload.get("page")
        page_size = payload.get("page_size")

        # Aliases automáticos
        def apply_alias(table: str) -> str:
            if " AS " in table.upper():
                return table
            if table in aliases:
                return f"{table} AS {aliases[table]}"
            return table

        tables = [apply_alias(t) for t in tables]

        # SELECT e agregados
        select_parts: List[str] = []
        aggregate_alias_map = {}

        # aplicar auto_aggregate
        if auto_aggregate and group_by:
            new_cols = []
            new_aggs = dict(aggregates)
            gb = set(group_by)

            for col in columns:
                if col in gb or col == "*" or "(" in col:
                    new_cols.append(col)
                else:
                    if col not in new_aggs:
                        new_aggs[col] = "SUM"

            columns = new_cols
            aggregates = new_aggs

        # Monta colunas simples
        select_parts.extend(columns)

        # Monta agregados
        for f, func in aggregates.items():
            alias = f.split(".")[-1]
            alias = f"{func.lower()}_{alias}"

            aggregate_alias_map[alias] = f"{func.upper()}({f})"
            select_parts.append(f"{func.upper()}({f}) AS {alias}")

        # FROM principal
        main_table = tables[0]
        main_name, main_alias = self._parse_table_alias(main_table)

        sql = f"SELECT {', '.join(select_parts)} FROM {main_name}"
        if main_alias:
            sql += f" AS {main_alias}"

        # tabelas adicionais
        for t in tables[1:]:
            tn, ta = self._parse_table_alias(t)
            sql += f", {tn}"
            if ta:
                sql += f" AS {ta}"

        # JOINs com condições complexas
        for j in joins:
            sql += f" {self._build_join_clause(j)}"

        # WHERE
        if filters:
            wc = self._build_filter_clause(filters)
            if wc:
                sql += f" WHERE {wc}"

        # GROUP BY
        if group_by:
            gb_expr = ", ".join(group_by)
            if rollup:
                sql += f" GROUP BY ROLLUP({gb_expr})"
            elif cube:
                sql += f" GROUP BY CUBE({gb_expr})"
            else:
                sql += f" GROUP BY {gb_expr}"

        # HAVING fix (usando funções reais)
        if having:
            h_parts = []
            for field, cond in having.items():
                if field in aggregate_alias_map:
                    field_expr = aggregate_alias_map[field]
                else:
                    field_expr = field

                op = cond.get("op").upper()
                val = cond.get("value")

                if op in ("IS NULL", "IS NOT NULL"):
                    h_parts.append(f"{field_expr} {op}")
                else:
                    h_parts.append(f"{field_expr} {op} '{val}'")

            sql += " HAVING " + " AND ".join(h_parts)

        # ORDER BY
        if order_by:
            orders = [
                f"{ob['field']} {ob.get('direction','ASC').upper()}" for ob in order_by
            ]
            sql += " ORDER BY " + ", ".join(orders)
        else:
            # sem ORDER BY → paginação desabilitada
            page = None
            page_size = None

        # PAGINAÇÃO SEGURA
        if (not for_cte) and page and page_size and order_by:
            offset = (page - 1) * page_size
            sql += f" OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
            return sql, {"page": page, "page_size": page_size}

        return sql, {"page": None, "page_size": None}

    # ======================================================
    # 🔹 JOIN builder com field-to-field
    # ======================================================
    def _build_join_clause(self, j: dict) -> str:
        if hasattr(j, "model_dump"):
            j = j.model_dump(exclude_none=True, by_alias=True)

        jt = j.get("type", "INNER").upper()
        table = j.get("table")

        tn, ta = self._parse_table_alias(table)
        sql = f"{jt} JOIN {tn}"
        if ta:
            sql += f" AS {ta}"

        # JOIN simples
        if "left" in j:
            return sql + f" ON {j['left']} = {j['right']}"

        # JOIN complexo
        conds = j.get("conditions") or [j["on"]]
        on_parts = []
        for c in conds:
            left = c["left"]
            op = c["op"].upper()
            right = c["right"]

            field_ops = {
                "=FIELD": "=",
                "<>FIELD": "<>",
                ">FIELD": ">",
                "<FIELD": "<",
                ">=FIELD": ">=",
                "<=FIELD": "<=",
            }

            if op in field_ops:
                on_parts.append(f"{left} {field_ops[op]} {right}")
            else:
                on_parts.append(f"{left} {op} '{right}'")

        return sql + " ON " + " AND ".join(on_parts)

    # ======================================================
    # 🔹 FILTROS
    # ======================================================
    def _build_filter_clause(self, filters: Any) -> str:
        if hasattr(filters, "model_dump"):
            filters = filters.model_dump(exclude_none=True, by_alias=True)

        if isinstance(filters, dict):
            if "and" in filters:
                parts = [self._build_filter_clause(f) for f in filters["and"]]
                return "(" + " AND ".join(p for p in parts if p) + ")"

            if "or" in filters:
                parts = [self._build_filter_clause(f) for f in filters["or"]]
                return "(" + " OR ".join(p for p in parts if p) + ")"

            # filtro simples
            for field, cond in filters.items():
                op = cond["op"].upper()
                val = cond["value"]

                field_ops = {
                    "=FIELD": "=",
                    "<>FIELD": "<>",
                    ">FIELD": ">",
                    "<FIELD": "<",
                    ">=FIELD": ">=",
                    "<=FIELD": "<=",
                }

                if op in field_ops:
                    return f"{field} {field_ops[op]} {val}"
                else:
                    return f"{field} {op} '{val}'"

        return ""

    # ======================================================
    # 🔹 alias helper
    # ======================================================
    def _parse_table_alias(self, table: str) -> Tuple[str,Optional[str]]:
        if " AS " in table.upper():
            t, a = re.split(r"\s+AS\s+", table, flags=re.IGNORECASE)
            return t.strip(), a.strip()
        parts = table.split()
        return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], None)
