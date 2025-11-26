# app/repositories/system_repository.py

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import BusinessLogicError
from app.utils.logger import log_info, log_error
from difflib import SequenceMatcher
import re

class SystemRepository(BaseRepository):
    """
    Repositório responsável por consultas sobre o sistema, nomes de tabelas, colunas...
    """

    def get_all_tables(self, limit: int = 10, offset: int = 0) -> list[dict]:
        log_info(f"Consultando tabelas no Protheus... (limit={limit}, offset={offset})")
        query = f"""
            SELECT 
                t.name AS TableName,
                X2.*
            FROM sys.tables t
            LEFT JOIN SX2010 X2
                ON X2.X2_ARQUIVO = t.name
                AND X2.D_E_L_E_T_ = ''
            ORDER BY t.name
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
        """
        tables = self.execute_query(query, (offset, limit))
        return tables

    def get_table(self, tableName: str) ->dict:
        log_info(f"Buscando informações da tabela {tableName}.")
        query = """
            SELECT 
                t.name AS TableName,
                X2.*
            FROM sys.tables t
            LEFT JOIN SX2010 X2
                ON X2.X2_ARQUIVO = t.name
            WHERE
                t.name = ?
                AND X2.D_E_L_E_T_ = ''
        """
        table = self.execute_query(query, (tableName,))
        if not table:
            raise BusinessLogicError(f"Tabela com código '{tableName}' não encontrada.")
        return table

    def get_columns_table(self, tableName: str) -> dict:
        log_info(f"Buscando colunas da tabela {tableName}.")
        query = """
            SELECT TOP 10
                X3.*
            FROM
                SX3010 AS X3
            INNER JOIN
                SX2010 AS X2
                ON X3.X3_ARQUIVO = X2.X2_CHAVE
            WHERE
                X2.X2_ARQUIVO = ?
                AND X3.D_E_L_E_T_ = ''
                AND X2.D_E_L_E_T_ = ''
            ORDER BY
                X3.X3_ORDEM;
        """

        columns = self.execute_query(query, (tableName,))
        if not columns:
            raise BusinessLogicError(f"Colunas da tabela com código '{tableName}' não encontrada.")
        return columns

    def search_table_for_description(self, description: str, page: int = 1, page_size: int = 20) -> dict:
        """
        Busca tabelas do Protheus (SX2010) com fallback inteligente:
        - 1ª etapa: busca por LIKE (rápida)
        - 2ª etapa: fallback com busca total se poucos resultados encontrados
        - Ranking Python para relevância
        """
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 200:
            page_size = 20

        offset = (page - 1) * page_size
        terms = [t.strip().upper() for t in re.split(r'\s+', description) if t.strip()]
        if not terms:
            raise BusinessLogicError("Descrição inválida — forneça ao menos uma palavra para busca.")

        like_clauses = []
        params = []
        for term in terms:
            like_clauses.append("UPPER(X2.X2_NOME) LIKE UPPER(?)")
            params.append(f"%{term}%")
        where_clause = " OR ".join(like_clauses)

        # 1️⃣ Primeira tentativa (busca por LIKE)
        query = f"""
            SELECT 
                X2.X2_ARQUIVO,
                X2.X2_NOME,
                X2.X2_CHAVE
            FROM SX2010 AS X2
            WHERE
                ({where_clause})
                AND X2.D_E_L_E_T_ = ''
            ORDER BY X2.X2_NOME;
        """
        results = self.execute_query(query, tuple(params))

        # 2️⃣ Se não achar ou achar poucos, faz fallback global
        if not results or len(results) < 10:
            log_info(f"Poucos resultados ({len(results)}). Ativando fallback total de SX2010.")
            query_fallback = """
                SELECT X2.X2_ARQUIVO, X2.X2_NOME, X2.X2_CHAVE
                FROM SX2010 AS X2
                WHERE X2.D_E_L_E_T_ = ''
                ORDER BY X2.X2_NOME;
            """
            results = self.execute_query(query_fallback, ())

        # 🔍 Agora aplica o ranking Python completo
        desc_upper = description.upper()
        desc_terms = desc_upper.split()

        for row in results:
            nome = row.get("X2_NOME", "")
            nome_upper = nome.upper()

            seq_ratio = SequenceMatcher(None, desc_upper, nome_upper).ratio()
            matched_terms = [t for t in desc_terms if t in nome_upper]
            coverage = len(matched_terms) / len(desc_terms)
            order_score = 0
            last_pos = -1
            for term in desc_terms:
                pos = nome_upper.find(term)
                if pos >= 0 and pos > last_pos:
                    order_score += 1
                    last_pos = pos
            order_ratio = order_score / len(desc_terms)
            len_ratio = min(len(desc_upper), len(nome_upper)) / max(len(desc_upper), len(nome_upper))

            total_score = (
                seq_ratio * 60 +
                coverage * 25 +
                order_ratio * 10 +
                len_ratio * 5
            ) * 100

            row["similarity_ratio"] = round(seq_ratio, 3)
            row["coverage_ratio"] = round(coverage, 3)
            row["order_ratio"] = round(order_ratio, 3)
            row["length_ratio"] = round(len_ratio, 3)
            row["total_score"] = round(total_score, 2)

        results.sort(key=lambda x: x["total_score"], reverse=True)

        total = len(results)
        start = offset
        end = offset + page_size
        paginated_results = results[start:end]

        return {
            "success": True,
            "page": page,
            "page_size": page_size,
            "total_records": total,
            "total_pages": (total // page_size) + (1 if total % page_size else 0),
            "data": paginated_results
        }
