# 🧩 Guia de Uso — Product API

## 📘 Descrição

A API **Product** fornece acesso aos dados de produtos e suas relações no **Protheus**, incluindo:

-   Consulta de produtos (`SB1010`)
-   Estrutura (BOM) e hierarquia de componentes (`SG1010`)
-   Relação inversa (Where Used — pais)
-   Controle de paginação e profundidade (`max_depth`)

---

## ⚙️ Endpoints

| Método | Endpoint                                  | Descrição                                                     |
| ------ | ----------------------------------------- | ------------------------------------------------------------- |
| `GET`  | `/products/`                              | Lista produtos com limite definido                            |
| `GET`  | `/products/search/description`            | Busca avançada por descrição com score                        |
| `GET`  | `/products/search`                        | Pesquisa produto específico por código, descrição ou grupo    |
| `GET`  | `/products/{code}`                        | Consulta produto específico                                   |
| `GET`  | `/products/{code}/structure`              | Estrutura do produto (componentes) via CTE                    |
| `GET`  | `/products/{code}/parents`                | Produtos que utilizam o item (pais) via CTE                   |
| `GET`  | `/products/{code}/suppliers`              | Lista fornecedores de um produto                              |
| `GET`  | `/products/{code}/inbound-invoice-items`  | Notas fiscais de entrada do item                              |
| `GET`  | `/products/{code}/outbound-invoice-items` | Notas fiscais de saída do item                                |
| `GET`  | `/products/{code}/stock`                  | Consulta estoque com filtros e paginação                      |
| `GET`  | `/products/{code}/guide`                  | Roteiro de produção (SG2010) com opção de incluir componentes |

---

## 🔍 Parâmetros

| Parâmetro   | Tipo | Padrão | Descrição                                      |
| ----------- | ---- | ------ | ---------------------------------------------- |
| `limit`     | int  | 50     | Limite de registros retornados em `/products/` |
| `code`      | str  | —      | Código do produto (`B1_COD`)                   |
| `max_depth` | int  | 10     | Profundidade máxima da recursão                |
| `page`      | int  | 1      | Página atual                                   |
| `page_size` | int  | 100    | Registros por página (máx: 500)                |
| `branch`    | str  | None   | Filial para filtro                             |
| `location`  | str  | None   | Local de estoque                               |

---

## 🧩 Exemplo de Requisição

### 🔹 1. Listar produtos

```http
GET /products?limit=20
```

**Resposta:**

```json
{
    "success": true,
    "message": "Listagem realizada com sucesso!",
    "data": {
        "total": 20,
        "produtos": [
            {
                "B1_COD": "10080522",
                "B1_DESC": "TERMINAL BANDEIRA",
                "B1_GRUPO": "1008"
            }
        ]
    }
}
```

---

### 🔍 2. Nova Rota — Busca Avançada por Descrição

#### **GET /products/search/description**

Busca produtos pela descrição utilizando:

-   frase completa
-   termos separados
-   ranking inteligente por relevância
-   peso baseado na posição do termo
-   similaridade normalizada por tamanho
-   paginação

---

#### 📌 Parâmetros

| Nome          | Tipo   | Obrigatório | Descrição                                   |
| ------------- | ------ | ----------- | ------------------------------------------- |
| `description` | string | ✔           | Texto da busca                              |
| `page`        | int    | ✖           | Página (default: 1)                         |
| `page_size`   | int    | ✖           | Registros por página (default: 50, max 500) |

---

#### 🧠 Ranking Inteligente (Score)

O ranking é um ponto chave da rota. Ele utiliza os seguintes pesos:

---

##### 🟦 1. Frase completa

```
+50 pontos
```

---

##### 🟦 2. Localização da palavra (1 termo)

| Regra                                   | Score |
| --------------------------------------- | ----- |
| início da descrição (`TERM %`)          | +30   |
| início de palavra (`% TERM %`)          | +20   |
| presente em qualquer posição (`%TERM%`) | +10   |

---

##### 🟩 3. Múltiplos termos

| Regra                            | Score |
| -------------------------------- | ----- |
| termo no início                  | +25   |
| termo iniciando palavra          | +15   |
| termo presente em qualquer lugar | +5    |

---

##### 🟧 4. Similaridade normalizada de tamanho

Pontuação entre **0 e 10**, calculada por:

-   distância entre o tamanho da descrição e o tamanho da busca
-   normalização para evitar favorecer descrições muito longas
-   CAST para `INT` para evitar erros de JSON (`Decimal`)

---

#### 🔎 Exemplo de requisição

```http
GET /products/search/description?description=TERM BANDEIRA&page=1&page_size=5
```

---

#### 🔎 Exemplo de resposta

```json
{
    "success": true,
    "message": "Busca por descrição realizada com sucesso.",
    "data": {
        "page": 1,
        "pageSize": 5,
        "total": 56,
        "totalPages": 12,
        "description": "TERM BANDEIRA",
        "results": [
            {
                "B1_COD": "10081501",
                "B1_DESC": "TERM. BANDEIRA 6,3X0,8...",
                "relevance_score": 47
            }
        ]
    }
}
```

---

### 🔹 3. Pesquisa de Produtos

A rota permite realizar uma busca inteligente em produtos do Protheus, utilizando:

-   Código (B1_COD)

-   Descrição completa (B1_DESC)

-   Termos individuais da descrição

-   Grupo (B1_GRUPO)

-   Ordenação automática por relevância

-   Paginação

#### 🔎 Como a busca funciona

Ao informar o parâmetro description, a API realiza:

**Exemplo de pedido:**

-   "Liste 5 exemplos de terminais bandeira."

```http
GET /products/search?page=1&page_size=5&description=TERM BANDEIRA
```

1.  Busca pela frase completa

```sql
B1_DESC LIKE '%TERM BANDEIRA%'
```

2.  Busca pelos termos individuais

Exemplo: "terminal bandeira" →

```sql
B1_DESC LIKE '%TERM%'
OR B1_DESC LIKE '%BANDEIRA%'
```

3. Ranking automático de relevância

O resultado é ordenado por um score que considera:

| Critério                             | Pontos      |
| ------------------------------------ | ----------- |
| Combina a frase completa             | **+50**     |
| Cada termo encontrado                | **+10**     |
| Similaridade do tamanho da descrição | **0 a +10** |

4. Ordenação final

```sql
ORDER BY relevance_score DESC, B1_COD
```

#### 📘 Exemplo de requisição

```http
GET /products/search?page=1&page_size=50&code=100&description=TERM. BANDEIRA&group=1008
```

| Parâmetro     | Tipo | Obrigatório | Descrição                                         |
| ------------- | ---- | ----------- | ------------------------------------------------- |
| `page`        | int  | ✖           | Página atual (default: 1)                         |
| `page_size`   | int  | ✖           | Registros por página (default: 50, máx: 500)      |
| `code`        | str  | ✖           | Pesquisa por código (`B1_COD LIKE '%valor%'`)     |
| `description` | str  | ✖           | Pesquisa por descrição (`B1_DESC LIKE '%valor%'`) |
| `group`       | str  | ✖           | Filtro por grupo (`B1_GRUPO`)                     |

**Exemplo de requisição**

```http
GET /products/search?page=1&page_size=20&description=terminal
```

**Resposta:**

```json
{
    "success": true,
    "message": "Pesquisa de produtos realizada com sucesso (página 1/3).",
    "data": {
        "total": 58,
        "page": 1,
        "pageSize": 20,
        "totalPages": 3,
        "filters": {
            "code": null,
            "description": "terminal",
            "group": null
        },
        "data": [
            {
                "B1_COD": "10080522",
                "B1_DESC": "TERMINAL BANDEIRA 6,30X0,80MM2",
                "B1_GRUPO": "1008",
                "B1_UM": "UN",
                "B1_TIPO": "PA"
            }
        ]
    }
}
```

---

### 🔹 4. Consultar produto específico

```http
GET /products/10080522
```

**Resposta:**

```json
{
    "success": true,
    "message": "Produto localizado com sucesso!",
    "data": {
        "produto": {
            "B1_COD": "10080522",
            "B1_DESC": "TERMINAL BANDEIRA 6,30X0,80MM2",
            "B1_GRUPO": "1008"
        }
    }
}
```

---

### 🔹 5. Estrutura do produto (BOM)

```http
GET /products/10080522/structure?max_depth=10&page=1&page_size=50
```

**Resposta:**

```json
{
    "success": true,
    "message": "Estrutura do produto 10080522 retornada com sucesso (página 1/3).",
    "data": {
        "total": 120,
        "page": 1,
        "pageSize": 50,
        "data": {
            "code": "10080522",
            "description": "TERMINAL BANDEIRA",
            "components": [
                {
                    "code": "20010001",
                    "description": "COMPONENTE FITA",
                    "quantity": 2,
                    "components": []
                }
            ]
        }
    }
}
```

---

### 🔹 6. Produtos pais (Where Used)

```http
GET /products/20010001/parents?max_depth=5&page=1&page_size=50
```

**Resposta:**

```json
{
    "success": true,
    "message": "Produtos pai de 20010001 retornados com sucesso (página 1/1).",
    "data": {
        "total": 15,
        "page": 1,
        "data": {
            "code": "20010001",
            "description": "COMPONENTE FITA",
            "components": [
                {
                    "code": "10080522",
                    "description": "TERMINAL BANDEIRA",
                    "quantity": 2
                }
            ]
        }
    }
}
```

---

### 🔹 7. Notas Fiscais de Entrada (Inbound)

```http
GET /products/{code}/inbound-invoice-items?page=1&page_size=50&issue_date_start=2024-01-01&issue_date_end=2024-12-31&supplier=000001&branch=01
```

| Parâmetro          | Tipo | Obrigatório | Descrição                                    |
| ------------------ | ---- | ----------- | -------------------------------------------- |
| `code`             | str  | ✔           | Código do produto (`D1_COD`)                 |
| `page`             | int  | ✖           | Página (default: 1)                          |
| `page_size`        | int  | ✖           | Registros por página (default: 50, máx: 500) |
| `issue_date_start` | str  | ✖           | Data inicial de emissão (`YYYY-MM-DD`)       |
| `issue_date_end`   | str  | ✖           | Data final de emissão (`YYYY-MM-DD`)         |
| `supplier`         | str  | ✖           | Código do fornecedor (`D1_FORNECE`)          |
| `branch`           | str  | ✖           | Filial (`D1_FILIAL`)                         |

**Resposta:**

```json
{
    "success": true,
    "message": "Inbound invoices for 10080522 fetched successfully (page 1/2).",
    "data": {
        "total": 73,
        "page": 1,
        "pageSize": 50,
        "totalPages": 2,
        "filters": {
            "issue_date_start": "20240101",
            "issue_date_end": "20241231",
            "supplier": "000001",
            "branch": "01"
        },
        "data": [
            {
                "D1_FILIAL": "01",
                "D1_DOC": "12345",
                "D1_SERIE": "1",
                "D1_FORNECE": "000001",
                "supplier_name": "FORNECEDOR TESTE",
                "D1_COD": "10080522",
                "D1_QUANT": 150,
                "D1_EMISSAO": "20240105",
                "D1_LOCAL": "01"
            }
        ]
    }
}
```

---

### 🔹 8. Notas Fiscais de Saída (Outbound)

```http
GET /products/{code}/outbound-invoice-items?page=1&page_size=50&issue_date_start=2024-01-01&issue_date_end=2024-12-31&customer=000001&branch=01
```

| Parâmetro          | Tipo | Obrigatório | Descrição                                    |
| ------------------ | ---- | ----------- | -------------------------------------------- |
| `code`             | str  | ✔           | Código do produto (`D2_COD`)                 |
| `page`             | int  | ✖           | Página (default: 1)                          |
| `page_size`        | int  | ✖           | Registros por página (default: 50, máx: 500) |
| `issue_date_start` | str  | ✖           | Data inicial de emissão (`YYYY-MM-DD`)       |
| `issue_date_end`   | str  | ✖           | Data final de emissão (`YYYY-MM-DD`)         |
| `customer`         | str  | ✖           | Código do cliente (`D2_CLIENTE`)             |
| `branch`           | str  | ✖           | Filial (`D2_FILIAL`)                         |

**Resposta:**

```json
{
    "success": true,
    "message": "Outbound invoices for 10080522 fetched successfully (page 1/3).",
    "data": {
        "total": 120,
        "page": 1,
        "pageSize": 50,
        "totalPages": 3,
        "filters": {
            "issue_date_start": "20240101",
            "issue_date_end": "20241231",
            "customer": "000001",
            "branch": "01"
        },
        "data": [
            {
                "D2_FILIAL": "01",
                "D2_DOC": "98765",
                "D2_SERIE": "1",
                "D2_CLIENTE": "000001",
                "customer_name": "CLIENTE TESTE",
                "D2_COD": "10080522",
                "D2_QUANT": 75,
                "D2_EMISSAO": "20240210",
                "D2_LOCAL": "01"
            }
        ]
    }
}
```

---

### 🔹 9. Estoque

```http
GET /products/{code}/stock?page=1&page_size=50&branch=01&location=01
```

| Parâmetro   | Tipo | Obrigatório | Descrição                          |
| ----------- | ---- | ----------- | ---------------------------------- |
| `code`      | str  | ✔           | Código do produto (B2_COD)         |
| `page`      | int  | ✖           | Página (default: 1)                |
| `page_size` | int  | ✖           | Registros por página (default: 50) |
| `branch`    | str  | ✖           | Filial (`B2_FILIAL`)               |
| `location`  | str  | ✖           | Local (`B2_LOCAL`)                 |

**Resposta:**

```json
{
    "success": true,
    "message": "Estoque de 10080522 retornado com sucesso (página 1/1).",
    "data": {
        "total": 2,
        "page": 1,
        "pageSize": 50,
        "totalPages": 1,
        "filters": {
            "branch": "01",
            "location": "01"
        },
        "data": [
            {
                "B2_FILIAL": "01",
                "B2_LOCAL": "01",
                "B2_COD": "10080522",
                "B2_QATU": 1500,
                "B2_QEMP": 0,
                "B2_QPEDI": 0,
                "B2_SEGUM": "UN",
                "B2_QTREC": 0
            }
        ]
    }
}
```

---

### 🔹 10. Roteiro de Produção (Guide)

Consulta o roteiro de produção do item na tabela **SG2010**.  
Pode retornar apenas o roteiro do produto principal ou incluir também o roteiro de todos os seus componentes, utilizando a árvore de estrutura (BOM — SG1010).

```http
GET /products/{code}/guide?page=1&page_size=50&branch=01&include_components=true&max_depth=10
```

| Parâmetro            | Tipo | Obrigatório | Descrição                                                              |
| -------------------- | ---- | ----------- | ---------------------------------------------------------------------- |
| `code`               | str  | ✔           | Código do produto (`G2_PRODUTO`)                                       |
| `page`               | int  | ✖           | Página atual (default: 1)                                              |
| `page_size`          | int  | ✖           | Registros por página (default: 50, máx: 500)                           |
| `branch`             | str  | ✖           | Filial (`G2_FILIAL`)                                                   |
| `include_components` | bool | ✖           | Se `true`, retorna o roteiro do produto **e de todos os componentes**  |
| `max_depth`          | int  | ✖           | Profundidade da estrutura ao buscar componentes (default: 10, máx: 50) |

#### 🧠 Comportamento da rota

-   include_components = false → retorna apenas o roteiro do produto informado

-   include_components = true →

        -   monta a árvore da estrutura (CTE recursiva SG1010)

        -   identifica componentes até max_depth

        -   retorna todos os roteiros encontrados em SG2010

        -   adiciona o campo bomLevel, indicando o nível dentro da árvore

        -   ordenação automática por:

            ```sql
            bomLevel ASC,
            G2_PRODUTO ASC,
            G2_OPER ASC
            ```

**📘 Exemplo de requisição**

```http
GET /products/10080522/guide?include_components=true&page=1&page_size=20
```

**📘 Exemplo de resposta**

```json
{
    "success": true,
    "message": "Roteiro de produção retornado com sucesso (página 1/3).",
    "data": {
        "total": 54,
        "page": 1,
        "pageSize": 20,
        "totalPages": 3,
        "filters": {
            "branch": "01",
            "include_components": true,
            "max_depth": 10
        },
        "data": [
            {
                "G2_FILIAL": "01",
                "G2_PRODUTO": "10080522",
                "G2_OPER": "010",
                "G2_RECURSO": "PRENSA1",
                "G2_TEMPO": 12.5,
                "bomLevel": 0
            },
            {
                "G2_FILIAL": "01",
                "G2_PRODUTO": "20010001",
                "G2_OPER": "020",
                "G2_RECURSO": "MONT1",
                "G2_TEMPO": 3.0,
                "bomLevel": 1
            }
        ]
    }
}
```

---

## 🧠 Dicas para o agente GPT

-   Utilize `/products/{code}/structure` para entender a **árvore de montagem**.
-   Utilize `/products/{code}/parents` para rastrear **onde o item é usado**.
-   Sempre incluir paginação (`page`, `page_size`) para respostas grandes.
-   Campos `max_depth` > 10 podem ser lentos; mantenha entre 5–10.
-   Trate `data["components"]` recursivamente — cada nó contém subcomponentes.

```

```
