# app/utils/sql_validator.py
import re
import json
from pathlib import Path
from app.utils.logger import log_error


class SqlValidator:
    """
    Validador SQL seguro para SQL Server (Protheus).

    Permite:
    - DECLARE (variáveis escalares)
    - DECLARE @T TABLE (...) (controlado)
    - SET @X = literal | @Y
    - SELECT simples ou múltiplos SELECTs
    - WITH / CTE

    Bloqueia:
    - DDL / DML
    - EXEC / TRANSACTIONS
    - SETs perigosos
    """

    BANNED_KEYWORDS = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "CREATE", "TRUNCATE", "MERGE", "EXEC",
        "GRANT", "REVOKE",
        "BEGIN", "COMMIT", "ROLLBACK",
    ]

    MAX_SELECTS = 5  # limite de segurança

    def __init__(self):
        self.allowed_tables = self._load_allowed_tables()

    # ------------------------------------------------------------------
    # 🔹 Config
    # ------------------------------------------------------------------
    def _load_allowed_tables(self) -> set[str]:
        try:
            config_path = (
                Path(__file__).parent.parent / "config" / "allowed_tables.json"
            )
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {t.upper() for t in data.get("allowed_tables", [])}
        except Exception as e:
            log_error(f"[SQL_VALIDATOR] Erro ao carregar allowed_tables.json: {e}")
            raise RuntimeError("Erro ao carregar whitelist de tabelas")

    # ------------------------------------------------------------------
    # 🔹 Validação principal
    # ------------------------------------------------------------------
    def validate(self, sql: str) -> None:
        if not sql or not isinstance(sql, str):
            raise ValueError("SQL inválido ou vazio.")

        sql_clean = sql.strip().upper()

        # 🔒 Entrada permitida
        if not sql_clean.startswith(("DECLARE", "SET", "WITH", "SELECT")):
            raise PermissionError(
                "Somente instruções DECLARE, SET, SELECT ou WITH são permitidas."
            )

        # 🚫 Keywords proibidas
        for kw in self.BANNED_KEYWORDS:
            if re.search(rf"\b{kw}\b", sql_clean, re.IGNORECASE):
                raise PermissionError(f"Comando proibido detectado: {kw}")

        # 🚫 Remove comentários
        sql_no_comments = re.sub(
            r"(--[^\n]*|/\*.*?\*/)", "", sql, flags=re.DOTALL
        )

        # 🔹 Divide em instruções
        statements = [s.strip() for s in sql_no_comments.split(";") if s.strip()]

        select_count = 0

        for stmt in statements:
            stmt_upper = stmt.upper()

            # ----------------------------------------------------------
            # DECLARE
            # ----------------------------------------------------------
            if stmt_upper.startswith("DECLARE"):
                # DECLARE escalar
                if re.match(
                    r"^DECLARE\s+@[A-Z0-9_]+\s+[A-Z0-9()_,\s]+(\s*=\s*[^;]+)?$",
                    stmt_upper,
                ):
                    continue

                # DECLARE TABLE
                if re.match(
                    r"^DECLARE\s+@[A-Z0-9_]+\s+TABLE\s*\([\s\S]*?\)$",
                    stmt_upper,
                ):
                    if re.search(
                        r"\b(SELECT|PRIMARY|FOREIGN|CONSTRAINT|INDEX)\b",
                        stmt_upper,
                    ):
                        raise PermissionError(
                            "DECLARE TABLE contém definição não permitida."
                        )
                    continue

                raise PermissionError("DECLARE inválido ou não suportado.")

            # ----------------------------------------------------------
            # SET
            # ----------------------------------------------------------
            if stmt_upper.startswith("SET"):
                if not re.match(
                    r"^SET\s+@[A-Z0-9_]+\s*=\s*(NULL|'[^']*'|\d+|@[A-Z0-9_]+)$",
                    stmt_upper,
                ):
                    raise PermissionError("SET inválido ou não suportado.")
                continue

            # ----------------------------------------------------------
            # SELECT / WITH
            # ----------------------------------------------------------
            if stmt_upper.startswith("WITH") or stmt_upper.startswith("SELECT"):
                select_count += 1
                continue

            # ----------------------------------------------------------
            # BLOQUEIO FINAL
            # ----------------------------------------------------------
            raise PermissionError(
                "Somente instruções DECLARE, SET e SELECT são permitidas."
            )

        # 🔒 Regras finais
        if select_count < 1:
            raise PermissionError(
                "É obrigatório existir pelo menos um SELECT no SQL."
            )

        if select_count > self.MAX_SELECTS:
            raise PermissionError(
                f"Limite máximo de SELECTs excedido ({self.MAX_SELECTS})."
            )

        # ------------------------------------------------------------------
        # 🔍 Validação de tabelas (whitelist)
        # ------------------------------------------------------------------
        tables = re.findall(r"\bFROM\s+([A-Z0-9_]+)", sql_clean, re.IGNORECASE)
        tables += re.findall(r"\bJOIN\s+([A-Z0-9_]+)", sql_clean, re.IGNORECASE)

        for t in tables:
            if not t:
                continue
            if "(" in t or ")" in t:
                continue
            if t.upper() not in self.allowed_tables:
                raise PermissionError(
                    f"Tabela '{t}' não autorizada (fora da whitelist)."
                )

        return True
