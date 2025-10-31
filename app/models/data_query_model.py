# app/models/data_query_model.py



from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union


# ======================================================
# 🔹 MODELOS BÁSICOS
# ======================================================
class JoinModel(BaseModel):
    type: Optional[str] = Field("INNER", description="Tipo de JOIN (INNER, LEFT, RIGHT, FULL)")
    table: Optional[str] = Field(None, description="Tabela a ser associada")
    left: str = Field(..., description="Campo da tabela principal")
    right: str = Field(..., description="Campo da tabela associada")


class FilterCondition(BaseModel):
    op: str = Field("=", description="Operador (=, >, <, LIKE, IN, BETWEEN, IS NULL, IS NOT NULL)")
    value: Optional[Union[str, int, float, List[Any]]] = Field(
        None, description="Valor ou lista de valores (não obrigatório para IS NULL / IS NOT NULL)"
    )


# ======================================================
# 🔹 MODELO INTERNO RECURSIVO (para execução real)
# ======================================================
class FilterGroupInternal(BaseModel):
    and_: Optional[List[Union["FilterGroupInternal", Dict[str, FilterCondition]]]] = Field(None, alias="and")
    or_: Optional[List[Union["FilterGroupInternal", Dict[str, FilterCondition]]]] = Field(None, alias="or")

FilterGroupInternal.model_rebuild()


# ======================================================
# 🔹 MODELO SIMPLIFICADO (para OpenAPI / GPT)
# ======================================================
class FilterGroup(BaseModel):
    and_: Optional[List[Any]] = Field(None, alias="and", description="Lista de filtros combinados com AND")
    or_: Optional[List[Any]] = Field(None, alias="or", description="Lista de filtros combinados com OR")


# ======================================================
# 🔹 MODELO PRINCIPAL
# ======================================================
class OrderByModel(BaseModel):
    field: str = Field(..., description="Campo para ordenação")
    direction: Optional[str] = Field("ASC", description="Direção (ASC ou DESC)")


class DataQueryRequest(BaseModel):
    tables: List[str] = Field(..., example=["SB2010"], description="Tabelas da consulta")
    columns: List[str] = Field(["*"], example=["SB2010.B2_CC"], description="Colunas base")
    joins: Optional[List[JoinModel]] = Field(None, description="Definição de JOINs entre tabelas")

    filters: Optional[Union[Dict[str, Any], FilterGroup, List[Any]]] = Field(
        None, description="Filtros aplicados (suporte a 'and'/'or' encadeados)"
    )

    group_by: Optional[List[str]] = Field(None, description="Campos para agrupamento (GROUP BY)")
    aggregates: Optional[Dict[str, str]] = Field(None, description="Funções de agregação (ex: {'B2_QATU': 'SUM'})")
    having: Optional[Dict[str, FilterCondition]] = Field(None, description="Filtros sobre agregações (HAVING)")
    rollup: Optional[bool] = Field(False, description="Ativa ROLLUP (subtotais hierárquicos)")
    cube: Optional[bool] = Field(False, description="Ativa CUBE (todas as combinações de agrupamento)")
    auto_aggregate: Optional[bool] = Field(False, description="Agrega automaticamente colunas numéricas (SUM)")
    order_by: Optional[List[OrderByModel]] = Field(None, description="Ordenação dos resultados")

    # 🔹 Agora realmente opcionais
    page: Optional[int] = Field(None, ge=1, description="Página atual (opcional)")
    page_size: Optional[int] = Field(None, ge=1, le=10000, description="Tamanho da página (opcional)")

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
