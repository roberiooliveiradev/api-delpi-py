# ⚙️ Guia de Uso — System API

## 📘 Descrição
A API **System** permite **explorar a estrutura de tabelas e colunas** do banco do Protheus.  
Ideal para descoberta de metadados (ex: tabelas SB1010, SB2010, SG1010).

---

## ⚙️ Endpoints

| Método | Endpoint | Descrição |
|---------|-----------|------------|
| `GET` | `/system/tables` | Lista tabelas com paginação |
| `GET` | `/system/tables/{tableName}` | Detalha as colunas e descrições da tabela |

---

## 🔍 Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|------------|------|---------|------------|
| `page` | int | 1 | Número da página |
| `limit` | int | 50 | Quantidade de tabelas por página |
| `tableName` | str | — | Nome exato da tabela (ex: `SB1010`) |

---

## 🧩 Exemplo de uso

### 🔹 1. Listar tabelas
```http
GET /system/tables?page=1&limit=20
```
**Resposta:**
```json
{
  "success": true,
  "message": "Listagem paginada realizada com sucesso!",
  "data": {
    "page": 1,
    "limit": 20,
    "results": [
      { "TableName": "SB1010", "Description": "Cadastro de produtos" },
      { "TableName": "SB2010", "Description": "Saldos de estoque" }
    ]
  }
}
```

---

### 🔹 2. Listar colunas de uma tabela
```http
GET /system/tables/SB1010
```
**Resposta:**
```json
{
  "success": true,
  "message": "Tabela localizada com sucesso!",
  "data": [
    { "ColumnName": "B1_COD", "Description": "Código do produto" },
    { "ColumnName": "B1_DESC", "Description": "Descrição" },
    { "ColumnName": "B1_GRUPO", "Description": "Grupo de produto" }
  ]
}
```

---

## 🧠 Dicas para o agente GPT

- Use `/system/tables` para **descobrir nomes de tabelas disponíveis**.  
- Use `/system/tables/{tableName}` para **entender as colunas** antes de montar consultas com `/data/query`.  
- Sempre validar se a tabela possui `D_E_L_E_T_` antes de criar filtros.  
- Utilize paginação (`page`, `limit`) para evitar consultas pesadas.
