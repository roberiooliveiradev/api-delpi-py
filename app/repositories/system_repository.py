# app/repositories/system_repository.py

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import BusinessLogicError
from app.utils.logger import log_info, log_error

class SystemRepository(BaseRepository):
    """
    Repositório responsável por consultas sobre o sistema, nomes de tabelas, colunas...
    """

    def get_all_tables(self, limit: int = 10, offset: int = 0) -> list[dict]:
        log_info(f"Consultando tabelas no Protheus... (limit={limit}, offset={offset})")
        query = f"""
            SELECT 
                t.name AS TableName,
                ep.value AS Description
            FROM sys.tables t
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = t.object_id
                AND ep.minor_id = 0
                AND ep.class = 1
                AND ep.name = 'MS_Description'
            ORDER BY t.name
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
        """
        tables = self.execute_query(query, (offset, limit))
        return tables

    
    def get_columns_table(self, tableName: str) -> dict:
        log_info(f"Buscando colunas da tabela {tableName}.")
        query = """
            SELECT
                c.name AS ColumnName,
                ep.value AS Description
            FROM sys.columns c
            INNER JOIN sys.tables t ON c.object_id = t.object_id
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = c.object_id
                AND ep.minor_id = c.column_id
                AND ep.class = 1
                AND ep.name = 'MS_Description'
            WHERE t.name = ?
            ORDER BY c.column_id;
        """
        table = self.execute_query(query, (tableName,))
        if not table:
            raise BusinessLogicError(f"Produto com código '{tableName}' não encontrado.")
        return table