# 🧩 Guia de Uso da Rota `/data/sql`

## 📘 Descrição

A rota `/data/sql` permite a **execução direta de instruções SQL puras**, enviadas em **formato JSON**, com **validação de segurança completa**, incluindo:

-   Verificação de **tabelas permitidas** (`allowed_tables.json`);
-   Bloqueio de **comandos DML e DDL** (`UPDATE`, `DELETE`, `DROP`, etc.);
-   Suporte a **CTEs e CTEs recursivas** (`WITH` e `WITH RECURSIVE`);
-   Prevenção de **injeções SQL e múltiplos comandos encadeados**;
-   Compatibilidade com **SQL Server (T-SQL)**.

> ⚠️ Esta rota deve ser usada **apenas por agentes técnicos homologados** (nível de automação avançado).  
> O usuário humano nunca deve visualizar ou editar diretamente o SQL enviado.

---

## ⚙️ Método e Endpoint

| Método | Endpoint    | Autenticação         | Tipo de Body       |
| ------ | ----------- | -------------------- | ------------------ |
| `POST` | `/data/sql` | 🔐 Requer JWT válido | `application/json` |

---

## 🧱 Corpo da Requisição

O corpo deve conter o SQL dentro de um objeto JSON, conforme abaixo:

### ✅ Exemplo correto


```json
{
    "sql": "WITH hierarchy AS (SELECT B1_COD, B1_GRUPO, 0 AS LEVEL FROM SB1010 WHERE B1_GRUPO = '1008' UNION ALL SELECT p.B1_COD, p.B1_GRUPO, h.LEVEL + 1 FROM SB1010 p JOIN hierarchy h ON p.B1_GRUPO = h.B1_COD) SELECT * FROM hierarchy;"
}
```

### ❌ Exemplo incorreto

```sql
WITH hierarchy AS (
    SELECT B1_COD, B1_GRUPO, 0 AS LEVEL
    FROM SB1010
)
SELECT * FROM hierarchy;
```

> OBS: Remova qualquer comentário antes de executar o sql <br>

> A rota `/data/sql` **não aceita texto puro** (`text/plain`). <br>

> O corpo deve ser enviado como **JSON** (`Content-Type: application/json`).

---

## 🧰 Recursos e Validações

| Categoria                   | Comportamento                                                                          |
| --------------------------- | -------------------------------------------------------------------------------------- |
| **Comando permitido**       | Somente `SELECT`                                                                       |
| **CTE simples e recursiva** | Suportadas                                                                             |
| **Tabelas**                 | Limitadas a `allowed_tables.json`                                                      |
| **Funções SQL**             | `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`, `TRIM`, `UPPER`, `LOWER`, `CAST`, `CONVERT`, etc. |
| **Paginação e ORDER BY**    | Controladas pelo SQL enviado                                                           |
| **Múltiplos comandos**      | 🚫 Bloqueados (`;` detectado fora do contexto)                                         |
| **Comentários**             | Suportados (`--` e `/* ... */`)                                                        |
| **Banco SQL Server**        | `WITH RECURSIVE` é automaticamente ajustado para `WITH`                                |
| **Banco PostgreSQL/MySQL**  | Suporte nativo a `WITH RECURSIVE`                                                      |

---

## 📈 Exemplo de Requisição

```bash
curl -X POST "https://api.transformamaisdelpi.com.br/data/sql" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "WITH hierarchy AS (SELECT B1_COD, B1_GRUPO, 0 AS LEVEL FROM SB1010 WHERE B1_GRUPO = '\''1008'\'' UNION ALL SELECT p.B1_COD, p.B1_GRUPO, h.LEVEL + 1 FROM SB1010 p JOIN hierarchy h ON p.B1_GRUPO = h.B1_COD) SELECT * FROM hierarchy;"
  }'
```

---

## ✅ Resposta de Sucesso

```json
{
    "success": true,
    "sql": "WITH hierarchy AS (...) SELECT * FROM hierarchy;",
    "total": 37,
    "data": [
        { "B1_COD": "10080123", "B1_GRUPO": "1008", "LEVEL": 0 },
        { "B1_COD": "10080125", "B1_GRUPO": "10080123", "LEVEL": 1 }
    ]
}
```

---

## ❌ Resposta de Erro

### 🚫 Comando proibido

```json
{
    "success": false,
    "message": "Comando proibido detectado: UPDATE"
}
```

### 🚫 Tabela não permitida

```json
{
    "success": false,
    "message": "Tabela 'ZZ9999' não autorizada (fora da whitelist allowed_tables.json)."
}
```

### 🚫 SQL encadeado

```json
{
    "success": false,
    "message": "⚠️ Detecção de múltiplos comandos SQL — apenas uma instrução é permitida."
}
```

---

## 🧠 Boas Práticas

-   Sempre **finalize o SQL com `;`** (recomendado).
-   Prefira `WITH` (sem `RECURSIVE`) quando estiver em ambiente SQL Server.
-   Evite comandos longos — para relatórios complexos, use a rota `/data/query`.
-   Utilize sempre **CTEs nomeadas claramente** (`WITH estoque_total AS (...)`).
-   Mantenha a lista de `allowed_tables.json` atualizada conforme o ambiente Protheus.

---

## 🧱 Exemplo de uso interno pelo agente

### 🧠 Requisição automática (modo agente)

Quando o agente precisar consultar dados SQL puros:

1. Verificar se o comando é um `SELECT` válido.
2. Montar o JSON conforme o modelo abaixo:

    ```json
    { "sql": "SELECT TOP 3 * FROM SB1010 WHERE D_E_L_E_T_ = '';" }
    ```

3. Enviar o corpo JSON via `/data/sql` (Content-Type: application/json).
4. Retornar apenas o resultado (`data` e `total`) — **nunca o SQL completo**.
5. Caso o SQL seja rejeitado, relatar ao usuário:  
   _“Comando rejeitado por segurança SQL. Apenas SELECTs em tabelas permitidas são aceitos.”_

---

## 🔐 Limitações

-   Não executa `INSERT`, `UPDATE`, `DELETE` ou `ALTER`.
-   Não suporta `GO` (batch SQL Server).
-   Apenas uma instrução por requisição.
-   Não executa funções de sistema (`EXEC`, `sp_...`).

---

## 🧾 Resumo rápido

| Item                 | `/data/query`           | `/data/sql`                  |
| -------------------- | ----------------------- | ---------------------------- |
| Entrada              | JSON estruturado        | JSON com campo `"sql"`       |
| Validação            | Estrutural (Pydantic)   | Sintática (Regex + AST leve) |
| Tipo de consulta     | Montada via JSON        | Escrita manual pelo agente   |
| CTEs                 | Sim                     | Sim (inclusive recursivas)   |
| Paginação automática | Sim                     | Não (manual via SQL)         |
| Segurança            | Alta (campos whitelist) | Alta (com validação direta)  |

## 📗 Exemplos de solicitações

### 1. Usuário: "Listar produtos programados para produzir hoje"

🧱 Tabelas envolvidas

-   SC2010 — Ordens de Produção
-   SH8010 — Operações Alocadas
-   SD4010 — Requisições Empenhadas
-   SB1010 — Cadastro de produtos

⚙️ Condições aplicadas

-   H8.H8_DTINI = data atual
-   Filial = 01 ou 02 
-   C2_PRIOR = 500 (Prioridade Livre)
-   Somente registros ativos (`D_E_L_E_T_ = ''`)

💾 Consulta:

```sql
SELECT
    OP.C2_PRODUTO        AS COD_PRODUTO,
    P.B1_DESC            AS DESCRICAO_PRODUTO,
    OP.C2_QUANT          AS QTD_PLANEJADA,
    OP.C2_UM             AS UNIDADE,
    OA.H8_DTINI          AS DATA_INICIO_OPERACAO
FROM SC2010 OP
LEFT JOIN SD4010 RE
    ON RE.D4_OP = OP.C2_OP
LEFT JOIN SH8010 OA
    ON OA.H8_OP    = RE.D4_OP
   AND OA.H8_OPER = RE.D4_OPERAC
LEFT JOIN SB1010 P
    ON P.B1_COD = OP.C2_PRODUTO
WHERE
        OP.C2_FILIAL = :FILIAL
    AND RE.D4_FILIAL = :FILIAL
    AND OA.H8_FILIAL = :FILIAL
    AND OP.C2_PRIOR  = '500'
    AND OA.H8_DTINI  = :DATA
    AND OP.D_E_L_E_T_ = ''
    AND RE.D_E_L_E_T_ = ''
    AND OA.D_E_L_E_T_ = ''
    AND P.D_E_L_E_T_  = ''
    AND P.B1_TIPO = 'PA'
GROUP BY
    OP.C2_PRODUTO,
    P.B1_DESC,
    OP.C2_QUANT,
    OP.C2_UM,
    OA.H8_DTINI
ORDER BY
    OP.C2_PRODUTO ASC
```


### 2. Usuário: "Listar OPs (ordens de produção) finalizadas hoje"

🧱 Tabelas envolvidas:

-   SC2010 — Ordens de Produção
-   SD4010 — Empenhos de componentes
-   SB1010 — Cadastro de produtos
-   SH8010 — Roteiro de operações

⚙️ Condições aplicadas:

-   OP.C2_QUANT = OP.C2_QUJE → total necessário produzido
-   OA.H8_DTINI = 20251127 → operação de hoje
-   Filial = 01 ou 02 → Pergunte a filial ao usuário
-   Todos os registros ativos (`D_E_L_E_T_ = ''`)
-   OP.C2_PRIOR = 500 → prioridade Livre (501 Bloqueado)

💾 Consulta:

```sql
SELECT
    OP.C2_OP        AS COD_OP,
    OP.C2_PRODUTO   AS COD_PRODUTO,
    P.B1_DESC       AS DESCRICAO_PRODUTO,
    OP.C2_QUANT     AS QTD_OP,
    OP.C2_QUJE      AS QTD_PRODUZIDA,
    OP.C2_UM        AS UNIDADE,
    OA.H8_HRINI     AS HORA_INICIO,
    OA.H8_HRFIM     AS HORA_FIM,
    OA.H8_DTINI     AS DATA_INICIO,
    OA.H8_DTFIM     AS DATA_FIM,
    OA.H8_CTRAB     AS CT
FROM SC2010 OP
INNER JOIN SD4010 RE
    ON RE.D4_OP = OP.C2_OP
INNER JOIN SB1010 P
    ON P.B1_COD = OP.C2_PRODUTO
INNER JOIN SH8010 OA
    ON OA.H8_OP    = RE.D4_OP
   AND OA.H8_OPER = RE.D4_OPERAC
WHERE
    OP.D_E_L_E_T_ = ''
AND RE.D_E_L_E_T_ = ''
AND P.D_E_L_E_T_  = ''
AND OA.D_E_L_E_T_ = ''
AND OP.C2_QUANT   = OP.C2_QUJE        
AND OP.C2_PRIOR   = '500'             
AND OP.C2_FILIAL  = :FILIAL
AND RE.D4_FILIAL  = :FILIAL
AND OA.H8_FILIAL  = :FILIAL
AND OA.H8_DTINI   = :DATA
GROUP BY
    OP.C2_OP,
    OP.C2_PRODUTO,
    P.B1_DESC,
    OP.C2_QUANT,
    OP.C2_QUJE,
    OP.C2_UM,
    OA.H8_HRINI,
    OA.H8_HRFIM,
    OA.H8_DTINI,
    OA.H8_DTFIM,
    OA.H8_CTRAB
ORDER BY
    OA.H8_HRINI ASC,
    OP.C2_OP   ASC;
```

### 3. Usuário: "Listar OPs programadas em aberto (não finalizadas) de hoje"

🧱 Tabelas envolvidas:

-   SC2010 — Ordens de Produção
-   SD4010 — Empenhos de componentes
-   SB1010 — Cadastro de produtos
-   SH8010 — Roteiro de operações

⚙️ Condições aplicadas:

-   OP.C2_QUANT > OP.C2_QUJE → não finalizada
-   OA.H8_DTINI = 20251127 → operação de hoje
-   Filial = 01 ou 02 → Pergunte a filial ao usuário
-   Todos os registros ativos (`D_E_L_E_T_ = ''`)
-   OP.C2_PRIOR = 500 → prioridade Livre (501 Bloqueado)

💾 Consulta:

```sql
SELECT
    OP.C2_OP AS COD_OP,
    OP.C2_PRODUTO AS COD_PRODUTO,
    P.B1_DESC AS DESCRICAO_PRODUTO,
    OP.C2_QUANT AS QTD_OP,
    OP.C2_QUJE AS QTD_PRODUZIDA,
    (OP.C2_QUANT * 1000 - OP.C2_QUJE * 1000) / 1000 AS QTD_FALTANTE,
    OP.C2_UM AS UNIDADE,
    OA.H8_HRINI AS HORA_INICIO,
    OA.H8_DTINI AS DATA_INICIO,
    OA.H8_CTRAB AS CT
FROM SC2010 OP
INNER JOIN SD4010 RE
    ON RE.D4_OP = OP.C2_OP
INNER JOIN SB1010 P
    ON P.B1_COD = OP.C2_PRODUTO
INNER JOIN SH8010 OA
    ON OA.H8_OP = RE.D4_OP
   AND OA.H8_OPER = RE.D4_OPERAC
WHERE
    OP.D_E_L_E_T_ = ''
AND RE.D_E_L_E_T_ = ''
AND P.D_E_L_E_T_  = ''
AND OA.D_E_L_E_T_ = ''
AND OP.C2_QUANT  > OP.C2_QUJE
AND OP.C2_PRIOR  = '500'
AND OP.C2_FILIAL = :FILIAL
AND RE.D4_FILIAL = :FILIAL
AND OA.H8_FILIAL = :FILIAL
AND OA.H8_DTINI  = :DATA
GROUP BY
    OP.C2_OP,
    OP.C2_PRODUTO,
    P.B1_DESC,
    OP.C2_QUANT,
    OP.C2_QUJE,
    OP.C2_UM,
    OA.H8_HRINI,
    OA.H8_DTINI,
    OA.H8_CTRAB
ORDER BY
    OA.H8_HRINI ASC,
    OP.C2_OP ASC;
```


### 4. Usuário: "Liste as OPs distintas em aberto."

🧱 Tabelas envolvidas

-   SC2010 — Ordens
-   SD4010 — Empenhos
-   SH8010 — Operações

⚙️ Condições aplicadas

-   DISTINCT OP.C2_OP
-   C2_QUANT > C2_QUJE
-   H8_DTINI = hoje
-   C2_PRIOR = 500
-   Filial = 01 ou 02
-   `D_E_L_E_T_ = ''`

💾 Consulta

```sql
SELECT DISTINCT
    OP.C2_OP AS COD_OP
FROM SC2010 OP
INNER JOIN SD4010 RE
    ON OP.C2_OP = RE.D4_OP
INNER JOIN SH8010 OA
    ON RE.D4_OP    = OA.H8_OP
   AND RE.D4_OPERAC = OA.H8_OPER
WHERE
    OP.D_E_L_E_T_ = ''
    AND RE.D_E_L_E_T_ = ''
    AND OA.D_E_L_E_T_ = ''
    AND OP.C2_FILIAL = :FILIAL
    AND RE.D4_FILIAL = :FILIAL
    AND OA.H8_FILIAL = :FILIAL
    AND OP.C2_PRIOR = '500'
    AND OP.C2_QUANT > OP.C2_QUJE
    AND OA.H8_DTINI = :DATA
ORDER BY
    OP.C2_OP ASC;
```


### 5. Usuário: "Agrupar as ordens por centro de trabalho (CT) e contar finalizadas e não finalizadas."

🧱 Tabelas envolvidas

-   SC2010
-   SD4010
-   SH8010

⚙️ Condições aplicadas

-   C2_QUANT = C2_QUJE → finalizada
-   C2_QUANT > C2_QUJE → não finalizada
-   Agrupamento por H8_CTRAB
-   C2_PRIOR = 500
-   H8_DTINI = hoje
-   Filial = 01 ou 02
-   Registros ativos

💾 Consulta

```sql
SELECT
    OA.H8_CTRAB AS CT,
    COUNT(DISTINCT CASE 
        WHEN OP.C2_QUANT = OP.C2_QUJE THEN OP.C2_OP 
    END) AS OPS_FINALIZADAS,
    COUNT(DISTINCT CASE 
        WHEN OP.C2_QUANT > OP.C2_QUJE THEN OP.C2_OP 
    END) AS OPS_NAO_FINALIZADAS,
    COUNT(DISTINCT OP.C2_OP) AS TOTAL_OPS
FROM SC2010 OP
INNER JOIN SD4010 RE
    ON OP.C2_OP = RE.D4_OP
INNER JOIN SH8010 OA
    ON RE.D4_OP     = OA.H8_OP
   AND RE.D4_OPERAC = OA.H8_OPER
WHERE
    OP.D_E_L_E_T_ = ''
    AND RE.D_E_L_E_T_ = ''
    AND OA.D_E_L_E_T_ = ''
    AND OP.C2_FILIAL = :FILIAL
    AND RE.D4_FILIAL = :FILIAL
    AND OA.H8_FILIAL = :FILIAL
    AND OP.C2_PRIOR = '500'
    AND OA.H8_DTINI = :DATA
GROUP BY
    OA.H8_CTRAB
ORDER BY
    OA.H8_CTRAB ASC;
```

### 6. Usuário: “Identificar componentes sem empenho registrado (travamento de produção) para um CT específico”

🧱 Tabelas envolvidas

-   SD4010 — Empenhos
-   SH8010 — Operações
-   SB1010 — Produtos
-   SC2010 — Ordens de Produção  

⚙️ Condições aplicadas

-   D4_QUANT = 0 (sem empenho)
-   H8_CTRAB = CT-19
-   H8_DTINI = hoje
-   C2_PRIOR = 500
-   Filial = 01
-   Registros ativos

💾 Consulta

```sql
SELECT
    RE.D4_OP        AS COD_OP,
    RE.D4_PRODUTO   AS COD_PRODUTO,
    P.B1_DESC       AS DESCRICAO_PRODUTO,
    RE.D4_OPERAC    AS OPERACAO,
    RE.D4_QUANT     AS QTD_EMPENHO,
    OA.H8_CTRAB     AS CT
FROM SD4010 RE
INNER JOIN SC2010 OP
    ON OP.C2_OP = RE.D4_OP
INNER JOIN SB1010 P
    ON RE.D4_PRODUTO = P.B1_COD
INNER JOIN SH8010 OA
    ON RE.D4_OP      = OA.H8_OP
   AND RE.D4_OPERAC = OA.H8_OPER
WHERE
    RE.D_E_L_E_T_ = ''
    AND OP.D_E_L_E_T_ = ''
    AND P.D_E_L_E_T_  = ''
    AND OA.D_E_L_E_T_ = ''
    AND RE.D4_FILIAL = :FILIAL
    AND OP.C2_FILIAL = :FILIAL
    AND OA.H8_FILIAL = :FILIAL
    AND OP.C2_PRIOR = '500'
    AND RE.D4_QUANT = 0
    AND OA.H8_CTRAB = :CT
    AND OA.H8_DTINI = :DATA
ORDER BY
    RE.D4_OP ASC;
```

### 7. Usuário: “Identificar ordens finalizadas sem consumo de componentes”

🧱 Tabelas envolvidas

-   SC2010 — Ordens
-   SD4010 — Empenhos
-   SB1010 — Produtos
-   SH8010 — Operações

⚙️ Condições aplicadas

-   C2_QUANT = C2_QUJE (finalizada)
-   SUM(D4_QUANT) = 0 (sem consumo)
-   H8_CTRAB = CT-19
-   H8_DTINI = hoje
-   C2_PRIOR = 500
-   Filial = 01
-   Registros ativos

💾 Consulta

```sql
SELECT
    OP.C2_OP        AS COD_OP,
    OP.C2_PRODUTO   AS COD_PRODUTO,
    P.B1_DESC       AS DESCRICAO_PRODUTO,
    OP.C2_QUANT     AS QTD_PLANEJADA,
    OP.C2_QUJE      AS QTD_PRODUZIDA,
    RE.D4_COD       AS COD_COMPONENTE,
    RE.D4_OPERAC    AS OPERACAO,
    SUM(RE.D4_QUANT) AS QTD_EMPENHO,
    OA.H8_CTRAB     AS CT
FROM SC2010 OP
INNER JOIN SD4010 RE
    ON OP.C2_OP = RE.D4_OP
INNER JOIN SB1010 P
    ON OP.C2_PRODUTO = P.B1_COD
INNER JOIN SH8010 OA
    ON RE.D4_OP      = OA.H8_OP
   AND RE.D4_OPERAC = OA.H8_OPER
WHERE
    OP.D_E_L_E_T_ = ''
    AND RE.D_E_L_E_T_ = ''
    AND P.D_E_L_E_T_  = ''
    AND OA.D_E_L_E_T_ = ''
    AND OP.C2_FILIAL = :FILIAL
    AND RE.D4_FILIAL = :FILIAL
    AND OA.H8_FILIAL = :FILIAL
    AND OP.C2_PRIOR = '500'
    AND OA.H8_DTINI = :DATA
    AND OA.H8_CTRAB = :CT
    AND OP.C2_QUANT = OP.C2_QUJE
GROUP BY
    OP.C2_OP,
    OP.C2_PRODUTO,
    P.B1_DESC,
    OP.C2_QUANT,
    OP.C2_QUJE,
    RE.D4_COD,
    RE.D4_OPERAC,
    OA.H8_CTRAB
HAVING
    SUM(RE.D4_QUANT) = 0
ORDER BY
    OP.C2_OP ASC;
```


### 8. Usuário: "Média de tempo por CT (H8_HRINI → H8_HRFIM)"

🧱 Tabelas envolvidas

-   SC2010 — Ordens de Produção
-   SD4010 — Empenhos
-   SH8010 — Operações

⚙️ Condições aplicadas

-   Apenas ordens finalizadas (C2_QUANT = C2_QUJE)
-   Agrupar por H8_CTRAB
-   C2_PRIOR = 500
-   Filial = 01
-   H8_DTINI = hoje
-   H8_HRFIM IS NOT NULL
-   H8_HRINI IS NOT NULL
-   Registros ativos

💾 Consulta

```sql
SELECT
    OA.H8_CTRAB AS CT,
    CAST(
        AVG(
            (
                (CAST(LEFT(REPLACE(OA.H8_HRFIM, ':', ''), 2) AS INT) * 60 +
                 CAST(RIGHT(REPLACE(OA.H8_HRFIM, ':', ''), 2) AS INT)
                )
              -
                (CAST(LEFT(REPLACE(OA.H8_HRINI, ':', ''), 2) AS INT) * 60 +
                 CAST(RIGHT(REPLACE(OA.H8_HRINI, ':', ''), 2) AS INT)
                )
            ) / 60.0
        ) AS FLOAT
    ) AS TEMPO_MEDIO_HORAS
FROM SC2010 OP
INNER JOIN SD4010 RE
    ON OP.C2_OP = RE.D4_OP
INNER JOIN SH8010 OA
    ON RE.D4_OP      = OA.H8_OP
   AND RE.D4_OPERAC = OA.H8_OPER
WHERE
    OP.D_E_L_E_T_ = ''
    AND RE.D_E_L_E_T_ = ''
    AND OA.D_E_L_E_T_ = ''
    AND OP.C2_FILIAL = :FILIAL
    AND RE.D4_FILIAL = :FILIAL
    AND OA.H8_FILIAL = :FILIAL
    AND OP.C2_PRIOR = '500'
    AND OA.H8_DTINI = :DATA
    AND OA.H8_DTFIM = :DATA
    AND OA.H8_HRINI IS NOT NULL
    AND OA.H8_HRFIM IS NOT NULL
    AND OP.C2_QUANT = OP.C2_QUJE
GROUP BY
    OA.H8_CTRAB
ORDER BY
    OA.H8_CTRAB ASC;

```

> Atenção: as colunas de horas no TOTVS são no formato texto HH:MM por isso é necessário usar o CAST


### 9. Usuário: "Estoque total por filial/local, Grupo 1008 Descrição TERM. BANDEIRA"

🧱 Tabelas envolvidas

-   SD4010 — Empenhos de componentes
-   SH8010 — Operações alocadas
-   SB1010 — Cadastro de produtos

⚙️ Condições aplicadas

-   `D4_QUANT` = 0 → componente sem empenho
-   `H8_CTRAB` = 'CT-19' → filtrar por centro de trabalho específico
-   `H8_DTINI` = data atual (20251127)
-   `C2_PRIOR` = 500 → apenas OPs com prioridade livre
-   Filial = 01
-   Registros ativos (`D_E_L_E_T* = '' `)

💾 Consulta

```sql
WITH estoque_total AS (
    SELECT
        E.B2_FILIAL,
        E.B2_LOCAL,
        E.B2_COD,
        SUM(E.B2_QATU) AS QT
    FROM SB2010 E
    WHERE
        E.D_E_L_E_T_ = ''
    GROUP BY
        E.B2_FILIAL,
        E.B2_LOCAL,
        E.B2_COD
)
SELECT
    T.B2_FILIAL,
    T.B2_LOCAL,
    P.B1_COD,
    P.B1_DESC,
    T.QT
FROM SB1010 P
INNER JOIN estoque_total T
    ON P.B1_COD = T.B2_COD
WHERE
    P.D_E_L_E_T_ = ''
    AND P.B1_DESC LIKE '%TERM. BANDEIRA%'
    and P.B1_GRUPO = '1008'
ORDER BY
    P.B1_COD ASC;
```
