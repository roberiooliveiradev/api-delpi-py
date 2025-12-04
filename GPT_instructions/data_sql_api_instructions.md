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

> A rota `/data/sql` **não aceita texto puro** (`text/plain`).
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
