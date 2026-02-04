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
    - WITH / CTE (inclusive múltiplas CTEs)
      -> nomes de CTE NÃO precisam estar na whitelist

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

    MAX_SELECTS = 10

    def __init__(self):
        self.allowed_tables = self._load_allowed_tables()

    # ------------------------------------------------------------------
    # 🔹 Config
    # ------------------------------------------------------------------
    def _load_allowed_tables(self) -> set[str]:
        try:
            config_path = Path(__file__).parent.parent / "config" / "allowed_tables.json"
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {t.upper() for t in data.get("allowed_tables", [])}
        except Exception as e:
            log_error(f"[SQL_VALIDATOR] Erro ao carregar allowed_tables.json: {e}")
            raise RuntimeError("Erro ao carregar whitelist de tabelas")

    # ------------------------------------------------------------------
    # 🔹 Remove comentários SQL (robusto)
    # ------------------------------------------------------------------
    def _strip_sql_comments(self, sql: str) -> str:
        """
        Remove TODOS os comentários SQL:
        - -- comentário
        - /* comentário */
        Preserva conteúdo dentro de strings.
        """
        result = []
        i = 0
        in_string = False
        length = len(sql)

        while i < length:
            ch = sql[i]
            next_ch = sql[i + 1] if i + 1 < length else ""

            # controle de strings
            if ch == "'":
                in_string = not in_string
                result.append(ch)
                i += 1
                continue

            if not in_string:
                # comentário --
                if ch == "-" and next_ch == "-":
                    i += 2
                    while i < length and sql[i] not in ("\n", "\r"):
                        i += 1
                    continue

                # comentário /* */
                if ch == "/" and next_ch == "*":
                    i += 2
                    while i + 1 < length and not (sql[i] == "*" and sql[i + 1] == "/"):
                        i += 1
                    i += 2
                    continue

            result.append(ch)
            i += 1

        return "".join(result)

    # ------------------------------------------------------------------
    # 🔹 Extrair nomes de CTEs
    # ------------------------------------------------------------------
    def _extract_cte_names(self, sql_up: str) -> set[str]:
        """
        Extrai nomes de CTEs do(s) bloco(s) WITH ... AS ( ... )
        """
        cte_names: set[str] = set()
        pos = 0

        while True:
            idx = sql_up.find("WITH", pos)
            if idx == -1:
                break

            i = idx + 4
            depth = 0

            while i < len(sql_up):
                if sql_up[i] == "(":
                    depth += 1
                elif sql_up[i] == ")":
                    depth = max(0, depth - 1)

                if depth == 0 and sql_up.startswith("SELECT", i):
                    break

                i += 1

            with_block = sql_up[idx:i]
            found = re.findall(r"\b([A-Z0-9_]+)\s+AS\s*\(", with_block)

            for name in found:
                cte_names.add(name.upper())

            pos = i

        return cte_names

    # ------------------------------------------------------------------
    # 🔹 Validação principal
    # ------------------------------------------------------------------
    def validate(self, sql: str) -> None:
        if not sql or not isinstance(sql, str):
            raise ValueError("SQL inválido ou vazio.")

        # 1️⃣ Remove comentários ANTES de tudo
        sql_no_comments = self._strip_sql_comments(sql)
        sql_clean = sql_no_comments.strip()
        sql_up = sql_clean.upper()

        # 2️⃣ Validação inicial
        if not sql_up.startswith(("DECLARE", "SET", "WITH", "SELECT")):
            raise PermissionError(
                "Somente instruções DECLARE, SET, SELECT ou WITH são permitidas."
            )

        # 3️⃣ Bloqueio de keywords proibidas
        for kw in self.BANNED_KEYWORDS:
            if re.search(rf"\b{kw}\b", sql_up):
                raise PermissionError(f"Comando proibido detectado: {kw}")

        # 4️⃣ Divide instruções
        statements = [s.strip() for s in sql_clean.split(";") if s.strip()]
        select_count = 0

        for stmt in statements:
            stmt_up = stmt.upper()

            # DECLARE
            if stmt_up.startswith("DECLARE"):
                if re.match(
                    r"^DECLARE\s+@[A-Z0-9_]+\s+[A-Z0-9()_,\s]+(\s*=\s*[^;]+)?$",
                    stmt_up,
                ):
                    continue

                if re.match(
                    r"^DECLARE\s+@[A-Z0-9_]+\s+TABLE\s*\([\s\S]*?\)$",
                    stmt_up,
                ):
                    if re.search(r"\b(SELECT|PRIMARY|FOREIGN|CONSTRAINT|INDEX)\b", stmt_up):
                        raise PermissionError(
                            "DECLARE TABLE contém definição não permitida."
                        )
                    continue

                raise PermissionError("DECLARE inválido ou não suportado.")

            # SET
            if stmt_up.startswith("SET"):
                if not re.match(
                    r"^SET\s+@[A-Z0-9_]+\s*=\s*(NULL|'[^']*'|\d+|@[A-Z0-9_]+)$",
                    stmt_up,
                ):
                    raise PermissionError("SET inválido ou não suportado.")
                continue

            # SELECT / WITH
            if stmt_up.startswith("WITH") or stmt_up.startswith("SELECT"):
                select_count += 1
                continue

            raise PermissionError(
                "Somente instruções DECLARE, SET, SELECT ou WITH são permitidas."
            )

        # 5️⃣ Regras finais de SELECT
        if select_count < 1:
            raise PermissionError("É obrigatório existir pelo menos um SELECT no SQL.")

        if select_count > self.MAX_SELECTS:
            raise PermissionError(
                f"Limite máximo de SELECTs excedido ({self.MAX_SELECTS})."
            )

        # 6️⃣ Validação de tabelas físicas (whitelist)
        cte_names = self._extract_cte_names(sql_up)

        tables = re.findall(r"\bFROM\s+([A-Z0-9_]+)", sql_up)
        tables += re.findall(r"\bJOIN\s+([A-Z0-9_]+)", sql_up)

        for t in tables:
            name = t.upper()

            if name in cte_names:
                continue

            if name.startswith("@"):
                continue

            if name not in self.allowed_tables:
                raise PermissionError(
                    f"Tabela '{t}' não autorizada (fora da whitelist)."
                )

        return True
