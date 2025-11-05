# app/repositories/data_repository.py
from app.repositories.base_repository import BaseRepository
from app.utils.logger import log_info, log_error
import re

class DataRepository(BaseRepository):
    """
    Repositório analítico dinâmico — agora com suporte a aliases de tabelas.
    """

    ALLOWED_OPERATORS = {
        "=", ">", "<", ">=", "<=", "<>",
        "LIKE", "NOT LIKE",
        "IN", "NOT IN",
        "BETWEEN",
        "IS NULL", "IS NOT NULL"
    }
    ALLOWED_JOIN_TYPES = {"INNER", "LEFT", "RIGHT", "FULL"}
    SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.()*]+$")
    ALLOWED_SQL_FUNCTIONS = {"TRIM", "LTRIM", "RTRIM", "UPPER", "LOWER", "LEN", "CAST", "CONVERT"}

    # ======================================================
    # 🔹 MÉTODO PRINCIPAL
    # ======================================================
    def execute_dynamic_query(self, payload: dict) -> dict:
        try:
            # ✅ Compatibilidade com Pydantic v1/v2 e dicionários
            if hasattr(payload, "model_dump"):
                payload = payload.model_dump(exclude_none=True, by_alias=True)
            elif hasattr(payload, "dict"):
                payload = payload.dict(exclude_none=True, by_alias=True)
            elif not isinstance(payload, dict):
                raise TypeError("O payload recebido não é um dicionário ou modelo válido.")

            # 🔹 Normalização
            tables = payload.get("tables") or []
            columns = payload.get("columns") or ["*"]
            joins = payload.get("joins") or []
            filters = payload.get("filters") or None
            order_by = payload.get("order_by") or []
            group_by = payload.get("group_by") or []
            aggregates = payload.get("aggregates") or {}
            having = payload.get("having") or {}
            rollup = payload.get("rollup", False)
            cube = payload.get("cube", False)
            auto_aggregate = payload.get("auto_aggregate", False)
            aliases = payload.get("aliases") or {}

            # 🔹 Paginação opcional
            page = payload.get("page")
            page_size = payload.get("page_size")

            if not tables:
                raise ValueError("Informe ao menos uma tabela.")

            main_table = tables[0]

            # ======================================================
            # 🔹 Validação de nomes / aliases
            # ======================================================
            for t in tables + columns + group_by + list(aggregates.keys()):
                if t in ("*",) or t.endswith(".*"):
                    continue
                if "(" in t and ")" in t:
                    func_name = t.split("(")[0].upper()
                    if func_name not in self.ALLOWED_SQL_FUNCTIONS:
                        raise ValueError(f"Função SQL não permitida: {func_name}")
                    continue
                if not re.match(r"^[A-Za-z0-9_.()\s]+(AS\s+[A-Za-z0-9_]+)?$", t, re.IGNORECASE):
                    raise ValueError(f"Nome inválido ou alias não permitido: {t}")

            # ======================================================
            # 🔹 SELECT base
            # ======================================================
            select_parts = list(columns)
            for field, func in aggregates.items():
                select_parts.append(f"{func.upper()}({field}) AS {func.lower()}_{field.split('.')[-1]}")

            main_table_name, main_alias = self._parse_table_alias(main_table)
            sql = f"SELECT {', '.join(select_parts)} FROM {main_table_name}"
            if main_alias:
                sql += f" AS {main_alias}"

            # ======================================================
            # 🔹 JOINs
            # ======================================================
            for j in joins:
                join_type = j.get("type", "INNER").upper()
                if join_type not in self.ALLOWED_JOIN_TYPES:
                    raise ValueError(f"Tipo de JOIN inválido: {join_type}")

                join_table_name, join_alias = self._parse_table_alias(j.get("table", ""))
                left, right = j.get("left"), j.get("right")

                sql += f" {join_type} JOIN {join_table_name}"
                if join_alias:
                    sql += f" AS {join_alias}"
                sql += f" ON {left} = {right}"

            # ======================================================
            # 🔹 WHERE
            # ======================================================
            if filters:
                where_clause = self._build_filter_clause(filters)
                if where_clause:
                    sql += f" WHERE {where_clause}"

            # ======================================================
            # 🔹 GROUP BY / ROLLUP / CUBE
            # ======================================================
            if group_by:
                group_expr = ", ".join(group_by)
                if rollup:
                    sql += f" GROUP BY ROLLUP({group_expr})"
                elif cube:
                    sql += f" GROUP BY CUBE({group_expr})"
                else:
                    sql += f" GROUP BY {group_expr}"

            # ======================================================
            # 🔹 HAVING
            # ======================================================
            if having:
                having_clauses = []
                for field, cond in having.items():
                    op = cond.get("op", "=").upper()
                    val = cond.get("value")
                    if op in ("IS NULL", "IS NOT NULL"):
                        having_clauses.append(f"{field} {op}")
                    elif op == "BETWEEN":
                        having_clauses.append(f"{field} BETWEEN '{val[0]}' AND '{val[1]}'")
                    elif op in ("IN", "NOT IN"):
                        val_str = ", ".join(f"'{v}'" for v in val)
                        having_clauses.append(f"{field} {op} ({val_str})")
                    else:
                        having_clauses.append(f"{field} {op} '{val}'")
                sql += " HAVING " + " AND ".join(having_clauses)

            # ======================================================
            # 🔹 ORDER BY
            # ======================================================
            if order_by:
                order_clause = ", ".join(
                    f"{ob['field']} {ob.get('direction', 'ASC').upper()}" for ob in order_by
                )
            else:
                order_clause = "R_E_C_N_O_ ASC"
            sql += f" ORDER BY {order_clause}"

            # ======================================================
            # 🔹 Paginação condicional
            # ======================================================
            if page is not None and page_size is not None:
                offset = (page - 1) * page_size
                sql += f" OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
                pagination_info = {"page": page, "page_size": page_size}
            else:
                pagination_info = {"page": None, "page_size": None}

            # ======================================================
            # 🔹 Execução
            # ======================================================
            rows = self.execute_query(sql)
            return {
                "success": True,
                "sql": sql,
                "data": rows,
                **pagination_info,
                "total": len(rows),
                "pages": 1,
            }

        except Exception as e:
            log_error(f"Erro na consulta analítica: {e}")
            return {"success": False, "message": f"500: {e}"}

    # ======================================================
    # 🔹 CONSTRUÇÃO RECURSIVA DOS FILTROS
    # ======================================================
    def _build_filter_clause(self, filters: dict) -> str:
        if not filters:
            return ""

        if isinstance(filters, dict):
            and_key = "and" if "and" in filters else "and_" if "and_" in filters else None
            or_key = "or" if "or" in filters else "or_" if "or_" in filters else None

            if and_key:
                clauses = [self._build_filter_clause(f) for f in filters[and_key] if f]
                return f"({' AND '.join([c for c in clauses if c])})"
            if or_key:
                clauses = [self._build_filter_clause(f) for f in filters[or_key] if f]
                return f"({' OR '.join([c for c in clauses if c])})"

            parts = []
            for field, cond in filters.items():
                if not isinstance(cond, dict) or "op" not in cond:
                    continue
                op = cond.get("op", "=").upper()
                val = cond.get("value")

                if op not in self.ALLOWED_OPERATORS:
                    raise ValueError(f"Operador não permitido: {op}")

                if op in ("IS NULL", "IS NOT NULL"):
                    parts.append(f"{field} {op}")
                elif op in ("IN", "NOT IN"):
                    val_str = ", ".join(f"'{v}'" for v in val)
                    parts.append(f"{field} {op} ({val_str})")
                elif op == "BETWEEN":
                    if not isinstance(val, list) or len(val) != 2:
                        raise ValueError("BETWEEN requer [min, max]")
                    parts.append(f"{field} BETWEEN '{val[0]}' AND '{val[1]}'")
                else:
                    parts.append(f"{field} {op} '{val}'")
            return " AND ".join(parts)

        if isinstance(filters, list):
            return " AND ".join([c for c in [self._build_filter_clause(f) for f in filters] if c])
        return ""

    # ======================================================
    # 🔹 SUPORTE A ALIAS
    # ======================================================
    def _parse_table_alias(self, table_name: str) -> tuple[str, str | None]:
        """
        Retorna (tabela, alias) a partir de 'SB1010 AS P' ou 'SB1010 P'.
        """
        if not table_name:
            return "", None
        parts = re.split(r"\s+AS\s+|\s+", table_name.strip(), flags=re.IGNORECASE)
        if len(parts) == 2:
            return parts[0], parts[1]
        return table_name.strip(), None
