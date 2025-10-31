# app/repositories/data_repository.py



from app.repositories.base_repository import BaseRepository
from app.utils.logger import log_info, log_error
import re


class DataRepository(BaseRepository):
    """
    Repositório analítico dinâmico — suporta:
    - JOINs e filtros seguros (inclusive AND/OR aninhados)
    - GROUP BY, HAVING, ROLLUP e CUBE
    - Agregações automáticas (SUM/AVG/COUNT)
    - Operadores avançados: IN, NOT IN, BETWEEN, IS NULL, IS NOT NULL, LIKE, NOT LIKE
    - Paginação e ordenação
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
            if hasattr(payload, "model_dump"):  # Pydantic v2
                payload = payload.model_dump(exclude_none=True, by_alias=True)
            elif hasattr(payload, "dict"):      # Pydantic v1
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

            # 🔹 Paginação opcional
            page = payload.get("page")
            page_size = payload.get("page_size")

            if not tables:
                raise ValueError("Informe ao menos uma tabela.")

            main_table = tables[0]

            # ======================================================
            # 🔹 Validação de nomes
            # ======================================================
            for t in tables + columns + group_by + list(aggregates.keys()):
                if t in ("*",) or t.endswith(".*"):
                    continue
                if "(" in t and ")" in t:
                    func_name = t.split("(")[0].upper()
                    if func_name not in self.ALLOWED_SQL_FUNCTIONS:
                        raise ValueError(f"Função SQL não permitida: {func_name}")
                    continue
                if not self.SAFE_IDENTIFIER.match(t):
                    raise ValueError(f"Nome inválido: {t}")

            # ======================================================
            # 🔹 SELECT base
            # ======================================================
            select_parts = list(columns)
            for field, func in aggregates.items():
                select_parts.append(f"{func.upper()}({field}) AS {func.lower()}_{field.split('.')[-1]}")

            sql = f"SELECT {', '.join(select_parts)} FROM {main_table}"

            # ======================================================
            # 🔹 JOINs
            # ======================================================
            for j in joins:
                join_type = j.get("type", "INNER").upper()
                if join_type not in self.ALLOWED_JOIN_TYPES:
                    raise ValueError(f"Tipo de JOIN inválido: {join_type}")
                join_table = j.get("table", "")
                left, right = j.get("left"), j.get("right")
                sql += f" {join_type} JOIN {join_table} ON {left} = {right}"

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
        """
        Monta recursivamente os filtros SQL com suporte a 'and' / 'or' aninhados.
        Compatível com o alias interno do Pydantic ('and_' e 'or_').
        """
        if not filters:
            return ""

        # 🧩 Suporte tanto a 'and' quanto 'and_'
        if isinstance(filters, dict):
            and_key = "and" if "and" in filters else "and_" if "and_" in filters else None
            or_key = "or" if "or" in filters else "or_" if "or_" in filters else None

            # 🔹 AND lógico
            if and_key:
                subfilters = filters[and_key]
                clauses = []
                for f in subfilters:
                    clause = self._build_filter_clause(f)
                    if clause:
                        clauses.append(clause)
                return f"({' AND '.join(clauses)})" if clauses else ""

            # 🔹 OR lógico
            if or_key:
                subfilters = filters[or_key]
                clauses = []
                for f in subfilters:
                    clause = self._build_filter_clause(f)
                    if clause:
                        clauses.append(clause)
                return f"({' OR '.join(clauses)})" if clauses else ""

            # 🔹 Caso base — dicionário simples {campo: {op, value}}
            parts = []
            for field, cond in filters.items():
                if not isinstance(cond, dict) or "op" not in cond:
                    continue
                op = cond.get("op", "=").upper()
                val = cond.get("value")

                if op not in self.ALLOWED_OPERATORS:
                    raise ValueError(f"Operador não permitido: {op}")

                # Construção da cláusula
                if op in ("IS NULL", "IS NOT NULL"):
                    part = f"{field} {op}"
                elif op in ("IN", "NOT IN"):
                    val_str = ", ".join(f"'{v}'" for v in val)
                    part = f"{field} {op} ({val_str})"
                elif op == "BETWEEN":
                    if not isinstance(val, list) or len(val) != 2:
                        raise ValueError("BETWEEN requer [min, max]")
                    part = f"{field} BETWEEN '{val[0]}' AND '{val[1]}'"
                else:
                    part = f"{field} {op} '{val}'"

                parts.append(part)

            return " AND ".join(parts)

        # 🔹 Caso improvável: lista direta
        if isinstance(filters, list):
            clauses = [self._build_filter_clause(f) for f in filters]
            clauses = [c for c in clauses if c]
            return " AND ".join(clauses)

        return ""
