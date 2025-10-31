# 🧩 Guia de Uso da Rota `/data/query`

## 📘 Descrição

A rota `/data/query` é uma **API analítica dinâmica** que permite consultas SQL seguras e automatizadas sobre o banco de dados **Protheus (SB1010, SB2010, etc.)**, com suporte a filtros, agregações, funções SQL e paginação.

---

## ⚙️ Método e Endpoint

| Método | Endpoint      | Autenticação         |
| ------ | ------------- | -------------------- |
| `POST` | `/data/query` | 🔐 Requer JWT válido |

---

## 🧱 Corpo da Requisição

```json
{
    "tables": ["SB1010", "SB2010"],
    "columns": ["SB1010.B1_COD", "SB1010.B1_DESC", "SB2010.B2_QATU"],
    "joins": [
        {
            "type": "LEFT",
            "table": "SB2010",
            "left": "SB1010.B1_COD",
            "right": "SB2010.B2_COD"
        }
    ],
    "filters": {
        "UPPER(TRIM(SB1010.B1_DESC))": { "op": "LIKE", "value": "%CABO%" },
        "SB1010.B1_GRUPO": { "op": "=", "value": "1008" },
        "SB1010.D_E_L_E_T_": { "op": "=", "value": "" },
        "CAST(SB2010.B2_QATU AS VARCHAR(50))": { "op": "IS NOT NULL" },
        "SB2010.D_E_L_E_T_": { "op": "=", "value": "" }
    },
    "order_by": [{ "field": "SB1010.B1_COD", "direction": "ASC" }],
    "page": 1,
    "page_size": 20
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
    "tables": ["SB2010"],
    "columns": ["SB2010.B2_FILIAL", "SB2010.B2_LOCAL"],
    "aggregates": {
        "SB2010.B2_CM1": "AVG",
        "SB2010.B2_QATU": "SUM"
    },
    "filters": {
        "SB2010.B2_TIPO": { "op": "=", "value": "PA" },
        "SB2010.D_E_L_E_T_": { "op": "=", "value": "" }
    },
    "group_by": ["SB2010.B2_FILIAL", "SB2010.B2_LOCAL"],
    "rollup": true,
    "having": { "SUM(SB2010.B2_QATU)": { "op": ">", "value": 100 } },
    "order_by": [{ "field": "SB2010.B2_FILIAL", "direction": "ASC" }]
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
    "tables": ["SB1010", "SB2010"],
    "columns": [
        "SB1010.B1_COD",
        "SB1010.B1_DESC",
        "SB2010.B2_FILIAL",
        "SB2010.B2_LOCAL"
    ],
    "joins": [
        {
            "type": "LEFT",
            "table": "SB2010",
            "left": "SB1010.B1_COD",
            "right": "SB2010.B2_COD"
        }
    ],
    "filters": {
        "UPPER(SB1010.B1_DESC)": { "op": "LIKE", "value": "%CABO%" },
        "SB1010.B1_GRUPO": { "op": "=", "value": "1008" },
        "SB1010.D_E_L_E_T_": { "op": "=", "value": "" },
        "SB2010.D_E_L_E_T_": { "op": "=", "value": "" }
    },
    "aggregates": { "SB2010.B2_QATU": "SUM" },
    "group_by": ["SB2010.B2_FILIAL", "SB2010.B2_LOCAL"],
    "rollup": true,
    "order_by": [{ "field": "SB2010.B2_FILIAL", "direction": "ASC" }],
    "page": 1,
    "page_size": 50
}
```

---

## ✅ Resposta de Sucesso

```json
{
    "success": true,
    "message": "Consulta executada com sucesso — página 1 de 1.",
    "data": {
        "sql": "SELECT ...",
        "page": 1,
        "page_size": 10,
        "total": 57,
        "pages": 3,
        "data": [
            {
                "B1_COD": "10080522",
                "DESCRICAO": "TERM. PONTA CABO 0,75-1,50MM2 NU FITADO",
                "B2_QATU": 120
            }
        ]
    }
}
```

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
    "tables": ["SB1010", "SB2010"],
    "columns": [
        "SB1010.B1_COD",
        "SB1010.B1_DESC",
        "SB2010.B2_FILIAL",
        "SB2010.B2_LOCAL"
    ],
    "joins": [
        {
            "type": "LEFT",
            "table": "SB2010",
            "left": "SB1010.B1_COD",
            "right": "SB2010.B2_COD"
        }
    ],
    "filters": {
        "UPPER(SB1010.B1_DESC)": { "op": "LIKE", "value": "%CABO%" },
        "SB1010.B1_GRUPO": { "op": "=", "value": "1008" },
        "SB1010.D_E_L_E_T_": { "op": "=", "value": "" },
        "SB2010.D_E_L_E_T_": { "op": "=", "value": "" }
    },
    "aggregates": { "SB2010.B2_QATU": "SUM" },
    "group_by": ["SB2010.B2_FILIAL", "SB2010.B2_LOCAL"],
    "rollup": true,
    "order_by": [{ "field": "SB2010.B2_FILIAL", "direction": "ASC" }],
    "page": 1,
    "page_size": 50
}
```
