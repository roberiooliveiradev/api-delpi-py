# 🧩 Guia de Uso da Rota `/data/query`

## 📘 Descrição

A rota `/data/query` é uma **API analítica dinâmica** que permite consultas SQL seguras e automatizadas sobre o banco de dados **Protheus (SB1010, SB2010, etc.)**, com suporte a filtros, agregações, funções SQL e paginação.

## 🤖 Instrução de Execução Automática da API DELPI

-   Sempre que precisar consultar a rota `/data/query`, o agente deve:

    -   Montar automaticamente o corpo JSON de forma segura e completa;
    -   Enviar a requisição **diretamente**, sem pedir confirmação do usuário;
    -   Retornar apenas o resultado da API (ou o erro, se houver);
    -   Nunca exibir ou pedir validação do objeto JSON antes do envio.

-   O agente **não deve perguntar “Deseja enviar?”**, “Confirma envio?”, etc.
-   O agente **pode mostrar o JSON enviado apenas em modo de depuração** (quando solicitado explicitamente com “mostre o JSON”).

---

## ⚙️ Método e Endpoint

| Método | Endpoint      | Autenticação         |
| ------ | ------------- | -------------------- |
| `POST` | `/data/query` | 🔐 Requer JWT válido |

---

## 🧱 Corpo da Requisição

```json
{
    "tables": ["SB1010 AS P", "SB2010 AS E"],
    "columns": [
        "P.B1_COD",
        "P.B1_DESC",
        "E.B2_FILIAL",
        "E.B2_LOCAL",
        "E.B2_QATU"
    ],
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
            { "P.B1_GRUPO": { "op": "=", "value": "1008" } },
            { "P.B1_TIPO": { "op": "=", "value": "MP" } },
            { "E.B2_QATU": { "op": ">", "value": 0 } },
            {
                "or": [
                    { "P.B1_DESC": { "op": "NOT LIKE", "value": "%TERM%" } },
                    { "P.B1_DESC": { "op": "NOT LIKE", "value": "%FASTON%" } }
                ]
            }
        ]
    },
    "order_by": [{ "field": "P.B1_DESC", "direction": "ASC" }],
    "page": 1,
    "page_size": 30
}
```

### 🧩 Campo aliases (opcional)

Você também pode definir aliases separadamente:

```json
{
    "tables": ["SB1010", "SB2010"],
    "aliases": { "SB1010": "P", "SB2010": "E" },
    "columns": ["P.B1_COD", "P.B1_DESC", "E.B2_QATU"],
    "joins": [
        {
            "type": "LEFT",
            "table": "SB2010",
            "left": "P.B1_COD",
            "right": "E.B2_COD"
        }
    ]
}
```

---

## 🔍 Operadores de Filtro

| Operador                  | Descrição           | Exemplo                                              |
| ------------------------- | ------------------- | ---------------------------------------------------- |
| `=`                       | Igual               | `"B1_TIPO": {"op": "=", "value": "PA"}`              |
| `<>`                      | Diferente           | `"B2_TIPO": {"op": "<>", "value": "MP"}`             |
| `>` / `<` / `>=` / `<=`   | Comparação numérica | `"B2_QATU": {"op": ">", "value": 0}`                 |
| `LIKE` / `NOT LIKE`       | Busca textual       | `"B1_DESC": {"op": "LIKE", "value": "%CABO%"}`       |
| `IN` / `NOT IN`           | Lista de valores    | `"B1_GRUPO": {"op": "IN", "value": ["1008","1009"]}` |
| `BETWEEN`                 | Faixa de valores    | `"B2_QATU": {"op": "BETWEEN", "value": [10,50]}`     |
| `IS NULL` / `IS NOT NULL` | Nulidade            | `"B2_QATU": {"op": "IS NOT NULL"}`                   |

---

## 🧮 Agregações e Agrupamentos

```json
{
    "tables": ["SB2010 AS E"],
    "columns": ["E.B2_FILIAL", "E.B2_LOCAL"],
    "aggregates": {
        "E.B2_QATU": "SUM",
        "E.B2_CM1": "AVG"
    },
    "group_by": ["E.B2_FILIAL", "E.B2_LOCAL"],
    "rollup": true,
    "having": {
        "SUM(E.B2_QATU)": { "op": ">", "value": 100 }
    },
    "order_by": [{ "field": "E.B2_FILIAL", "direction": "ASC" }]
}
```

---

## 🧠 Funções SQL Seguras

| Função                 | Tipo      | Exemplo                                 |
| ---------------------- | --------- | --------------------------------------- |
| `TRIM()`               | Texto     | `"TRIM(SB1010.B1_DESC)"`                |
| `UPPER()` / `LOWER()`  | Texto     | `"UPPER(SB1010.B1_DESC)"`               |
| `LEN()`                | Texto     | `"LEN(SB1010.B1_DESC)"`                 |
| `CAST()` / `CONVERT()` | Conversão | `"CAST(SB2010.B2_QATU AS VARCHAR(50))"` |
| `LTRIM()` / `RTRIM()`  | Texto     | `"LTRIM(SB2010.B2_LOCAL)"`              |

> ⚠️ Use `CAST(... AS VARCHAR)` ao aplicar TRIM/UPPER em colunas numéricas.

---

## 📊 Exemplo Avançado

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

> ⚠️ Não mostrar para o usuário o SQL retornado pela API.

---

## ⚠️ Boas Práticas

-   Sempre filtre `D_E_L_E_T_ = ""` para excluir registros lógicos.
-   Use `LEFT JOIN` quando quiser manter produtos sem movimento (SB1010 → SB2010).
-   Evite `TRIM()` em colunas numéricas — use `CAST()` antes.
-   Mantenha o `ORDER BY` em colunas da tabela principal (`SB1010`).

---

## 🧠 Exemplo de Prompt GPT

> “Monte uma consulta que mostre o total de estoque (`B2_QATU`) por filial e local apenas para produtos do grupo 1008 com ‘CABO’ na descrição, agrupando com subtotais.”

### GPT deve gerar:

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
