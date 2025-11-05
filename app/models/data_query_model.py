# app/models/data_query_model.py

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union


# ======================================================
# 🔹 MODELOS BÁSICOS
# ======================================================
class JoinModel(BaseModel):
    type: Optional[str] = Field(
        "INNER",
        description="Tipo de JOIN (INNER, LEFT, RIGHT, FULL)"
    )
    table: Optional[str] = Field(
        None,
        description="Tabela a ser associada (suporta alias: 'SB2010 AS E' ou 'SB2010 E')"
    )
    left: str = Field(
        ...,
        description="Campo da tabela principal (pode usar alias, ex.: 'P.B1_COD')"
    )
    right: str = Field(
        ...,
        description="Campo da tabela associada (pode usar alias, ex.: 'E.B2_COD')"
    )


class FilterCondition(BaseModel):
    op: str = Field(
        "=",
        description="Operador (=, >, <, >=, <=, <>, LIKE, NOT LIKE, IN, NOT IN, BETWEEN, IS NULL, IS NOT NULL)"
    )
    value: Optional[Union[str, int, float, List[Any]]] = Field(
        None,
        description="Valor ou lista de valores (não obrigatório para IS NULL / IS NOT NULL)"
    )


# ======================================================
# 🔹 MODELO INTERNO RECURSIVO (para execução real)
#   - Mantém compatibilidade com 'and'/'or' via alias de campo
# ======================================================
class FilterGroupInternal(BaseModel):
    and_: Optional[List[Union["FilterGroupInternal", Dict[str, FilterCondition]]]] = Field(
        None, alias="and", description="Lista de filtros combinados com AND"
    )
    or_: Optional[List[Union["FilterGroupInternal", Dict[str, FilterCondition]]]] = Field(
        None, alias="or", description="Lista de filtros combinados com OR"
    )

# Necessário para referências recursivas
FilterGroupInternal.model_rebuild()


# ======================================================
# 🔹 MODELO SIMPLIFICADO (para OpenAPI / GPT)
#   - Usado quando se deseja maior flexibilidade na composição
# ======================================================
class FilterGroup(BaseModel):
    and_: Optional[List[Any]] = Field(
        None, alias="and", description="Lista de filtros combinados com AND"
    )
    or_: Optional[List[Any]] = Field(
        None, alias="or", description="Lista de filtros combinados com OR"
    )


# ======================================================
# 🔹 ORDENAÇÃO
# ======================================================
class OrderByModel(BaseModel):
    field: str = Field(
        ..., description="Campo para ordenação (suporta alias, ex.: 'P.B1_DESC')"
    )
    direction: Optional[str] = Field(
        "ASC", description="Direção (ASC ou DESC)"
    )


# ======================================================
# 🔹 MODELO PRINCIPAL DA SOLICITAÇÃO
# ======================================================
class DataQueryRequest(BaseModel):
    # Tabelas podem trazer alias embutido: "SB1010 AS P" ou "SB1010 P"
    tables: List[str] = Field(
        ...,
        example=["SB1010 AS P"],
        description="Tabelas da consulta (com ou sem alias: 'SB1010', 'SB1010 AS P', 'SB1010 P')"
    )

    # Colunas podem referenciar alias: "P.B1_COD"
    columns: List[str] = Field(
        ["*"],
        example=["P.B1_COD", "P.B1_DESC"],
        description="Colunas base (suporta alias e funções SQL permitidas)"
    )

    joins: Optional[List[JoinModel]] = Field(
        None,
        description="Definição de JOINs entre tabelas (tabela com alias, left/right com alias)"
    )

    # Filtros aceitam tanto dict simples quanto grupos (and/or) recursivos
    filters: Optional[Union[Dict[str, Any], FilterGroup, List[Any]]] = Field(
        None,
        description="Filtros aplicados (suporte a 'and'/'or' encadeados; chaves podem usar alias)"
    )

    group_by: Optional[List[str]] = Field(
        None, description="Campos para agrupamento (suporta alias)"
    )
    aggregates: Optional[Dict[str, str]] = Field(
        None, description="Funções de agregação (ex.: {'P.B1_PESO': 'SUM'})"
    )
    having: Optional[Dict[str, FilterCondition]] = Field(
        None, description="Filtros sobre agregações (HAVING)"
    )
    rollup: Optional[bool] = Field(
        False, description="Ativa ROLLUP (subtotais hierárquicos)"
    )
    cube: Optional[bool] = Field(
        False, description="Ativa CUBE (todas as combinações de agrupamento)"
    )
    auto_aggregate: Optional[bool] = Field(
        False, description="Agrega automaticamente colunas numéricas (SUM)"
    )

    order_by: Optional[List[OrderByModel]] = Field(
        None, description="Ordenação dos resultados"
    )

    # Mapa extra de aliases (opcional). Se informado, a camada de repositório
    # pode transformá-los em 'AS' automaticamente ao montar o FROM/JOIN.
    aliases: Optional[Dict[str, str]] = Field(
        None,
        description="Mapeia tabelas para aliases. Ex.: {'SB1010': 'P', 'SB2010': 'E'}"
    )

    # Paginação
    page: Optional[int] = Field(
        None, ge=1, description="Página atual (opcional)"
    )
    page_size: Optional[int] = Field(
        None, ge=1, le=10000, description="Tamanho da página (opcional)"
    )

    # ==================================================
    # 🔹 Exemplos para documentação (OpenAPI/Swagger)
    # ==================================================
    # model_config = {
    #     "json_schema_extra": {
    #         "examples": [
    #             # Exemplo 1 — Consulta simples com alias e filtro composto
    #             {
    #                 "summary": "Produtos com alias e filtro AND/OR",
    #                 "value": {
    #                     "tables": ["SB1010 AS P"],
    #                     "columns": ["P.B1_COD", "P.B1_DESC"],
    #                     "filters": {
    #                         "and": [
    #                             {"P.B1_GRUPO": {"op": "=", "value": "1008"}},
    #                             {"P.B1_TIPO": {"op": "=", "value": "MP"}},
    #                             {"P.D_E_L_E_T_": {"op": "=", "value": ""}},
    #                             {
    #                                 "or": [
    #                                     {"P.B1_DESC": {"op": "NOT LIKE", "value": "%TERM%"}},
    #                                     {"P.B1_DESC": {"op": "NOT LIKE", "value": "%FASTON%"}}
    #                                 ]
    #                             }
    #                         ]
    #                     },
    #                     "order_by": [{"field": "P.B1_DESC", "direction": "ASC"}]
    #                 }
    #             },
    #             # Exemplo 2 — JOIN com alias, filtros e paginação
    #             {
    #                 "summary": "Produtos + Estoque (JOIN) com alias",
    #                 "value": {
    #                     "tables": ["SB1010 AS P", "SB2010 AS E"],
    #                     "columns": ["P.B1_COD", "P.B1_DESC", "E.B2_FILIAL", "E.B2_LOCAL", "E.B2_QATU"],
    #                     "joins": [
    #                         {
    #                             "type": "LEFT",
    #                             "table": "SB2010 AS E",
    #                             "left": "P.B1_COD",
    #                             "right": "E.B2_COD"
    #                         }
    #                     ],
    #                     "filters": {
    #                         "and": [
    #                             {"P.D_E_L_E_T_": {"op": "=", "value": ""}},
    #                             {"E.D_E_L_E_T_": {"op": "=", "value": ""}},
    #                             {"E.B2_QATU": {"op": ">", "value": 0}}
    #                         ]
    #                     },
    #                     "order_by": [{"field": "P.B1_COD", "direction": "ASC"}],
    #                     "page": 1,
    #                     "page_size": 50
    #                 }
    #             },
    #             # Exemplo 3 — Group By, agregação e Having com alias
    #             {
    #                 "summary": "Agregação por produto com HAVING",
    #                 "value": {
    #                     "tables": ["SB2010 AS E"],
    #                     "columns": ["E.B2_COD"],
    #                     "aggregates": {"E.B2_QATU": "SUM"},
    #                     "group_by": ["E.B2_COD"],
    #                     "having": {
    #                         "SUM(E.B2_QATU)": {"op": ">", "value": 0}
    #                     },
    #                     "order_by": [{"field": "E.B2_COD", "direction": "ASC"}]
    #                 }
    #             }
    #         ]
    #     }
    # }

    model_config = {
        "json_schema_extra": {
            "example": {
                "tables": ["SB1010"],
                "columns": ["SB1010.B1_COD", "SB1010.B1_DESC"],
                "filters": {
                    "and": [
                        {"SB1010.B1_GRUPO": {"op": "=", "value": "1008"}},
                        {"SB1010.B1_TIPO": {"op": "=", "value": "MP"}},
                        {"SB1010.D_E_L_E_T_": {"op": "=", "value": ""}},
                        {
                            "or": [
                                {"SB1010.B1_DESC": {"op": "NOT LIKE", "value": "%TERM%"}},
                                {"SB1010.B1_DESC": {"op": "NOT LIKE", "value": "%FASTON%"}}
                            ]
                        }
                    ]
                },
                "order_by": [{"field": "SB1010.B1_DESC", "direction": "ASC"}]
            }
        }
    }

    

    # model_config = {
    #     "json_schema_extra": {
    #         "example": {
    #             "tables": ["SB1010", "SB2010"],
    #             "columns": ["SB1010.B1_COD", "SB1010.B1_DESC", "SB2010.B2_QATU"],
    #             "joins": [
    #                 {
    #                     "type": "LEFT",
    #                     "table": "SB2010",
    #                     "left": "SB1010.B1_COD",
    #                     "right": "SB2010.B2_COD"
    #                 }
    #             ],
    #             "filters": {
    #                 "SB1010.D_E_L_E_T_": {"op": "=", "value": ""},
    #                 "SB1010.B1_DESC": {"op": "LIKE", "value": "%CABO%"},
    #                 "SB1010.B1_GRUPO": {"op": "=", "value": "1008"},
    #                 "SB2010.D_E_L_E_T_": {"op": "=", "value": ""},
    #                 "SB2010.B2_QATU": {"op": ">", "value": 0},
    #                 "TRIM(CAST(SB2010.B2_QATU AS VARCHAR(50)))": { "op": "IS NOT NULL" }
    #             },
    #             "order_by": [
    #                 {"field": "SB1010.B1_COD", "direction": "ASC"}
    #             ],
    #             "page": 1,
    #             "page_size": 20
    #         }
    #     }
    # }
