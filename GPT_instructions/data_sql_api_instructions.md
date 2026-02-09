# 🧩 Guia de Uso da Rota `/data/sql`

## 📘 Descrição

A rota `/data/sql` permite a **execução controlada de SQL puro (T-SQL)**, enviadas em **formato JSON**, com **validação de segurança completa**,
Ela funciona como uma camada segura de leitura sobre o banco TOTVS Protheus (SQL Server), permitindo consultas avançadas sem expor DDL/DML ou risco de execução arbitrária, incluindo:

-   Verificação de **tabelas permitidas** (`allowed_tables.json`);
-   Bloqueio de **comandos DML e DDL** (`UPDATE`, `DELETE`, `DROP`, etc.);
-   Suporte a **CTEs e CTEs recursivas** (`WITH` e `WITH RECURSIVE`);
-   Compatibilidade com **SQL Server (T-SQL)**.

Principais capacidades

-   ✅ Execução de SELECTs simples ou múltiplos SELECTs
-   ✅ Suporte a DECLARE, SET e variáveis escalares
-   ✅ Suporte a CTEs (WITH), inclusive múltiplas CTEs
-   ✅ Suporte a comentários SQL (-- e /* ... */)
-   ✅ Validação de tabelas físicas via whitelist
-   ❌ Bloqueio total de DML, DDL, EXEC e transações

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

| Categoria                     | Comportamento                       |
| ----------------------------- | ---------------------------------------------------------------- |
| **Comandos permitidos**       | `DECLARE`, `SET`, `SELECT`, `WITH`  |
| **CTEs**                      | Suportadas (simples e múltiplas)    |
| **Múltiplos SELECTs**         | ✅ Permitidos na mesma requisição    |
| **Variáveis SQL**             | `DECLARE` e `SET` permitidos        |
| **Funções SQL**               | `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`, `TRIM`, `UPPER`, `LOWER`, `CAST`, `CONVERT`, etc. |
| **Comentários SQL**           | Suportados (`--` e `/* ... */`)     |
| **Tabelas físicas**           | Validadas via `allowed_tables.json` |
| **CTEs na whitelist**         | ❌ Não exigidas                      |
| **DML / DDL**                 | ❌ Bloqueados                        |
| **EXEC / stored procedures**  | ❌ Bloqueados                        |
| **Transações (BEGIN/COMMIT)** | ❌ Bloqueadas                        |
| **GO / batches**              | ❌ Não suportados                    |


---

## 📈 Exemplo de Requisição

```bash
curl -X POST "https://api.transformamaisdelpi.com.br/data/sql" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "DECLARE @G VARCHAR(10); SET @G = '\''1008'\''; SELECT TOP 3 * FROM SB1010 WHERE B1_GRUPO = @G;"
  }'
```

---

## ✅ Resposta de Sucesso

-   Consulta simples

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

-   Múltiplos SELECTs

```json
{
  "success": true,
  "results": [
    {
      "index": 1,
      "total": 3,
      "data": [ ... ]
    },
    {
      "index": 2,
      "total": 1,
      "data": [ ... ]
    }
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

### 🚫 SQL inválido

```json
{
  "success": false,
  "message": "Somente instruções DECLARE, SET, SELECT ou WITH são permitidas."
}
```

---

## 🧠 Boas Práticas

-   Sempre **finalize o SQL com `;`** (recomendado).
-   Declare todas as variáveis antes do WITH ou SELECT
-   Prefira CTEs para queries longas e legíveis
-   Use comentários para documentar regras de negócio
-   Use aliases claros (SB1, SH6, C)
-   Prefira `WITH` (sem `RECURSIVE`) quando estiver em ambiente SQL Server.
-   Utilize sempre **CTEs nomeadas claramente** (`WITH estoque_total AS (...)`).
-   Mantenha a lista de `allowed_tables.json` atualizada conforme o ambiente Protheus.

## 🔐 Limitações Importantes

-   Apenas leitura
-   Sem `INSERT`, `UPDATE`, `DELETE`
-   Sem `EXEC` ou `sp_*`
-   Sem `GO`
-   Sem controle automático de paginação
-   Não valida semântica de variáveis (erro vem do SQL Server)


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

## 📗 Exemplos de solicitações

---

### 1. Usuário: **“Listar produtos programados para produzir hoje”**

#### 🎯 Objetivo

Listar os **produtos que possuem ordens de produção programadas para execução no dia**, considerando apenas **ordens ativas**, com **prioridade livre**, permitindo identificar rapidamente **o que está planejado para produzir hoje** por filial.

A consulta tem como finalidade:

- fornecer a **lista diária de produtos programados**;
- apoiar o **planejamento e acompanhamento do PCP**;
- garantir visibilidade do **plano de produção real do dia**;
- considerar apenas **produtos acabados válidos**.

---

#### 🧱 Tabelas envolvidas

##### SC2010 — Ordens de Produção

| Coluna      | Descrição |
|------------|-----------|
| C2_OP      | Ordem de produção |
| C2_PRODUTO | Código do produto |
| C2_QUANT   | Quantidade planejada |
| C2_UM      | Unidade de medida |
| C2_PRIOR   | Prioridade da OP |
| C2_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SH8010 — Operações Alocadas

| Coluna      | Descrição |
|------------|-----------|
| H8_OP      | Ordem de produção |
| H8_OPER    | Operação |
| H8_DTINI   | Data de início da operação |
| H8_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SD4010 — Requisições / Empenhos

| Coluna      | Descrição |
|------------|-----------|
| D4_OP      | Ordem de produção |
| D4_OPERAC  | Operação |
| D4_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código do produto |
| B1_DESC    | Descrição do produto |
| B1_TIPO    | Tipo do produto (PA) |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Operação programada para **hoje**  
  - `H8_DTINI = :DATA`

- Apenas OPs com prioridade **Livre**  
  - `C2_PRIOR = '500'`

- Apenas **produtos acabados**  
  - `B1_TIPO = 'PA'`

- Filial analisada  
  - `:FILIAL` (ex.: 01 ou 02)

- Considerar somente registros ativos  
  - `SC2010.D_E_L_E_T_ = ''`  
  - `SD4010.D_E_L_E_T_ = ''`  
  - `SH8010.D_E_L_E_T_ = ''`  
  - `SB1010.D_E_L_E_T_ = ''`

---

#### 💾 Consulta

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
    OP.C2_PRODUTO ASC;
```

---

### 2. Usuário: **“Listar OPs (ordens de produção) finalizadas hoje”**

#### 🎯 Objetivo

Listar as **ordens de produção (OPs) finalizadas no dia**, considerando apenas **ordens ativas**, com **prioridade livre**, cuja **operação esteja programada para a data informada**.

A consulta tem como finalidade:

- identificar **produção efetivamente concluída no dia**;
- apoiar o **acompanhamento diário do PCP e da produção**;
- permitir análise por **Centro de Trabalho (CT)**;
- garantir que apenas **ordens válidas e encerradas** sejam consideradas.

---

#### 🧱 Tabelas envolvidas

##### SC2010 — Ordens de Produção

| Coluna      | Descrição |
|------------|-----------|
| C2_OP      | Ordem de produção |
| C2_PRODUTO | Código do produto |
| C2_QUANT   | Quantidade planejada |
| C2_QUJE    | Quantidade produzida |
| C2_UM      | Unidade de medida |
| C2_PRIOR   | Prioridade da OP |
| C2_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SD4010 — Empenhos de Componentes

| Coluna      | Descrição |
|------------|-----------|
| D4_OP      | Ordem de produção |
| D4_OPERAC  | Operação |
| D4_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código do produto |
| B1_DESC    | Descrição do produto |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SH8010 — Operações Alocadas

| Coluna      | Descrição |
|------------|-----------|
| H8_OP      | Ordem de produção |
| H8_OPER    | Operação |
| H8_DTINI   | Data de início da operação |
| H8_DTFIM   | Data de término da operação |
| H8_HRINI   | Hora de início |
| H8_HRFIM   | Hora de término |
| H8_CTRAB   | Centro de Trabalho |
| H8_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Ordem **finalizada**  
  - `C2_QUANT = C2_QUJE`

- Operação programada para **hoje**  
  - `H8_DTINI = :DATA`

- Apenas OPs com prioridade **Livre**  
  - `C2_PRIOR = '500'`

- Filial analisada  
  - `:FILIAL` (ex.: 01 ou 02)

- Considerar somente registros ativos  
  - `SC2010.D_E_L_E_T_ = ''`  
  - `SD4010.D_E_L_E_T_ = ''`  
  - `SB1010.D_E_L_E_T_ = ''`  
  - `SH8010.D_E_L_E_T_ = ''`

---

#### 💾 Consulta

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

---

### 3. Usuário: **“Listar OPs programadas em aberto (não finalizadas) de hoje”**

#### 🎯 Objetivo

Listar as **ordens de produção (OPs) programadas para o dia** que **ainda não foram finalizadas**, considerando apenas **ordens ativas**, com **prioridade livre**, permitindo acompanhamento operacional diário por **Centro de Trabalho (CT)**.

A consulta tem como finalidade:

- identificar o **backlog real do dia**;
- acompanhar ordens **em execução ou pendentes**;
- apoiar o **controle de produção e PCP**;
- fornecer visão clara de **quantidade planejada, produzida e faltante**.

---

#### 🧱 Tabelas envolvidas

##### SC2010 — Ordens de Produção

| Coluna      | Descrição |
|------------|-----------|
| C2_OP      | Ordem de produção |
| C2_PRODUTO | Código do produto |
| C2_QUANT   | Quantidade planejada |
| C2_QUJE    | Quantidade produzida |
| C2_UM      | Unidade de medida |
| C2_PRIOR   | Prioridade da OP |
| C2_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SD4010 — Empenhos de Componentes

| Coluna      | Descrição |
|------------|-----------|
| D4_OP      | Ordem de produção |
| D4_OPERAC  | Operação |
| D4_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código do produto |
| B1_DESC    | Descrição do produto |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SH8010 — Operações Alocadas

| Coluna      | Descrição |
|------------|-----------|
| H8_OP      | Ordem de produção |
| H8_OPER    | Operação |
| H8_DTINI   | Data de início da operação |
| H8_HRINI   | Hora de início |
| H8_CTRAB   | Centro de Trabalho |
| H8_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Ordem **em aberto** (não finalizada)  
  - `C2_QUANT > C2_QUJE`

- Operação programada para **hoje**  
  - `H8_DTINI = :DATA`

- Apenas OPs com prioridade **Livre**  
  - `C2_PRIOR = '500'`

- Filial analisada  
  - `:FILIAL` (ex.: 01 ou 02)

- Considerar somente registros ativos  
  - `SC2010.D_E_L_E_T_ = ''`  
  - `SD4010.D_E_L_E_T_ = ''`  
  - `SB1010.D_E_L_E_T_ = ''`  
  - `SH8010.D_E_L_E_T_ = ''`

---

#### 📐 Regra de cálculo da quantidade faltante

A quantidade faltante é calculada a partir da diferença entre o planejado e o produzido:

```text
(C2_QUANT - C2_QUJE)
```

A expressão é ajustada para preservar casas decimais conforme a unidade do produto.

---

#### 💾 Consulta

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

---

### 4. Usuário: **“Liste as OPs distintas em aberto”**

#### 🎯 Objetivo

Listar as **ordens de produção (OPs) distintas que se encontram em aberto**, ou seja, **não finalizadas**, considerando apenas ordens **ativas**, **prioridade livre** e **com operação programada para a data informada**.

A consulta tem como finalidade:

- identificar rapidamente o **backlog real de produção**;
- apoiar o **controle operacional diário**;
- fornecer base para **priorização e acompanhamento** das OPs em execução;
- garantir que apenas ordens **válidas e ativas** sejam analisadas.

---

#### 🧱 Tabelas envolvidas

##### SC2010 — Ordens de Produção

| Coluna      | Descrição |
|------------|-----------|
| C2_OP      | Ordem de produção |
| C2_QUANT   | Quantidade planejada |
| C2_QUJE    | Quantidade produzida |
| C2_PRIOR   | Prioridade da OP |
| C2_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SD4010 — Empenhos / Consumo

| Coluna      | Descrição |
|------------|-----------|
| D4_OP      | Ordem de produção |
| D4_OPERAC  | Operação |
| D4_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SH8010 — Operações Alocadas

| Coluna      | Descrição |
|------------|-----------|
| H8_OP      | Ordem de produção |
| H8_OPER    | Operação |
| H8_DTINI   | Data de início da operação |
| H8_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Ordem **em aberto** (não finalizada)  
  - `C2_QUANT > C2_QUJE`

- Seleção de OPs **distintas**  
  - `DISTINCT C2_OP`

- Apenas OPs com prioridade **Livre**  
  - `C2_PRIOR = '500'`

- Data de execução da operação  
  - `H8_DTINI = :DATA`

- Filial analisada  
  - `:FILIAL` (ex.: 01 ou 02)

- Considerar somente registros ativos  
  - `SC2010.D_E_L_E_T_ = ''`  
  - `SD4010.D_E_L_E_T_ = ''`  
  - `SH8010.D_E_L_E_T_ = ''`

---

#### 💾 Consulta

```sql
SELECT DISTINCT
    OP.C2_OP AS COD_OP
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
    AND OP.C2_QUANT > OP.C2_QUJE
    AND OA.H8_DTINI = :DATA
ORDER BY
    OP.C2_OP ASC;
```

---

### 5. Usuário: **“Agrupar as ordens por centro de trabalho (CT) e contar finalizadas e não finalizadas”**


#### 🎯 Objetivo

Apurar a **quantidade de ordens de produção finalizadas e não finalizadas**, **agrupadas por Centro de Trabalho (CT)**, permitindo uma visão clara do **status produtivo por recurso** em uma data específica.

A consulta tem como finalidade:

- monitorar o **andamento da produção por CT**;
- identificar **acúmulo de ordens não finalizadas**;
- apoiar decisões de **balanceamento de carga e priorização**;
- fornecer um **indicador consolidado** para gestão operacional.

---

#### 🧱 Tabelas envolvidas

##### SC2010 — Ordens de Produção

| Coluna      | Descrição |
|------------|-----------|
| C2_OP      | Ordem de produção |
| C2_QUANT   | Quantidade planejada |
| C2_QUJE    | Quantidade produzida |
| C2_PRIOR   | Prioridade da OP |
| C2_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SD4010 — Empenhos / Consumo

| Coluna      | Descrição |
|------------|-----------|
| D4_OP      | Ordem de produção |
| D4_OPERAC  | Operação |
| D4_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SH8010 — Operações Alocadas

| Coluna      | Descrição |
|------------|-----------|
| H8_OP      | Ordem de produção |
| H8_OPER    | Operação |
| H8_CTRAB   | Centro de Trabalho |
| H8_DTINI   | Data de início da operação |
| H8_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Ordem **finalizada**  
  - `C2_QUANT = C2_QUJE`

- Ordem **não finalizada**  
  - `C2_QUANT > C2_QUJE`

- Agrupamento por **Centro de Trabalho**  
  - `H8_CTRAB`

- Apenas OPs com prioridade **Livre**  
  - `C2_PRIOR = '500'`

- Data de execução da operação  
  - `H8_DTINI = :DATA`

- Filiais analisadas  
  - `:FILIAL` (ex.: 01 ou 02)

- Considerar somente registros ativos  
  - `SC2010.D_E_L_E_T_ = ''`  
  - `SD4010.D_E_L_E_T_ = ''`  
  - `SH8010.D_E_L_E_T_ = ''`

---

#### 💾 Consulta

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
---

### 6. Usuário: **“Identificar componentes sem empenho registrado (travamento de produção) para um CT específico”**


#### 🎯 Objetivo

Identificar **componentes associados a ordens de produção ativas** que **não possuem empenho registrado** (`D4_QUANT = 0`) em um **Centro de Trabalho (CT) específico**, caracterizando **travamento de produção**.

A consulta permite:

- detectar **bloqueios operacionais** causados por ausência de empenho;
- identificar **ordens liberadas que não conseguem consumir material**;
- apoiar ações imediatas de **PCP, almoxarifado e produção**;
- analisar situações por **filial, CT e data específica**.

---

#### 🧱 Tabelas envolvidas

##### SD4010 — Empenhos de Componentes

| Coluna      | Descrição |
|------------|-----------|
| D4_OP      | Ordem de produção |
| D4_PRODUTO | Código do componente |
| D4_OPERAC  | Operação da OP |
| D4_QUANT   | Quantidade empenhada |
| D4_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SC2010 — Ordens de Produção

| Coluna      | Descrição |
|------------|-----------|
| C2_OP      | Ordem de produção |
| C2_PRIOR   | Prioridade da OP |
| C2_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código do produto |
| B1_DESC    | Descrição do produto |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SH8010 — Operações Alocadas

| Coluna      | Descrição |
|------------|-----------|
| H8_OP      | Ordem de produção |
| H8_OPER    | Operação |
| H8_CTRAB   | Centro de Trabalho |
| H8_DTINI   | Data de início da operação |
| H8_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Componentes **sem empenho registrado**  
  - `D4_QUANT = 0`

- Centro de Trabalho específico  
  - `H8_CTRAB = :CT`

- Data de execução da operação  
  - `H8_DTINI = :DATA`

- Apenas OPs com prioridade **Livre**  
  - `C2_PRIOR = '500'`

- Filial específica  
  - `:FILIAL`

- Considerar somente registros ativos  
  - `SD4010.D_E_L_E_T_ = ''`  
  - `SC2010.D_E_L_E_T_ = ''`  
  - `SB1010.D_E_L_E_T_ = ''`  
  - `SH8010.D_E_L_E_T_ = ''`

---

#### 💾 Consulta

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
---

### 7. Usuário: **“Identificar ordens finalizadas sem consumo de componentes”**

#### 🎯 Objetivo

Identificar **ordens de produção finalizadas** que **não apresentaram consumo de componentes**, caracterizando uma **inconsistência produtiva ou de apontamento**, uma vez que houve produção concluída sem baixa de material.

A consulta permite:

- detectar **falhas de apontamento ou empenho**;
- identificar **ordens encerradas indevidamente**;
- apoiar auditorias de **produção, estoque e custos**;
- isolar casos por **CT, filial e data específica**.

---

#### 🧱 Tabelas envolvidas

##### SC2010 — Ordens de Produção

| Coluna      | Descrição |
|------------|-----------|
| C2_OP      | Número da ordem de produção |
| C2_PRODUTO | Código do produto produzido |
| C2_QUANT   | Quantidade planejada |
| C2_QUJE    | Quantidade efetivamente produzida |
| C2_PRIOR   | Prioridade da OP |
| C2_FILIAL  | Filial da OP |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SD4010 — Empenhos / Consumo de Componentes

| Coluna      | Descrição |
|------------|-----------|
| D4_OP      | Ordem de produção |
| D4_OPERAC  | Operação da OP |
| D4_COD     | Código do componente |
| D4_QUANT   | Quantidade consumida |
| D4_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código do produto |
| B1_DESC    | Descrição do produto |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SH8010 — Operações Alocadas

| Coluna      | Descrição |
|------------|-----------|
| H8_OP      | Ordem de produção |
| H8_OPER    | Operação |
| H8_CTRAB   | Centro de Trabalho |
| H8_DTINI   | Data de início da operação |
| H8_FILIAL  | Filial |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Ordem de produção **finalizada**  
  - `C2_QUANT = C2_QUJE`

- **Sem consumo de componentes**  
  - `SUM(D4_QUANT) = 0`

- Centro de Trabalho específico  
  - `H8_CTRAB = :CT`

- Data de execução da operação  
  - `H8_DTINI = :DATA`

- Apenas OPs com prioridade **Livre**  
  - `C2_PRIOR = '500'`

- Filial específica  
  - `C2_FILIAL = :FILIAL`

- Considerar somente registros ativos  
  - `SC2010.D_E_L_E_T_ = ''`  
  - `SD4010.D_E_L_E_T_ = ''`  
  - `SB1010.D_E_L_E_T_ = ''`  
  - `SH8010.D_E_L_E_T_ = ''`

---

#### 💾 Consulta

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

---

### 8. Usuário: **"Média de tempo por CT (H8_HRINI → H8_HRFIM)"**

#### 🧱 Tabelas envolvidas

-   SC2010 — Ordens de Produção
-   SD4010 — Empenhos
-   SH8010 — Operações

#### ⚙️ Condições aplicadas

-   Apenas ordens finalizadas (C2_QUANT = C2_QUJE)
-   Agrupar por H8_CTRAB
-   C2_PRIOR = 500
-   Filial = 01
-   H8_DTINI = hoje
-   H8_HRFIM IS NOT NULL
-   H8_HRINI IS NOT NULL
-   Registros ativos

#### 💾 Consulta

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

---

### 9. Usuário: **“Estoque total por filial/local, Grupo 1008 – Descrição TERM. BANDEIRA”**


#### 🎯 Objetivo

Apurar o **estoque total disponível** de produtos do **grupo 1008 (terminais)** cuja **descrição contenha o texto “TERM. BANDEIRA”**, com os resultados **agrupados por filial e local de estoque**.

A consulta tem como finalidade:

- fornecer uma **visão consolidada de estoque físico**;
- permitir análise por **filial e local**;
- apoiar decisões de **produção, abastecimento e balanceamento de estoque**;
- garantir que apenas **produtos válidos e ativos** sejam considerados.

---

#### 🧱 Tabelas envolvidas

##### SB2010 — Estoque por Produto / Local

| Coluna      | Descrição |
|------------|-----------|
| B2_FILIAL  | Filial do estoque |
| B2_LOCAL   | Local de armazenagem |
| B2_COD     | Código do produto |
| B2_QATU    | Quantidade atual em estoque |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código do produto |
| B1_DESC    | Descrição do produto |
| B1_GRUPO   | Grupo do produto |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Considerar somente **produtos ativos**  
  - `SB1010.D_E_L_E_T_ = ''`

- Considerar somente **saldos de estoque ativos**  
  - `SB2010.D_E_L_E_T_ = ''`

- Filtrar produtos do **grupo 1008 (terminais)**  
  - `SB1010.B1_GRUPO = '1008'`

- Filtrar descrição contendo **TERM. BANDEIRA**  
  - `SB1010.B1_DESC LIKE '%TERM. BANDEIRA%'`

- Consolidação de estoque por:  
  - Filial (`B2_FILIAL`)  
  - Local (`B2_LOCAL`)  
  - Produto (`B2_COD`)

---

#### 💾 Consulta

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
    AND P.B1_GRUPO = '1008'
    AND P.B1_DESC LIKE '%TERM. BANDEIRA%'
ORDER BY
    P.B1_COD ASC;
```
---

### 10. Usuário: **“Buscar produtos do grupo 1050 com descrição contendo COMP e unidade diferente de peça”**

---

#### 🎯 Objetivo

Identificar **produtos cadastrados no grupo 1050** cuja **descrição contenha o termo “COMP”** e cuja **unidade de medida seja diferente de peça (PC)**.

A consulta tem como finalidade:

- detectar **inconsistências de cadastro** de unidade de medida;
- apoiar **saneamento e padronização** do cadastro de produtos;
- permitir análise objetiva de itens do grupo 1050 que **não seguem o padrão esperado de unidade**.

---

#### 🧱 Tabelas envolvidas

##### SB1010 — Cadastro de Produtos

> Fonte única necessária para a consulta.

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código interno do produto |
| B1_DESC    | Descrição do produto |
| B1_GRUPO   | Grupo do produto |
| B1_UM      | Unidade de medida |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Grupo do produto igual a **1050**  
  - `B1_GRUPO = '1050'`

- Descrição do produto contendo o texto **COMP**  
  - `B1_DESC LIKE '%COMP%'`

- Unidade de medida diferente de **peça (PC)**  
  - `B1_UM <> 'PC'`

- Considerar somente registros ativos  
  - `SB1010.D_E_L_E_T_ = ''`

---

#### 💾 Consulta

```sql
SELECT
    B1_COD   AS COD_PRODUTO,
    B1_DESC  AS DESCRICAO_PRODUTO,
    B1_GRUPO AS GRUPO,
    B1_UM    AS UNIDADE
FROM SB1010
WHERE
        D_E_L_E_T_ = ''
    AND B1_GRUPO = '1050'
    AND B1_DESC LIKE '%COMP%'
    AND B1_UM <> 'PC'
ORDER BY
    B1_COD;
```
---

### 11. Usuário: **"Encontrar produtos com partnumbers duplicados para um fornecedor"**

#### 🎯 Objetivo

Identificar produtos DELPI distintos que compartilham o mesmo **partnumber do fornecedor**, caracterizando duplicidade no relacionamento Produto × Fornecedor.

---

#### 🧱 Tabelas envolvidas

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código interno do produto DELPI |
| B1_DESC    | Descrição do produto |
| D_E_L_E_T_ | Indicador de exclusão lógica do registro |

##### SA5010 — Relacionamento Produto × Fornecedor

| Coluna      | Descrição |
|------------|-----------|
| A5_PRODUTO | Código do produto DELPI |
| A5_FORNECE | Código do fornecedor |
| A5_NOMEFOR | Nome do fornecedor |
| A5_CODPRF  | Partnumber do produto no fornecedor |
| D_E_L_E_T_ | Indicador de exclusão lógica do registro |

---

#### ⚙️ Condições aplicadas

- Fornecedor específico (`A5_FORNECE = '001499'`)
- Considera somente registros ativos  
  - `SB1010.D_E_L_E_T_ = ''`  
  - `SA5010.D_E_L_E_T_ = ''`
- Identificação de partnumbers duplicados  
  - Mesmo `A5_CODPRF` associado a mais de um produto DELPI

---

#### 💾 Consulta

```sql
SELECT
    P.B1_COD     AS COD_PRODUTO,
    P.B1_DESC    AS DESCRICAO_PRODUTO,
    F.A5_FORNECE AS COD_FORNECEDOR,
    F.A5_NOMEFOR AS NOME_FORNECEDOR,
    F.A5_CODPRF  AS PARTNUMBER
FROM SB1010 P
INNER JOIN SA5010 F
    ON F.A5_PRODUTO = P.B1_COD
WHERE
        F.A5_FORNECE =  '001499'
    AND F.D_E_L_E_T_ = ''
    AND P.D_E_L_E_T_ = ''
    AND F.A5_CODPRF IN (
        SELECT
            A5_CODPRF
        FROM SA5010
        WHERE
                A5_FORNECE =  '001499'
            AND D_E_L_E_T_ = ''
        GROUP BY
            A5_CODPRF
        HAVING COUNT(*) > 1
    )
ORDER BY
    F.A5_CODPRF,
    P.B1_COD;
```
---

### 12. Usuário: **“Buscar a última NF válida de um produto, excluindo transportadoras.”**

#### 🎯 Objetivo

Identificar a **última Nota Fiscal de Entrada válida** de um produto DELPI específico, garantindo que:

- o fornecedor seja **real (não transportadora)**;
- fornecedores internos previamente mapeados sejam **explicitamente excluídos**;
- apenas **registros ativos** sejam considerados;
- o resultado represente **a NF mais recente**, considerando critérios cronológicos consistentes.

O objetivo é obter **um único registro confiável por produto**, representando a última compra válida.

---

#### 🧱 Tabelas envolvidas

##### SD1010 — Itens de Notas Fiscais de Entrada

| Coluna        | Descrição |
|--------------|-----------|
| D1_FILIAL    | Filial de lançamento da NF |
| D1_COD       | Código do produto |
| D1_DOC       | Número da Nota Fiscal |
| D1_EMISSAO   | Data de emissão da NF |
| D1_DTDIGIT   | Data de digitação da NF |
| D1_FORNECE   | Código do fornecedor |
| D1_LOJA      | Loja do fornecedor |
| D_E_L_E_T_   | Indicador de exclusão lógica |

---

##### SA2010 — Cadastro de Fornecedores

| Coluna      | Descrição |
|------------|-----------|
| A2_COD     | Código do fornecedor |
| A2_LOJA    | Loja do fornecedor |
| A2_NOME    | Nome do fornecedor |
| A2_CGC     | CNPJ do fornecedor |
| A2_EST     | UF do fornecedor |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SA5010 — Relacionamento Produto × Fornecedor

| Coluna      | Descrição |
|------------|-----------|
| A5_PRODUTO | Código do produto DELPI |
| A5_FORNECE | Código do fornecedor |
| A5_LOJA    | Loja do fornecedor |
| A5_CODPRF  | Partnumber do produto no fornecedor |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Produto específico analisado  
  - `SD1010.D1_COD = '10080001'`

- Considerar somente registros ativos  
  - `SD1010.D_E_L_E_T_ = ''`  
  - `SA2010.D_E_L_E_T_ = ''`  
  - `SA5010.D_E_L_E_T_ = ''`

- Exclusão de fornecedores internos específicos  
  - `D1_FORNECE <> '000019'`  
  - `D1_FORNECE <> '001149'`

- Exclusão de transportadoras  
  - Fornecedor cujo nome contenha “TRANSP” é descartado  
  - `UPPER(SA2010.A2_NOME) NOT LIKE '%TRANSP%'`

- Determinação da última NF válida por produto  
  - Critério de ordenação hierárquico:
    1. Data de emissão (`D1_EMISSAO`)
    2. Data de digitação (`D1_DTDIGIT`)
    3. Número da NF (`D1_DOC`)
  - Uso de `ROW_NUMBER()` particionado por produto
  - Seleção apenas do registro mais recente (`RN = 1`)

---

#### 💾 Consulta

```sql
WITH ULTIMA_NF_PRODUTO AS (
    SELECT
        SD1.D1_FILIAL        AS FILIAL,
        SD1.D1_COD           AS COD_MATERIA_PRIMA,
        A5.A5_CODPRF         AS PARTNUMBER,
        SD1.D1_DOC           AS NF_NUMERO,
        SD1.D1_EMISSAO       AS DATA_EMISSAO,
        SD1.D1_DTDIGIT       AS DATA_DIGITACAO,
        SD1.D1_FORNECE       AS FORNECEDOR_CODIGO,
        SD1.D1_LOJA          AS FORNECEDOR_LOJA,
        SA2.A2_NOME          AS FORNECEDOR_NOME,
        SA2.A2_CGC           AS FORNECEDOR_CNPJ,
        SA2.A2_EST           AS FORNECEDOR_UF,
        ROW_NUMBER() OVER (
            PARTITION BY SD1.D1_COD
            ORDER BY
                SD1.D1_EMISSAO DESC,
                SD1.D1_DTDIGIT DESC,
                SD1.D1_DOC DESC
        ) AS RN
    FROM SD1010 SD1
    INNER JOIN SA2010 SA2
        ON SA2.A2_COD  = SD1.D1_FORNECE
       AND SA2.A2_LOJA = SD1.D1_LOJA
       AND SA2.D_E_L_E_T_ = ''
    LEFT JOIN SA5010 A5
        ON A5.A5_PRODUTO = SD1.D1_COD
       AND A5.A5_FORNECE = SD1.D1_FORNECE
       AND A5.A5_LOJA    = SD1.D1_LOJA
       AND A5.D_E_L_E_T_ = ''
    WHERE
            SD1.D_E_L_E_T_ = ''
        AND SD1.D1_COD = '10080001'
        AND SD1.D1_FORNECE <> '000019'
        AND SD1.D1_FORNECE <> '001149'
        AND UPPER(SA2.A2_NOME) NOT LIKE '%TRANSP%'
)
SELECT
    FILIAL,
    COD_MATERIA_PRIMA,
    PARTNUMBER,
    NF_NUMERO,
    DATA_EMISSAO,
    DATA_DIGITACAO,
    FORNECEDOR_CODIGO,
    FORNECEDOR_LOJA,
    FORNECEDOR_NOME,
    FORNECEDOR_CNPJ,
    FORNECEDOR_UF
FROM ULTIMA_NF_PRODUTO
WHERE RN = 1
ORDER BY COD_MATERIA_PRIMA;
```
---

### 13. Usuário: **“Identificar a quantidade consumida de terminais por CT, agrupada por filial”**

#### 🎯 Objetivo

Identificar a **quantidade efetivamente consumida de terminais (grupo 1008)** em um **Centro de Trabalho (CT) específico**, considerando **apenas produção real comprovada**, com os resultados **agrupados por filial**, dentro de um **período definido**.

A consulta garante que:

- o consumo apurado é **real**, não apenas planejado;
- o CT é validado por **apontamento efetivo de produção**;
- as quantidades **não são infladas** por múltiplos apontamentos;
- os resultados são **comparáveis entre filiais**.

---

#### 🧱 Tabelas envolvidas

##### SD4010 — Empenhos / Consumo de Materiais

| Coluna        | Descrição |
|--------------|-----------|
| D4_FILIAL    | Filial da ordem de produção |
| D4_OP        | Número da OP |
| D4_OPERAC    | Operação da OP |
| D4_COD       | Código do material consumido |
| D4_QTDEORI   | Quantidade originalmente empenhada |
| D4_QUANT     | Quantidade efetivamente baixada |
| D_E_L_E_T_   | Indicador de exclusão lógica |

---

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código do produto |
| B1_DESC    | Descrição do produto |
| B1_GRUPO   | Grupo do produto |
| B1_UM      | Unidade de medida |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

##### SH6010 — Apontamentos de Produção

| Coluna        | Descrição |
|--------------|-----------|
| H6_FILIAL    | Filial do apontamento |
| H6_OP        | Ordem de produção |
| H6_OPERAC   | Operação apontada |
| H6_RECURSO  | Recurso / Centro de Trabalho |
| H6_TIPO     | Tipo de apontamento (P = Produção) |
| H6_DATAINI  | Data de início da execução |
| D_E_L_E_T_  | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- Considerar apenas **terminais**  
  - `SB1010.B1_GRUPO = '1008'`

- Validar apenas **produção real**  
  - `SH6010.H6_TIPO = 'P'`

- Centro de Trabalho específico  
  - `SH6010.H6_RECURSO = 'CT-53'`

- Período de execução real  
  - `SH6010.H6_DATAINI BETWEEN '20250101' AND '20251231'`

- Agrupamento por filial  
  - `SD4010.D4_FILIAL`

- Considerar somente registros ativos  
  - `SD4010.D_E_L_E_T_ = ''`  
  - `SB1010.D_E_L_E_T_ = ''`  
  - `SH6010.D_E_L_E_T_ = ''`

- Validação de execução real por operação  
  - Uso de `EXISTS (SH6010)` para garantir que **cada linha da SD4010 só é considerada se a operação teve produção real no CT e no período informado**

---

#### 📐 Regra de cálculo da quantidade consumida

A quantidade consumida é calculada **exclusivamente a partir da SD4010**, utilizando o critério:

```text
D4_QTDEORI - D4_QUANT
```

Somente valores positivos são considerados, evitando consumo inflado ou registros inconsistentes.

---

#### 💾 Consulta

```sql
SELECT
    SD4.D4_FILIAL        AS FILIAL,
    SD4.D4_COD           AS COD_MATERIAL,
    SB1.B1_DESC          AS DESC_MATERIAL,
    SB1.B1_UM            AS UNIDADE,
    'CT-53'              AS CT,
    SUM(
        CASE
            WHEN SD4.D4_QTDEORI > SD4.D4_QUANT
            THEN SD4.D4_QTDEORI - SD4.D4_QUANT
            ELSE 0
        END
    ) AS QTD_CONSUMIDA
FROM SD4010 SD4
INNER JOIN SB1010 SB1
    ON SB1.B1_COD = SD4.D4_COD
WHERE
    SD4.D_E_L_E_T_ = ''
    AND SB1.D_E_L_E_T_ = ''
    AND SB1.B1_GRUPO = '1008'

    AND EXISTS (
        SELECT 1
        FROM SH6010 SH6
        WHERE
            SH6.D_E_L_E_T_ = ''
            AND SH6.H6_TIPO = 'P'
            AND SH6.H6_FILIAL = SD4.D4_FILIAL
            AND SH6.H6_OP     = SD4.D4_OP
            AND SH6.H6_OPERAC = SD4.D4_OPERAC
            AND SH6.H6_RECURSO = 'CT-53'
            AND SH6.H6_DATAINI BETWEEN '20250101' AND '20251231'
    )
GROUP BY
    SD4.D4_FILIAL,
    SD4.D4_COD,
    SB1.B1_DESC,
    SB1.B1_UM
ORDER BY
    SD4.D4_FILIAL,
    SD4.D4_COD;
```

### 14. Usuário: **“Tempo médio real de consumo de uma matéria prima para o CT-xx (CT específico, sem duplicidade de tempo)”**

---

#### 🎯 Objetivo

Calcular, para cada **matéria prima**, o **tempo médio real de consumo por unidade**, utilizando **dados reais de produção**, considerando:

- apenas **apontamentos de produção válidos** (`H6_TIPO = 'P'`);
- um **Centro de Trabalho (CT) específico**;
- uma **faixa de datas definida**;
- a **quantidade real consumida** de cada matéria prima;
- a **eliminação de duplicidade de tempo**, consolidando todos os apontamentos pertencentes à mesma **OP + operação**.

O resultado é um indicador **ponderado pelo volume real produzido**, tecnicamente consistente, adequado para análise de desempenho produtivo e engenharia de tempos.

---

#### 🧱 Tabelas envolvidas

##### SH6010 — Apontamentos de Produção

| Coluna        | Descrição |
|--------------|-----------|
| H6_FILIAL    | Filial do apontamento |
| H6_OP        | Ordem de produção |
| H6_OPERAC   | Operação da OP |
| H6_RECURSO  | Recurso / Centro de Trabalho |
| H6_TIPO     | Tipo de apontamento (P = Produção) |
| H6_DATAINI  | Data de início da execução |
| H6_DATAFIN  | Data de término da execução |
| H6_HORAINI  | Hora de início |
| H6_HORAFIN  | Hora de término |
| D_E_L_E_T_  | Indicador de exclusão lógica |

---

##### SD4010 — Consumo de Materiais

| Coluna        | Descrição |
|--------------|-----------|
| D4_FILIAL    | Filial da OP |
| D4_OP        | Ordem de produção |
| D4_OPERAC   | Operação da OP |
| D4_COD       | Código do material consumido |
| D4_QTDEORI  | Quantidade originalmente empenhada |
| D4_QUANT    | Quantidade efetivamente baixada |
| D_E_L_E_T_  | Indicador de exclusão lógica |

---

##### SB1010 — Cadastro de Produtos

| Coluna      | Descrição |
|------------|-----------|
| B1_COD     | Código do produto |
| B1_DESC    | Descrição do produto |
| B1_GRUPO   | Grupo do produto |
| B1_UM      | Unidade de medida |
| D_E_L_E_T_ | Indicador de exclusão lógica |

---

#### ⚙️ Condições aplicadas

- **SH6010 — Apontamentos de Produção**
  - Somente registros ativos: `D_E_L_E_T_ = ''`
  - Apenas produção real: `H6_TIPO = 'P'`
  - Centro de Trabalho específico: `H6_RECURSO = :CT`
  - Período de execução real: `H6_DATAINI BETWEEN :DATA_INICIO AND :DATA_FIM`
  - Apontamentos completos:
    - `H6_DATAFIN IS NOT NULL`
    - `H6_HORAINI <> ''`
    - `H6_HORAFIN <> ''`
  - **Consolidação do tempo** por:
    - Filial
    - OP
    - Operação
    - CT

- **SD4010 — Consumo de Terminais**
  - Somente registros ativos: `D_E_L_E_T_ = ''`
  - Quantidade real consumida calculada como:
    - `D4_QTDEORI - D4_QUANT` (quando positiva)
  - Agrupamento por:
    - Filial
    - OP
    - Operação
    - Código do material

- **SB1010 — Cadastro de Produto**
  - Somente registros ativos: `D_E_L_E_T_ = ''`
  - Apenas terminais: `B1_GRUPO = :GRUPO`

---

#### 🧮 Equações envolvidas

- **⏱️ Tempo total consolidado por OP + operação**

Para cada OP \(i\) e operação \(j\):

\[
T_{i,j} = \sum (DataHoraFim_{i,j} - DataHoraInicio_{i,j})
\]

> A soma elimina duplicidades causadas por múltiplos apontamentos na SH6010.

---

- **📦 Quantidade real consumida da matéria prima**

Para cada matéria prima \(t\), OP \(i\) e operação \(j\):

\[
Q_{i,j,t} = \sum
\begin{cases}
D4\_QTDEORI - D4\_QUANT, & \text{se } D4\_QTDEORI > D4\_QUANT \\
0, & \text{caso contrário}
\end{cases}
\]

---

#### ⏱️ Tempo médio real por materia prima (ponderado)

Para cada materia prima \(t\):

\[
\boxed{
TempoMédio_t = \frac{\sum T_{i,j}}{\sum Q_{i,j,t}}
}
\]

- Unidade: **segundos por peça**
- Tempo **ponderado pelo volume real consumido**
- Não se trata de média simples por OP

---

#### 💾 Consulta

```sql
DECLARE @CT VARCHAR(20);
DECLARE @GRUPO VARCHAR(20);
DECLARE @DATA_INICIO VARCHAR(20);
DECLARE @DATA_FIM VARCHAR(20);

SET @CT = 'CT-33A';
SET @GRUPO = '1007';
SET @DATA_INICIO = '20250101';
SET @DATA_FIM = '20251231';

WITH SH6_CONSOLIDADO AS (
    SELECT
        H6_FILIAL,
        H6_OP,
        H6_OPERAC,
        H6_RECURSO,
        -- Tempo TOTAL por OP + operação (elimina duplicidade)
        SUM(
            DATEDIFF(
                SECOND,
                CAST(CONVERT(char(8), H6_DATAINI, 112) + ' ' + H6_HORAINI AS datetime),
                CAST(CONVERT(char(8), H6_DATAFIN, 112) + ' ' + H6_HORAFIN AS datetime)
            )
        ) AS TEMPO_OP_SEG
    FROM SH6010
    WHERE
        D_E_L_E_T_ = ''
        AND H6_TIPO = 'P'
        AND H6_RECURSO = @CT
        AND H6_DATAINI BETWEEN @DATA_INICIO AND @DATA_FIM
        AND H6_DATAFIN IS NOT NULL
        AND H6_HORAINI <> ''
        AND H6_HORAFIN <> ''
    GROUP BY
        H6_FILIAL,
        H6_OP,
        H6_OPERAC,
        H6_RECURSO
),

CONSUMO AS (
    SELECT
        SD4.D4_FILIAL,
        SD4.D4_OP,
        SD4.D4_OPERAC,
        SD4.D4_COD,
        -- Quantidade REAL consumida
        SUM(
            CASE
                WHEN SD4.D4_QTDEORI > SD4.D4_QUANT
                THEN SD4.D4_QTDEORI - SD4.D4_QUANT
                ELSE 0
            END
        ) AS QTD_CONSUMIDA
    FROM SD4010 SD4
    WHERE
        SD4.D_E_L_E_T_ = ''
    GROUP BY
        SD4.D4_FILIAL,
        SD4.D4_OP,
        SD4.D4_OPERAC,
        SD4.D4_COD
)
SELECT
    SH6.H6_FILIAL AS FILIAL,
    SB1.B1_COD   AS CODIGO,
    SB1.B1_DESC  AS DESCRICAO,
    SB1.B1_UM    AS UNIDADE,
    SH6.H6_RECURSO AS CT,
    -- Quantidade total REAL no período / CT
    SUM(C.QTD_CONSUMIDA) AS QTD_TOTAL_MP,
    -- Tempo total REAL (sem duplicidade)
    SUM(SH6.TEMPO_OP_SEG) AS TEMPO_TOTAL_SEG,
    -- Tempo médio REAL por peça (ponderado)
    SUM(SH6.TEMPO_OP_SEG) * 1.0
    / NULLIF(SUM(C.QTD_CONSUMIDA), 0)
    AS TEMPO_MEDIO_SEG_POR_PECA
FROM SH6_CONSOLIDADO SH6
INNER JOIN CONSUMO C
    ON C.D4_FILIAL = SH6.H6_FILIAL
   AND C.D4_OP     = SH6.H6_OP
   AND C.D4_OPERAC = SH6.H6_OPERAC
INNER JOIN SB1010 SB1
    ON SB1.B1_COD   = C.D4_COD
   AND SB1.B1_GRUPO = @GRUPO
   AND SB1.D_E_L_E_T_ = ''
WHERE
    C.QTD_CONSUMIDA > 0
GROUP BY
    SH6.H6_FILIAL,
    SB1.B1_COD,
    SB1.B1_DESC,
    SB1.B1_UM,
    SH6.H6_RECURSO
ORDER BY
    SH6.H6_FILIAL,
    SB1.B1_COD,
    TEMPO_MEDIO_SEG_POR_PECA;
```

---

### 15. Usuário: **"Buscar produtos com descrição duplicada (Matéria-Prima)."**

#### 🎯 Objetivo

Identificar **produtos do tipo Matéria-Prima (MP)** cadastrados no
Protheus que compartilham **a mesma descrição (`B1_DESC`)**,
caracterizando **duplicidade de cadastro**, garantindo que:

-   apenas **produtos ativos** sejam considerados;
-   o escopo seja **restrito a MP**;
-   a duplicidade seja determinada **exclusivamente pela descrição
    textual**;
-   todos os **códigos envolvidos** em cada descrição duplicada sejam
    retornados;
-   seja possível **quantificar o grau de duplicidade** por descrição.

O objetivo é **detectar inconsistências de cadastro**, apoiar
**saneamento de dados** e **prevenir riscos operacionais**.

---

#### 🧱 Tabelas envolvidas

##### SB1010 --- Cadastro de Produtos

  Coluna          | Descrição
  --------------- | ----------------------
  B1_COD          | Código do produto
  B1_DESC         | Descrição do produto
  B1_TIPO         | Tipo do produto
  D_E\_L_E\_T\_   | Exclusão lógica

---

#### ⚙️ Condições aplicadas

-   Somente produtos ativos
    -   `D_E_L_E_T_ = ''`
-   Somente Matéria-Prima
    -   `B1_TIPO = 'MP'`
-   Identificação de duplicidade
    -   Agrupamento por `B1_DESC`
    -   `HAVING COUNT(*) > 1`

---

#### 💾 Consulta

``` sql
WITH descricoes_duplicadas AS (
    SELECT
        B1_DESC,
        COUNT(*) AS QTD
    FROM SB1010
    WHERE
        D_E_L_E_T_ = ''
        AND B1_TIPO = 'MP'
    GROUP BY
        B1_DESC
    HAVING COUNT(*) > 1
)
SELECT
    P.B1_COD   AS COD_PRODUTO,
    P.B1_DESC  AS DESCRICAO,
    D.QTD      AS QTD_PRODUTOS_COM_MESMA_DESCRICAO
FROM SB1010 P
INNER JOIN descricoes_duplicadas D
    ON D.B1_DESC = P.B1_DESC
WHERE
    P.D_E_L_E_T_ = ''
    AND P.B1_TIPO = 'MP'
ORDER BY
    D.QTD DESC,
    P.B1_DESC,
    P.B1_COD;
```