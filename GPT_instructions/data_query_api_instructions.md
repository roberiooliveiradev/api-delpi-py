# 🧩 Guia de Uso da Rota `/data/query`

## 📘 Descrição

A rota `/data/query` é uma **API analítica dinâmica** que permite consultas SQL seguras e automatizadas sobre o banco de dados **Protheus (SB1010, SB2010, etc.)**, com suporte a filtros recursivos, agregacões, funções SQL e paginação.

## 🤖 Instrução de Execução Automática da API DELPI

-   Sempre que precisar consultar a rota `/data/query`, o agente deve:
    -   Montar automaticamente o corpo JSON de forma segura e completa;
    -   Enviar a requisição diretamente, **sem pedir confirmação do usuário**;
    -   Retornar apenas o resultado da API (ou o erro, se houver);
    -   Não exibir o SQL gerado ao usuário final.

---

## ⚙️ Método e Endpoint

| Método | Endpoint      | Autenticação         |
| ------ | ------------- | -------------------- |
| `POST` | `/data/query` | 🔐 Requer JWT válido |

---

## 🧱 Corpo da Requisição

Todos os campos são opcionais, exceto `tables` e `columns`.

| Campo            | Tipo          | Obrigatório | Descrição                                     |
| ---------------- | ------------- | ----------- | --------------------------------------------- |
| `tables`         | array[string] | ✔           | Lista de tabelas ou aliases (`"SB1010 AS P"`) |
| `columns`        | array[string] | ✔           | Colunas ou expressões SQL seguras             |
| `joins`          | array[object] | ❌          | JOINs opcionais (INNER, LEFT, RIGHT, FULL)    |
| `filters`        | object        | ❌          | Filtros com suporte **recursivo (and/or)**    |
| `group_by`       | array[string] | ❌          | Campos de agrupamento                         |
| `aggregates`     | object        | ❌          | Agregacões personalizadas                     |
| `having`         | object        | ❌          | Filtros sobre agregados                       |
| `rollup`         | bool          | ❌          | Subtotais hierárquicos                        |
| `cube`           | bool          | ❌          | Combinações de agrupamento                    |
| `order_by`       | array[object] | ❌          | Ordenação (padrão: `R_E_C_N_O_ ASC`)          |
| `page`           | int           | ❌          | Página atual (default: null)                  |
| `page_size`      | int           | ❌          | Tamanho da página (default: null)             |
| `auto_aggregate` | bool          | ❌          | Reservado para uso futuro                     |
| `aliases`        | object        | ❌          | Mapeamento de aliases de tabela               |

> 🔹 **Observação:** Se `page` e `page_size` não forem informados, a consulta será executada **sem paginação** e retornará todos os registros.

---

## 🔍 Operadores de Filtro

| Operador                  | Descrição            | Exemplo                                              |
| ------------------------- | -------------------- | ---------------------------------------------------- |
| `=`                       | Igual                | `"B1_TIPO": {"op": "=", "value": "PA"}`              |
| `<>`                      | Diferente            | `"B2_TIPO": {"op": "<>", "value": "MP"}`             |
| `>` / `<` / `>=` / `<=`   | Comparativo numérico | `"B2_QATU": {"op": ">", "value": 0}`                 |
| `LIKE` / `NOT LIKE`       | Busca textual        | `"B1_DESC": {"op": "LIKE", "value": "%CABO%"}`       |
| `IN` / `NOT IN`           | Lista de valores     | `"B1_GRUPO": {"op": "IN", "value": ["1008","1009"]}` |
| `BETWEEN`                 | Faixa de valores     | `"B2_QATU": {"op": "BETWEEN", "value": [10,50]}`     |
| `IS NULL` / `IS NOT NULL` | Nulidade             | `"B2_QATU": {"op": "IS NOT NULL"}`                   |

### 🧰 Filtros Recursivos (AND/OR)

```json
"filters": {
  "and": [
    { "B1_GRUPO": { "op": "=", "value": "1008" } },
    {
      "or": [
        { "B1_DESC": { "op": "LIKE", "value": "%CABO%" } },
        { "B1_DESC": { "op": "LIKE", "value": "%FIO%" } }
      ]
    }
  ]
}
```

---

## 🤍 Funções SQL Seguras

| Função                 | Tipo      | Exemplo                                 |
| ---------------------- | --------- | --------------------------------------- |
| `TRIM()`               | Texto     | `"TRIM(SB1010.B1_DESC)"`                |
| `UPPER()` / `LOWER()`  | Texto     | `"UPPER(SB1010.B1_DESC)"`               |
| `LEN()`                | Texto     | `"LEN(SB1010.B1_DESC)"`                 |
| `CAST()` / `CONVERT()` | Conversão | `"CAST(SB2010.B2_QATU AS VARCHAR(50))"` |
| `LTRIM()` / `RTRIM()`  | Texto     | `"LTRIM(SB2010.B2_LOCAL)"`              |

> ⚠️ **Atenção:** Funções não listadas acima serão **rejeitadas automaticamente** por segurança SQL.

---

## 📈 Exemplo Avançado

```json
{
    "tables": ["SB1010 AS P", "SB2010 AS E"],
    "columns": ["P.B1_COD", "P.B1_DESC", "E.B2_FILIAL", "E.B2_LOCAL"],
    "joins": [
        {
            "type": "LEFT",
            "table": "SB2010 AS E",
            "left": "P.B1_COD",
            "right": "E.B2_COD"
        }
    ],
    "filters": {
        "and": [
            { "UPPER(P.B1_DESC)": { "op": "LIKE", "value": "%CABO%" } },
            { "P.B1_GRUPO": { "op": "=", "value": "1008" } },
            { "P.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "E.D_E_L_E_T_": { "op": "=", "value": "" } }
        ]
    },
    "aggregates": { "E.B2_QATU": "SUM" },
    "group_by": ["E.B2_FILIAL", "E.B2_LOCAL"],
    "rollup": true,
    "order_by": [{ "field": "E.B2_FILIAL", "direction": "ASC" }],
    "page": 1,
    "page_size": 50
}
```

---

## ✅ Resposta de Sucesso

```json
{
    "success": true,
    "sql": "SELECT P.B1_COD, P.B1_DESC, E.B2_FILIAL, E.B2_LOCAL, SUM(E.B2_QATU) AS sum_B2_QATU ...",
    "page": 1,
    "page_size": 50,
    "total": 120,
    "pages": 3,
    "data": [
        {
            "B1_COD": "10080522",
            "B1_DESC": "CABO CONDUTOR 1,5MM² AZUL",
            "B2_FILIAL": "01",
            "B2_LOCAL": "EST01",
            "SUM_B2_QATU": 240
        }
    ]
}
```

> ⚠️ **Não mostrar ao usuário o SQL retornado pela API.**

---

## ❌ Resposta de Erro

```json
{
    "success": false,
    "message": "500: <descrição do erro>"
}
```

---

## 🔍 Boas Práticas

-   Sempre filtrar `D_E_L_E_T_ = ""` para excluir registros lógicos.
-   Usar `LEFT JOIN` para manter produtos sem movimento.
-   Evitar `TRIM()` em colunas numéricas — use `CAST()` antes.
-   `ORDER BY` padrão é `R_E_C_N_O_ ASC` quando não especificado.
-   `auto_aggregate` ainda não implementado (reservado).

---

# 📗 Exemplos de solicitações do usuário

## Usuário: "Quais produtos serão produzidos hoje?"

-   TABELAS USADAS:

    -   SC2 - Ordens de Produção;
    -   SH8 - Operações Alocadas;
    -   SD4 - Requisições Empenhadas;

```json
{
    "tables": ["SC2010 AS OP"],
    "columns": [
        "OP.C2_PRODUTO AS COD_PRODUTO",
        "P.B1_DESC AS DESCRICAO_PRODUTO",
        "OP.C2_QUANT AS QTD_PLANEJADA",
        "OP.C2_UM AS UNIDADE",
        "H8.H8_DTINI AS DATA_INICIO_OPERACAO"
    ],
    "joins": [
        {
            "type": "LEFT",
            "table": "SD4010 AS SD4",
            "left": "OP.C2_OP",
            "right": "SD4.D4_OP"
        },
        {
            "type": "LEFT",
            "table": "SH8010 AS H8",
            "conditions": [
                { "left": "SD4.D4_OP", "op": "=FIELD", "right": "H8.H8_OP" },
                {
                    "left": "SD4.D4_OPERAC",
                    "op": "=FIELD",
                    "right": "H8.H8_OPER"
                }
            ]
        },
        {
            "type": "LEFT",
            "table": "SB1010 AS P",
            "left": "OP.C2_PRODUTO",
            "right": "P.B1_COD"
        }
    ],
    "filters": {
        "and": [
            { "OP.C2_FILIAL": { "op": "=", "value": "01" } },
            { "SD4.D4_FILIAL": { "op": "=", "value": "01" } },
            { "H8.H8_FILIAL": { "op": "=", "value": "01" } },
            { "OP.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "SD4.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "H8.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "P.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "P.B1_TIPO": { "op": "=", "value": "PA" } },
            { "OP.C2_PRIOR": { "op": "=", "value": "500" } },
            { "H8.H8_DTINI": { "op": "=", "value": "20251127" } }
        ]
    },
    "group_by": [
        "OP.C2_PRODUTO",
        "P.B1_DESC",
        "OP.C2_QUANT",
        "OP.C2_UM",
        "H8.H8_DTINI"
    ],
    "order_by": [{ "field": "OP.C2_PRODUTO", "direction": "ASC" }],
    "page": 1,
    "page_size": 100
}
```

> Substitua no filtro de "H8.H8_DTINI": { "op": "=", "value": "20251126" } pela data atualizada.

## Usuário: "Quais ops já foram finalizada hoje?"

Tabelas envolvidas:

-   SC2010 — Ordens de Produção
-   SD4010 — Empenhos de componentes
-   SB1010 — Cadastro de produtos
-   SH8010 — Roteiro de operações

Condições aplicadas:

-   OP.C2_QUANT = OP.C2_QUJE → total necessário produzido
-   OA.H8_DTINI = 20251127 → operação de hoje
-   Filial = 01 → Pergunte a filial ao usuário
-   Todos os registros ativos (`D_E_L_E_T_ = ''`)
-   OP.C2_PRIOR = 500 → prioridade Livre (501 Bloqueado)

Consulta:

```json
{
    "tables": ["SC2010 AS OP"],
    "columns": [
        "OP.C2_OP AS COD_OP",
        "OP.C2_PRODUTO AS COD_PRODUTO",
        "P.B1_DESC AS DESCRICAO_PRODUTO",
        "OP.C2_QUANT AS QTD_OP",
        "OP.C2_QUJE AS QTD_PRODUZIDA",
        "OP.C2_UM AS UNIDADE",
        "OA.H8_HRINI AS HORA_INICIO",
        "OA.H8_HRFIM AS HORA_FIM",
        "OA.H8_DTINI AS DATA_INICIO",
        "OA.H8_DTFIM AS DATA_FIM",
        "OA.H8_CTRAB AS CT"
    ],
    "joins": [
        {
            "type": "INNER",
            "table": "SD4010 AS RE",
            "left": "OP.C2_OP",
            "right": "RE.D4_OP"
        },
        {
            "type": "INNER",
            "table": "SB1010 AS P",
            "left": "OP.C2_PRODUTO",
            "right": "P.B1_COD"
        },
        {
            "type": "INNER",
            "table": "SH8010 AS OA",
            "conditions": [
                { "left": "RE.D4_OP", "op": "=FIELD", "right": "OA.H8_OP" },
                {
                    "left": "RE.D4_OPERAC",
                    "op": "=FIELD",
                    "right": "OA.H8_OPER"
                }
            ]
        }
    ],
    "filters": {
        "and": [
            { "OP.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "RE.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "P.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OA.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OP.C2_QUANT": { "op": "=FIELD", "value": "OP.C2_QUJE" } },
            { "OP.C2_FILIAL": { "op": "=", "value": "01" } },
            { "RE.D4_FILIAL": { "op": "=", "value": "01" } },
            { "OA.H8_FILIAL": { "op": "=", "value": "01" } },
            { "OP.C2_PRIOR": { "op": "=", "value": "500" } },
            { "OA.H8_DTINI": { "op": "=", "value": "20251127" } }
        ]
    },
    "group_by": [
        "OP.C2_OP",
        "OP.C2_PRODUTO",
        "P.B1_DESC",
        "OP.C2_QUANT",
        "OP.C2_QUJE",
        "OP.C2_UM",
        "OA.H8_HRINI",
        "OA.H8_HRFIM",
        "OA.H8_DTINI",
        "OA.H8_DTFIM",
        "OA.H8_CTRAB"
    ],
    "order_by": [
        { "field": "OA.H8_HRINI", "direction": "ASC" },
        { "field": "OP.C2_OP", "direction": "ASC" }
    ],
    "page": 1,
    "page_size": 500
}
```

## Usuário: "Quais ops programadas para hoje estão em aberto?"

Tabelas envolvidas:

-   SC2010 — Ordens de Produção
-   SD4010 — Empenhos de componentes
-   SB1010 — Cadastro de produtos
-   SH8010 — Roteiro de operações

Condições aplicadas:

-   OP.C2_QUANT > OP.C2_QUJE → falta produzir para finalizar
-   OA.H8_DTINI = 20251127 → operação de hoje
-   Filial = 01 → Pergunte a filial ao usuário
-   Todos os registros ativos (`D_E_L_E_T_ = ''`)
-   OP.C2_PRIOR = 500 → prioridade Livre (501 Bloqueado)

Consulta:

```json
{
    "tables": ["SC2010 AS OP"],
    "columns": [
        "OP.C2_OP AS COD_OP",
        "OP.C2_PRODUTO AS COD_PRODUTO",
        "P.B1_DESC AS DESCRICAO_PRODUTO",
        "OP.C2_QUANT AS QTD_OP",
        "OP.C2_QUJE AS QTD_PRODUZIDA",
        "(OP.C2_QUANT*1000-OP.C2_QUJE*1000)/1000 AS QTD_FALTANTE",
        "OP.C2_UM AS UNIDADE",
        "OA.H8_HRINI AS HORA_INICIO",
        "OA.H8_DTINI AS DATA_INICIO",
        "OA.H8_CTRAB AS CT"
    ],
    "joins": [
        {
            "type": "INNER",
            "table": "SD4010 AS RE",
            "left": "OP.C2_OP",
            "right": "RE.D4_OP"
        },
        {
            "type": "INNER",
            "table": "SB1010 AS P",
            "left": "OP.C2_PRODUTO",
            "right": "P.B1_COD"
        },
        {
            "type": "INNER",
            "table": "SH8010 AS OA",
            "conditions": [
                { "left": "RE.D4_OP", "op": "=FIELD", "right": "OA.H8_OP" },
                {
                    "left": "RE.D4_OPERAC",
                    "op": "=FIELD",
                    "right": "OA.H8_OPER"
                }
            ]
        }
    ],
    "filters": {
        "and": [
            { "OP.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "RE.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "P.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OA.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OP.C2_QUANT": { "op": ">FIELD", "value": "OP.C2_QUJE" } },
            { "OP.C2_FILIAL": { "op": "=", "value": "01" } },
            { "RE.D4_FILIAL": { "op": "=", "value": "01" } },
            { "OA.H8_FILIAL": { "op": "=", "value": "01" } },
            { "OP.C2_PRIOR": { "op": "=", "value": "500" } },
            { "OA.H8_DTINI": { "op": "=", "value": "20251127" } }
        ]
    },
    "group_by": [
        "OP.C2_OP",
        "OP.C2_PRODUTO",
        "P.B1_DESC",
        "OP.C2_QUANT",
        "OP.C2_QUJE",
        "OP.C2_UM",
        "OA.H8_HRINI",
        "OA.H8_DTINI",
        "OA.H8_CTRAB"
    ],
    "order_by": [
        { "field": "OA.H8_HRINI", "direction": "ASC" },
        { "field": "OP.C2_OP", "direction": "ASC" }
    ],
    "page": 1,
    "page_size": 500
}
```

## Usuário: "Liste as OPs distintas em aberto?"

```json
{
    "tables": ["SC2010 AS OP"],
    "columns": ["DISTINCT OP.C2_OP AS COD_OP"],
    "joins": [
        {
            "type": "INNER",
            "table": "SD4010 AS RE",
            "left": "OP.C2_OP",
            "right": "RE.D4_OP"
        },
        {
            "type": "INNER",
            "table": "SH8010 AS OA",
            "conditions": [
                { "left": "RE.D4_OP", "op": "=FIELD", "right": "OA.H8_OP" },
                {
                    "left": "RE.D4_OPERAC",
                    "op": "=FIELD",
                    "right": "OA.H8_OPER"
                }
            ]
        }
    ],
    "filters": {
        "and": [
            { "OP.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OA.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OP.C2_FILIAL": { "op": "=", "value": "01" } },
            { "RE.D4_FILIAL": { "op": "=", "value": "01" } },
            { "OA.H8_FILIAL": { "op": "=", "value": "01" } },
            { "OP.C2_PRIOR": { "op": "=", "value": "500" } },
            { "OP.C2_QUANT": { "op": ">FIELD", "value": "OP.C2_QUJE" } },
            { "OA.H8_DTINI": { "op": "=", "value": "20251127" } }
        ]
    },
    "group_by": ["OP.C2_OP"],
    "order_by": [{ "field": "OP.C2_OP", "direction": "ASC" }],
    "page": 1,
    "page_size": 500
}
```

## Objetivo: agrupar as ordens por centro de trabalho (CT) e contar finalizadas e não finalizadas.

-   Relação: SC2010 → SD4010 → SH8010

```json
{
    "tables": ["SC2010 AS OP"],
    "columns": [
        "OA.H8_CTRAB AS CT",
        "COUNT(DISTINCT CASE WHEN OP.C2_QUANT = OP.C2_QUJE THEN OP.C2_OP END) AS OPS_FINALIZADAS",
        "COUNT(DISTINCT CASE WHEN OP.C2_QUANT > OP.C2_QUJE THEN OP.C2_OP END) AS OPS_NAO_FINALIZADAS",
        "COUNT(DISTINCT OP.C2_OP) AS TOTAL_OPS"
    ],
    "joins": [
        {
            "type": "INNER",
            "table": "SD4010 AS RE",
            "left": "OP.C2_OP",
            "right": "RE.D4_OP"
        },
        {
            "type": "INNER",
            "table": "SH8010 AS OA",
            "conditions": [
                { "left": "RE.D4_OP", "op": "=FIELD", "right": "OA.H8_OP" },
                {
                    "left": "RE.D4_OPERAC",
                    "op": "=FIELD",
                    "right": "OA.H8_OPER"
                }
            ]
        }
    ],
    "filters": {
        "and": [
            { "OP.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "RE.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OA.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OP.C2_FILIAL": { "op": "=", "value": "01" } },
            { "RE.D4_FILIAL": { "op": "=", "value": "01" } },
            { "OA.H8_FILIAL": { "op": "=", "value": "01" } },
            { "OP.C2_PRIOR": { "op": "=", "value": "500" } },
            { "OA.H8_DTINI": { "op": "=", "value": "20251127" } }
        ]
    },
    "group_by": ["OA.H8_CTRAB"],
    "order_by": [{ "field": "OA.H8_CTRAB", "direction": "ASC" }],
    "page": 1,
    "page_size": 100
}
```

### Objetivo: identificar componentes sem empenho registrado (possível travamento de produção) para um CT especídfico.

-   Regra: D4_QUANT = 0

```json
{
    "tables": ["SD4010 AS RE"],
    "columns": [
        "RE.D4_OP AS COD_OP",
        "RE.D4_PRODUTO AS COD_PRODUTO",
        "P.B1_DESC AS DESCRICAO_PRODUTO",
        "RE.D4_OPERAC AS OPERACAO",
        "RE.D4_QUANT AS QTD_EMPENHO",
        "OA.H8_CTRAB AS CT"
    ],
    "joins": [
        {
            "type": "INNER",
            "table": "SB1010 AS P",
            "left": "RE.D4_PRODUTO",
            "right": "P.B1_COD"
        },
        {
            "type": "INNER",
            "table": "SH8010 AS OA",
            "conditions": [
                { "left": "RE.D4_OP", "op": "=FIELD", "right": "OA.H8_OP" },
                {
                    "left": "RE.D4_OPERAC",
                    "op": "=FIELD",
                    "right": "OA.H8_OPER"
                }
            ]
        }
    ],
    "filters": {
        "and": [
            { "RE.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "P.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OA.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "RE.D4_FILIAL": { "op": "=", "value": "01" } },
            { "OA.H8_FILIAL": { "op": "=", "value": "01" } },
            { "OP.C2_PRIOR": { "op": "=", "value": "500" } },
            { "OA.H8_DTINI": { "op": "=", "value": "20251127" } },
            { "OA.H8_CTRAB": { "op": "=", "value": "CT-19" } },
            { "RE.D4_QUANT": { "op": "=", "value": 0 } }
        ]
    },
    "order_by": [{ "field": "RE.D4_OP", "direction": "ASC" }],
    "page": 1,
    "page_size": 200
}
```

## Objetivo: identificar ordens finalizadas sem consumo de componentes.

Regras:

-   C2_QUANT = C2_QUJE → finalizada

-   D4_QUANT = 0 → sem empenho

```json
{
    "tables": ["SC2010 AS OP"],
    "columns": [
        "OP.C2_OP AS COD_OP",
        "OP.C2_PRODUTO AS COD_PRODUTO",
        "P.B1_DESC AS DESCRICAO_PRODUTO",
        "OP.C2_QUANT AS QTD_PLANEJADA",
        "OP.C2_QUJE AS QTD_PRODUZIDA",
        "RE.D4_COD AS COD_COMPONENTE",
        "RE.D4_OPERAC AS OPERACAO",
        "SUM(RE.D4_QUANT) AS QTD_EMPENHO",
        "OA.H8_CTRAB AS CT"
    ],
    "joins": [
        {
            "type": "INNER",
            "table": "SD4010 AS RE",
            "left": "OP.C2_OP",
            "right": "RE.D4_OP"
        },
        {
            "type": "INNER",
            "table": "SB1010 AS P",
            "left": "OP.C2_PRODUTO",
            "right": "P.B1_COD"
        },
        {
            "type": "INNER",
            "table": "SH8010 AS OA",
            "conditions": [
                { "left": "RE.D4_OP", "op": "=FIELD", "right": "OA.H8_OP" },
                {
                    "left": "RE.D4_OPERAC",
                    "op": "=FIELD",
                    "right": "OA.H8_OPER"
                }
            ]
        }
    ],
    "filters": {
        "and": [
            { "OP.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "RE.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "P.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OA.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OP.C2_FILIAL": { "op": "=", "value": "01" } },
            { "RE.D4_FILIAL": { "op": "=", "value": "01" } },
            { "OA.H8_FILIAL": { "op": "=", "value": "01" } },
            { "OP.C2_PRIOR": { "op": "=", "value": "500" } },
            { "OA.H8_DTINI": { "op": "=", "value": "20251127" } },
            { "OA.H8_CTRAB": { "op": "=", "value": "CT-19" } },
            { "OP.C2_QUANT": { "op": "=FIELD", "value": "OP.C2_QUJE" } }
        ]
    },
    "having": {
        "SUM(RE.D4_QUANT)": { "op": "=", "value": 0 }
    },
    "group_by": [
        "OP.C2_OP",
        "OP.C2_PRODUTO",
        "P.B1_DESC",
        "OP.C2_QUANT",
        "OP.C2_QUJE",
        "RE.D4_COD",
        "RE.D4_OPERAC",
        "OA.H8_CTRAB"
    ],
    "order_by": [{ "field": "OP.C2_OP", "direction": "ASC" }],
    "page": 1,
    "page_size": 200
}
```

## Objetivo: Calcula a média de tempo (em horas) entre o início (H8_HRINI) e o fim (H8_HRFIM) das operações realizadas hoje (2025-11-27).

-   Considera apenas ordens finalizadas (C2_QUANT = C2_QUJE).

-   Agrupa por Centro de Trabalho (H8_CTRAB).

-   Filtra apenas registros ativos da filial 01 e prioridade livre (500).

```json
{
    "tables": ["SC2010 AS OP"],
    "columns": [
        "OA.H8_CTRAB AS CT",
        "CAST(AVG(((CAST(LEFT(REPLACE(OA.H8_HRFIM,':',''),2) AS INT)*60 + CAST(RIGHT(REPLACE(OA.H8_HRFIM,':',''),2) AS INT)) - (CAST(LEFT(REPLACE(OA.H8_HRINI,':',''),2) AS INT)*60 + CAST(RIGHT(REPLACE(OA.H8_HRINI,':',''),2) AS INT)))/60.0) AS FLOAT) AS TEMPO_MEDIO_HORAS"
    ],
    "joins": [
        {
            "type": "INNER",
            "table": "SD4010 AS RE",
            "left": "OP.C2_OP",
            "right": "RE.D4_OP"
        },
        {
            "type": "INNER",
            "table": "SH8010 AS OA",
            "conditions": [
                { "left": "RE.D4_OP", "op": "=FIELD", "right": "OA.H8_OP" },
                {
                    "left": "RE.D4_OPERAC",
                    "op": "=FIELD",
                    "right": "OA.H8_OPER"
                }
            ]
        }
    ],
    "filters": {
        "and": [
            { "OP.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "RE.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OA.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "OP.C2_FILIAL": { "op": "=", "value": "01" } },
            { "RE.D4_FILIAL": { "op": "=", "value": "01" } },
            { "OA.H8_FILIAL": { "op": "=", "value": "01" } },
            { "OP.C2_PRIOR": { "op": "=", "value": "500" } },
            { "OA.H8_DTINI": { "op": "=", "value": "20251127" } },
            { "OA.H8_DTFIM": { "op": "=", "value": "20251127" } },
            { "OA.H8_HRFIM": { "op": "IS NOT NULL" } },
            { "OP.C2_QUANT": { "op": "=FIELD", "value": "OP.C2_QUJE" } }
        ]
    },
    "group_by": ["OA.H8_CTRAB"],
    "order_by": [{ "field": "OA.H8_CTRAB", "direction": "ASC" }],
    "page": 1,
    "page_size": 100
}
```

## Usuário: "Monte uma consulta que mostre o total de estoque (`B2_QATU`) por filial e local apenas para produtos do grupo 1008 com 'CABO' na descrição, agrupando com subtotais."

```json
{
    "with": {
        "estoque_total": {
            "tables": ["SB2010 AS E"],
            "columns": [
                "E.B2_FILIAL",
                "E.B2_LOCAL",
                "E.B2_COD",
                "SUM(E.B2_QATU) AS QT"
            ],
            "filters": {
                "and": [{ "E.D_E_L_E_T_": { "op": "=", "value": "" } }]
            },
            "group_by": ["E.B2_FILIAL", "E.B2_LOCAL", "E.B2_COD"]
        }
    },
    "tables": ["SB1010 AS P", "estoque_total AS T"],
    "columns": ["T.B2_FILIAL", "T.B2_LOCAL", "P.B1_COD", "P.B1_DESC", "T.QT"],
    "filters": {
        "and": [
            { "P.B1_COD": { "op": "=field", "value": "T.B2_COD" } },
            { "P.D_E_L_E_T_": { "op": "=", "value": "" } },
            { "P.B1_DESC": { "op": "like", "value": "%CABO%" } }
        ]
    },
    "order_by": [{ "field": "P.B1_COD", "direction": "ASC" }],
    "page": 1,
    "page_size": 5
}
```

---

## 🟦 Exemplo 1 — Consulta simples com paginação

```json
{
    "tables": ["SB1010 AS P"],
    "columns": ["P.B1_COD", "P.B1_DESC"],
    "filters": {
        "and": [{ "P.D_E_L_E_T_": { "op": "=", "value": "" } }]
    },
    "order_by": [{ "field": "P.B1_COD", "direction": "ASC" }],
    "page": 1,
    "page_size": 50
}
```

---

## 🟩 Exemplo 2 — Join usando comparação campo–campo

```json
{
    "tables": ["SB1010 AS P", "SB2010 AS E"],
    "columns": ["P.B1_COD", "P.B1_DESC", "E.B2_QATU"],
    "filters": {
        "and": [{ "P.B1_COD": { "op": "=field", "value": "E.B2_COD" } }]
    },
    "order_by": [{ "field": "P.B1_COD", "direction": "ASC" }],
    "page": 1,
    "page_size": 30
}
```

---

## 🟧 Exemplo 3 — CTE + comparação campo–campo

```json
{
    "with": {
        "estoque_total": {
            "tables": ["SB2010 AS E"],
            "columns": ["E.B2_COD", "SUM(E.B2_QATU) AS QT"],
            "filters": {
                "and": [{ "E.D_E_L_E_T_": { "op": "=", "value": "" } }]
            },
            "group_by": ["E.B2_COD"]
        },
        "estoque_pos": {
            "tables": ["estoque_total AS T"],
            "columns": ["T.B2_COD", "T.QT"],
            "filters": { "and": [{ "T.QT": { "op": ">", "value": "0" } }] }
        }
    },
    "tables": ["estoque_pos AS EP", "SB1010 AS P"],
    "columns": ["P.B1_COD", "P.B1_DESC", "EP.QT"],
    "filters": {
        "and": [{ "P.B1_COD": { "op": "=field", "value": "EP.B2_COD" } }]
    },
    "order_by": [{ "field": "EP.QT", "direction": "DESC" }],
    "page": 1,
    "page_size": 50
}
```

---

## 🟥 Exemplo 4 — HAVING com função agregada (SQL Server way)

```json
{
    "tables": ["SD2010 AS D"],
    "columns": ["D.D2_COD"],
    "group_by": ["D.D2_COD"],
    "aggregates": {
        "D.D2_QUANT": "SUM"
    },
    "having": {
        "SUM(D.D2_QUANT)": { "op": ">", "value": "50000" }
    },
    "order_by": [{ "field": "SUM(D.D2_QUANT)", "direction": "DESC" }],
    "page": 1,
    "page_size": 5
}
```

---

## 🟨 Exemplo 5 — JOIN com múltiplas condições + tuple compare

```json
{
    "tables": ["TabelaA AS A"],
    "columns": ["A.C1", "A.C2", "B.C2"],
    "joins": [
        {
            "type": "LEFT",
            "table": "TabelaB AS B",
            "conditions": [
                { "left": "A.C1", "op": "=field", "right": "B.C1" },
                { "left": "A.C1,A.C2", "op": "=tuple", "right": "B.C1,B.C2" }
            ]
        }
    ],
    "order_by": [{ "field": "A.C1", "direction": "ASC" }],
    "page": 1,
    "page_size": 50
}
```

---

## 🟪 Exemplo 6 — Expressões SQL no WHERE

```json
{
    "tables": ["SF2010 AS M"],
    "columns": ["M.F2_COD", "M.DATA"],
    "filters": {
        "and": [
            {
                "M.DATA": {
                    "op": ">=",
                    "value": { "sql": "DATEADD(day,-30,GETDATE())" }
                }
            }
        ]
    },
    "order_by": [{ "field": "M.DATA", "direction": "DESC" }],
    "page": 1,
    "page_size": 100
}
```

---

## 🟫 Exemplo 7 — CTE final com agregação automática

```json
{
    "with": {
        "movimentos": {
            "tables": ["SF2010 AS M"],
            "columns": ["M.F2_COD", "M.F2_QUANT"],
            "group_by": ["M.F2_COD"],
            "auto_aggregate": true
        }
    },
    "tables": ["movimentos AS X"],
    "columns": ["X.F2_COD", "X.sum_F2_QUANT"],
    "order_by": [{ "field": "X.sum_F2_QUANT", "direction": "DESC" }],
    "page": 1,
    "page_size": 20
}
```

---

# 🧱 Regras importantes

## ✔ 1. **CTEs não paginam**

A paginação funciona **somente no SELECT final**.

## ✔ 2. **SQL Server não aceita alias no HAVING**

Deve-se usar sempre:

```
HAVING SUM(T.CAMPO) > 100
```

Portanto no JSON:

```json
"having": {
  "SUM(D.D2_QUANT)": { "op": ">", "value": "100" }
}
```

## ✔ 3. **Paginações só ocorrem se existir ORDER BY**

Sem ORDER BY → sem OFFSET/FETCH.

## ✔ 4. **Comparações campo–campo**

Exemplo:

```json
{ "A.COD": { "op": "=field", "value": "B.COD" } }
```

## ✔ 5. **SQL Expressions**

```json
"value": { "sql": "DATEADD(day,-30,GETDATE())" }
```

## ✔ 6. **Tuple compare**

```json
"A.C1,A.C2": { "op": "=tuple", "value": "B.C1,B.C2" }
```

---

# 📝 Notas finais

-   Sempre use **funções agregadas completas no HAVING**
-   Sempre envie **order_by** se quiser paginação
-   CTEs nunca paginam
-   CTEs podem referenciar CTEs anteriores
-   Toda comparação campo–campo deve usar `"op": "=field"`
-   Expressões SQL são permitidas apenas como `{ "sql": "..." }`

---
