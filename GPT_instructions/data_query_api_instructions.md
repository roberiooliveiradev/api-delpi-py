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

## 🔎 Exemplo de Prompt GPT

> “Monte uma consulta que mostre o total de estoque (`B2_QATU`) por filial e local apenas para produtos do grupo 1008 com 'CABO' na descrição, agrupando com subtotais.”

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

```json
{
    "success": true,
    "message": "Consulta executada automaticamente.",
    "data": {
        "success": true,
        "sql": "WITH estoque_total AS (SELECT E.B2_COD, SUM(E.B2_QATU) AS QT FROM SB2010 AS E WHERE (E.D_E_L_E_T_ = '') GROUP BY E.B2_COD) SELECT P.B1_COD, P.B1_DESC, T.QT FROM SB1010 AS P, estoque_total AS T WHERE (P.B1_COD = T.B2_COD AND P.D_E_L_E_T_ = '') ORDER BY P.B1_COD ASC OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY",
        "data": [
            {
                "B1_COD": "10010001",
                "B1_DESC": "CABO PVC 70°C 0,75MM2 PT 450/750V BWF ESTANHADO NM 247-3",
                "QT": 0
            },
            {
                "B1_COD": "10010002",
                "B1_DESC": "CABO PVC 70°C 1,00MM2 PT 450/750V BWF ESTANHADO NM 247-3",
                "QT": 0
            },
            {
                "B1_COD": "10010003",
                "B1_DESC": "CABO PVC 70°C 2,50MM2 PT 450/750V BWF ESTANHADO NM 247-3",
                "QT": 0
            },
            {
                "B1_COD": "10010004",
                "B1_DESC": "CABO PVC 70°C 35,00MM2 PT 450/750V BWF NM 247-3",
                "QT": 0
            },
            {
                "B1_COD": "10010005",
                "B1_DESC": "CABO PVC 70°C 2,50MM2 PT 450/750V BWF NM 247-3 - ROHS",
                "QT": 1040.845
            }
        ],
        "page": 1,
        "page_size": 5,
        "total": 5,
        "pages": 1
    }
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

# 🟦 Exemplo 1 — Consulta simples com paginação

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

# 🟩 Exemplo 2 — Join usando comparação campo–campo

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

# 🟧 Exemplo 3 — CTE + comparação campo–campo

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

# 🟥 Exemplo 4 — HAVING com função agregada (SQL Server way)

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

# 🟨 Exemplo 5 — JOIN com múltiplas condições + tuple compare

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

# 🟪 Exemplo 6 — Expressões SQL no WHERE

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

# 🟫 Exemplo 7 — CTE final com agregação automática

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

# 📝 Notas finais

-   Sempre use **funções agregadas completas no HAVING**
-   Sempre envie **order_by** se quiser paginação
-   CTEs nunca paginam
-   CTEs podem referenciar CTEs anteriores
-   Toda comparação campo–campo deve usar `"op": "=field"`
-   Expressões SQL são permitidas apenas como `{ "sql": "..." }`

---
