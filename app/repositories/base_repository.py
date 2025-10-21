# app/repositories/base_repository.py
from app.database import get_connection
from app.utils.logger import log_info, log_error
from app.core.exceptions import DatabaseConnectionError
from datetime import datetime, date

class BaseRepository:
    """
    Classe base para acesso ao banco de dados SQL Server (Protheus).
    Fornece métodos utilitários para executar consultas e processar resultados.
    """

    def __init__(self):
        self.connection = None
        self.cursor = None

    # ---------------------------
    # 🔹 Conexão e controle
    # ---------------------------
    def connect(self):
        try:
            self.connection = get_connection()
            self.cursor = self.connection.cursor()
        except Exception as e:
            log_error(f"Erro ao conectar ao banco: {e}")
            raise DatabaseConnectionError(str(e))

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    # ---------------------------
    # 🔹 Execução de queries
    # ---------------------------
    def execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        """
        Executa uma query SQL e retorna uma lista de dicionários {coluna: valor}.
        """
        try:
            self.connect()
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            result = [self._normalize_row(dict(zip(columns, row))) for row in rows]
            return result

        except Exception as e:
            log_error(f"Erro ao executar query: {e}")
            raise DatabaseConnectionError(str(e))
        finally:
            self.close()

    def execute_one(self, query: str, params: tuple = ()) -> dict | None:
        """
        Executa uma query SQL e retorna o primeiro registro (dict).
        """
        try:
            self.connect()
            self.cursor.execute(query, params)
            row = self.cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in self.cursor.description]
            return self._normalize_row(dict(zip(columns, row)))
        except Exception as e:
            log_error(f"Erro ao executar query única: {e}")
            raise DatabaseConnectionError(str(e))
        finally:
            self.close()

    # ---------------------------
    # 🔹 Normalização de dados
    # ---------------------------
    def _normalize_row(self, row: dict) -> dict:
        """
        Limpa e normaliza dados retornados do banco.
        - Remove espaços extras
        - Converte datetime/date para ISO
        - Substitui None por string vazia
        """
        for k, v in row.items():
            if isinstance(v, (datetime, date)):
                row[k] = v.isoformat()
            elif isinstance(v, str):
                row[k] = v.strip()
            elif v is None:
                row[k] = ""
        return row
