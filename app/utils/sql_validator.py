# app/utils/sql_validator.py
import re
import json
from pathlib import Path
from app.utils.logger import log_error

class SqlValidator:
    """
    Validador SQL seguro — agora com suporte a CTEs (WITH e WITH RECURSIVE).
    Garante que apenas SELECTs em tabelas permitidas sejam executados.
    """

    BANNED_KEYWORDS = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "CREATE", "TRUNCATE", "MERGE", "EXEC", "GRANT",
        "REVOKE", "BEGIN", "COMMIT", "ROLLBACK",
    ]

    def __init__(self):
        self.allowed_tables = self._load_allowed_tables()

    def _load_allowed_tables(self):
        try:
            config_path = Path(__file__).parent.parent / "config" / "allowed_tables.json"
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {t.upper() for t in data.get("allowed_tables", [])}
        except Exception as e:
            log_error(f"[SQL_VALIDATOR] Falha ao carregar allowed_tables.json: {e}")
            raise RuntimeError("Erro ao carregar whitelist de tabelas permitidas")

    def validate(self, sql: str) -> None:
        """Executa todas as validações de segurança no SQL bruto, incluindo CTEs recursivas."""

        if not sql or not isinstance(sql, str):
            raise ValueError("SQL inválido ou vazio.")

        sql_clean = sql.strip().upper()

        # ✅ Aceita "WITH" e "WITH RECURSIVE", exige SELECT final
        if sql_clean.startswith("WITH ") or sql_clean.startswith("WITH RECURSIVE "):
            if "SELECT" not in sql_clean:
                raise PermissionError("CTE detectada, mas nenhuma instrução SELECT encontrada.")
        elif not sql_clean.startswith("SELECT "):
            raise PermissionError("Apenas instruções SELECT ou WITH ... SELECT são permitidas.")

        # 🚫 Palavras proibidas
        for kw in self.BANNED_KEYWORDS:
            if re.search(rf"\b{kw}\b", sql_clean, re.IGNORECASE):
                raise PermissionError(f"Comando proibido detectado: {kw}")

        # 🔍 Captura o bloco completo das CTEs (até o SELECT principal)
        cte_block = ""
        depth = 0
        start_idx = sql.upper().find("WITH")
        for i, ch in enumerate(sql[start_idx:], start=start_idx):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif depth <= 0 and sql[i:i+6].upper().startswith("SELECT"):
                cte_block = sql[start_idx:i]
                break

        # 🔍 Extrai nomes das CTEs
        cte_names = set()
        if cte_block:
            cte_defs = re.findall(r"\b([A-Za-z0-9_]+)\s+AS\s*\(", cte_block, re.IGNORECASE)
            cte_names = {n.upper() for n in cte_defs}

        # 🔍 Extrai tabelas de FROM e JOIN
        tables = re.findall(r"\bFROM\s+([A-Za-z0-9_]+)", sql, re.IGNORECASE)
        tables += re.findall(r"\bJOIN\s+([A-Za-z0-9_]+)", sql, re.IGNORECASE)

        for t in tables:
            if not t:
                continue
            if "(" in t or ")" in t:
                continue
            if t.upper() in cte_names:
                continue
            if t.upper() not in self.allowed_tables:
                raise PermissionError(f"Tabela '{t}' não autorizada (fora da whitelist allowed_tables.json).")

        # 🚫 Impede múltiplos comandos
        sql_no_comments = re.sub(r"(--[^\n]*|/\*.*?\*/)", "", sql, flags=re.DOTALL)
        parts = [p.strip() for p in sql_no_comments.strip().split(";") if p.strip()]

        if len(parts) > 1:
            raise PermissionError("⚠️ Detecção de múltiplos comandos SQL — apenas uma instrução é permitida.")

        return True


