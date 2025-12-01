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
| `POST` | `/products/search`                        | Pesquisa produto específico por código, descrição ou grupo    |
| `GET`  | `/products/{code}`                        | Consulta produto específico                                   |
| `GET`  | `/products/{code}/structure`              | Estrutura do produto (componentes) via CTE                    |
| `GET`  | `/products/{code}/parents`                | Produtos que utilizam o item (pais) via CTE                   |
| `GET`  | `/products/{code}/suppliers`              | Lista fornecedores de um produto                              |
| `GET`  | `/products/{code}/inbound-invoice-items`  | Notas fiscais de entrada do item                              |
| `GET`  | `/products/{code}/outbound-invoice-items` | Notas fiscais de saída do item                                |
| `GET`  | `/products/{code}/stock`                  | Consulta estoque com filtros e paginação                      |
| `GET`  | `/products/{code}/guide`                  | Roteiro de produção (SG2010) com opção de incluir componentes |
| `GET`  | `/products/{code}/inspection`             | Cadastro de inspeções de produtos e sesu componentes          |

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

### 🔹 2. Busca Avançada por Descrição

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
GET /products/{code}/guide?page=1&page_size=50&branch=01&&max_depth=10
```

| Parâmetro   | Tipo | Obrigatório | Descrição                                                              |
| ----------- | ---- | ----------- | ---------------------------------------------------------------------- |
| `code`      | str  | ✔           | Código do produto (`G2_PRODUTO`)                                       |
| `page`      | int  | ✖           | Página atual (default: 1)                                              |
| `page_size` | int  | ✖           | Registros por página (default: 50, máx: 500)                           |
| `branch`    | str  | ✖           | Filial (`G2_FILIAL`)                                                   |
| `max_depth` | int  | ✖           | Profundidade da estrutura ao buscar componentes (default: 10, máx: 50) |

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
GET /products/10080522/guide?page=1&page_size=20
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

**📘 Unidade das colunas**

| Coluna        | Unidade  | Obs                                                                                        |
| ------------- | -------- | ------------------------------------------------------------------------------------------ |
| **G2_SETUP**  | Minutos  | Tempo gasto para preparação (Setup) do Recurso para a operação.                            |
| **G2_TEMPAD** | Hora/Mil | Tempo Padrão de Operação. Tempo gasto nesta Operação para processamento de um Lote Padrão. |

> **A unidade de medida do tempo padrão (G2_TEMPAD) é hora/mil**

> **A unidade de medida do tempo padrão (G2_SETUP) é minutos**

> Indicar a filial de referência **coluna G2_FILIAL**

#### 🧮 Cálculo de Tempo Total de Produção (com Estrutura SG1010)

Ao calcular o **tempo total de produção de um item**, deve-se considerar o roteiro (SG2010) e a estrutura (SG1010).

| Fonte      | Campo       | Unidade      | Descrição                                                                  |
| ---------- | ----------- | ------------ | -------------------------------------------------------------------------- |
| **SG2010** | `G2_SETUP`  | **Hora**     | Tempo fixo de preparação (setup) executado uma vez por operação.           |
| **SG2010** | `G2_TEMPAD` | **Hora/Mil** | Tempo padrão da operação — **expresso em horas para produzir 1000 peças.** |

🧩 **Fórmula geral (por peça):**

\[
\text{Tempo Total (h)} = \sum G2_SETUP + \sum \left( \frac{G2_TEMPAD}{1000} \times \text{Qtd_Peças} \right)
\]

##### 🔹 **Regras:**

-   O **setup (`G2_SETUP`)** é somado integralmente (ocorre uma vez por operação).
-   O **tempo padrão (`G2_TEMPAD`)** e a **quantidade do componente (`G1_QUANT`)** são normalizados por mil peças — portanto, devem ser divididos por 1000 duas vezes (mil × mil).
-   Após obter o tempo de **1 peça**, multiplica-se pela **quantidade solicitada pelo usuário**.
-   O resultado final é expresso em **horas totais**, podendo ser convertido para minutos (×60).

**Exemplo prático**

| Operação | G2_SETUP (h) | G2_TEMPAD (h/mil) | Qtd Peças | Cálculo                   | Tempo (h) |
| -------- | ------------ | ----------------- | --------- | ------------------------- | --------- |
| 01       | 0.02         | 3.00              | 33        | 0.02 + (3.00 / 1000 × 33) | 0.119     |
| 02       | 0.05         | 1.50              | 33        | 0.05 + (1.50 / 1000 × 33) | 0.0995    |

**Tempo total do roteiro (33 peças):**  
\[
\text{Tempo Total (h)} = 0.119 + 0.0995 = \mathbf{0.2185\,h}
\]
\[
\text{Tempo Total (min)} = 0.2185 \times 60 = \mathbf{13.11\,min}
\]

> O agente DELPI deve sempre calcular **tempo por peça primeiro**, e só depois multiplicar pela **quantidade solicitada**, garantindo consistência com o roteiro (SG2010).

---

### 🔹 11. Inspeção de Processo (Inspection)

Retorna todas as informações de inspeção do produto informado **e de todos os seus componentes** em todos os níveis da estrutura (SG1).

A consulta utiliza as seguintes tabelas Protheus:

-   **SG1010 – Estrutura de Produto**  
    Usada para determinar todos os componentes em todos os níveis.
-   **QP6010 – Cabeçalho da Inspeção**  
    Traz dados gerais de inspeção para cada produto.
-   **QP7010 – Ensaios Mensuráveis**  
    Traz valores numéricos de inspeção (mínimo, máximo, nominal, limites etc.).
-   **QP8010 – Ensaios Textuais**  
    Traz ensaios com resultados em formato de texto.

---

```http
 GET /products/{code}/inspection?page=1&page_size=50&max_depth=10
```

##### 📌 Parâmetros

| Parâmetro   | Tipo | Obrigatório | Descrição                                                     |
| ----------- | ---- | ----------- | ------------------------------------------------------------- |
| `code`      | str  | ✔           | Código do produto (`QP6_PRODUT`)                              |
| `page`      | int  | ✖           | Página atual (default: 1)                                     |
| `page_size` | int  | ✖           | Registros por página (default: 50, máximo: 500)               |
| `max_depth` | int  | ✖           | Profundidade da estrutura ao buscar componentes (default: 10) |

---

---

#### 🔧 **Como funciona**

1. A API recebe um código de produto.
2. Usa SG1 para montar **toda a árvore de componentes**, incluindo múltiplos níveis.
3. Para **cada produto encontrado** (pai + componentes):
    - Busca **QP6** (um único cabeçalho por produto).
    - Busca **QP7** (lista de ensaios mensuráveis).
    - Busca **QP8** (lista de ensaios texto).
4. Retorna uma lista onde cada item representa **um produto** com:
    - `product` → código do produto
    - `level` → nível dentro da estrutura
    - `parentCode` → código do pai
    - `QP6` → objeto único
    - `QP7` → lista
    - `QP8` → lista

**📘 Exemplo de requisição**

```http
GET /products/90264022/inspection?page=1&page_size=10&max_depth=10
```

---

**📘 Exemplo de resposta**

```json
{
  "success": true,
  "message": "Inspeção de 90264022 retornada com sucesso (página 1/1).",
  "data": [
    {
      "product": "90264022",
      "level": 0,
      "parentCode": "",
      "QP6": { ... },
      "QP7": [],
      "QP8": [ ... ]
    },
    {
      "product": "70260035",
      "level": 1,
      "parentCode": "90264022",
      "QP6": { ... },
      "QP7": [ ... ],
      "QP8": [ ... ]
    }
  ]
}
```

#### 📘 **Observações importantes**

-   Somente produtos que possuem **registro na QP6** aparecem no resultado.
-   Componentes que não possuam inspeção configurada são ignorados.
-   O retorno **não é hierárquico** — a estrutura é linear, com os níveis informados em `level`.
-   `parentCode` permite reconstruir a árvore se necessário.

---

#### 📌 Campos Retornados

##### 🔹 qp6 — Cabeçalho da inspeção

Campos como:

-   QP6_PRODUT
-   QP6_REVI
-   QP6_DESCPO
-   QP6_DTCAD
-   QP6_PTOLER
-   QP6_TIPO
-   QP6_SITPRD

##### 🔹 ensaios_mensuraveis — QP7010

-   QP7_ENSAIO
-   QP7_UNIMED
-   QP7_MIN / QP7_MAX
-   QP7_LABOR

##### 🔹 ensaios_textuais — QP8010

-   QP8_ENSAIO
-   QP8_TEXTO
-   QP8_LABOR
-   QP8_OPERAC

---

#### 🧩 Dicas para o agente GPT

-   Use `max_depth >= 5` para inspeções completas.
-   Use paginação sempre em estruturas grandes.
-   Para apenas o produto principal, use `max_depth = 0–1`.

---

### 🔹 12. Análise Completa do Produto (Product Analyser)

A rota **Product Analyser** consolida em **uma única chamada**:

-   Dados gerais (SB1)\
-   Estrutura completa (BOM via SG1010)\
-   Roteiro completo (SG2010)\
-   Inspeções completas (QP6, QP7, QP8)

---

#### 📘 Endpoint

```http
GET /products/{code}/analyser?page=1&page_size=50&max_depth=10
```

---

#### 📌 Parâmetros

Parâmetro Tipo Obrigatório Descrição

| Parâmetro   | Tipo | Obrigatório | Descrição                                                             |
| ----------- | ---- | ----------- | --------------------------------------------------------------------- |
| `code`      | str  | ✔           | Código do produto (`B1_COD`)                                          |
| `page`      | int  | ✖           | Página (default: 1)                                                   |
| `page_size` | int  | ✖           | Registros por página (default 50, máximo 500)                         |
| `max_depth` | int  | ✖           | Profundidade da estrutura ao buscar componentes (default: 10, máx 15) |

---

#### 📘 Exemplo de Requisição

```http
GET /products/10080522/analyser?page=1&page_size=20&max_depth=10
```

---

#### 📘 Exemplo de Resposta

```json
{
  "success": true,
  "message": "Análise completa de 10080522 retornada com sucesso.",
  "data": {
    "product": { ... },
    "structure": { ... },
    "guide": { ... },
    "inspection": { ... }
  }
}
```

---

### 🔹 13. Fornecedores do Produto (Product ↔ Fornecedor)

Consulta os fornecedores vinculados a um produto na tabela SA5010 – Amarração Produto x Fornecedor, permitindo identificar quem fornece determinado item, além de preços e condições associadas.

**📘 Endpoint**

```http
GET /products/{code}/suppliers?page=1&page_size=50
```

**📌 Parâmetros**

| Parâmetro   | Tipo | Obrigatório | Descrição                                    |
| ----------- | ---- | ----------- | -------------------------------------------- |
| `code`      | str  | ✔           | Código do produto (`A5_PRODUTO`)             |
| `page`      | int  | ✖           | Página atual (default: 1)                    |
| `page_size` | int  | ✖           | Registros por página (default: 50, máx: 500) |

**📘 Exemplo de Requisição**

```http
GET /products/90264022/suppliers?page=1&page_size=10
```

**📘 Exemplo de Requisição**

```json
{
    "success": true,
    "message": "Fornecedores de 90264022 retornados com sucesso (página 1/1).",
    "data": {
        "total": 2,
        "page": 1,
        "pageSize": 10,
        "totalPages": 1,
        "data": [
            {
                "A5_FORNECE": "000001",
                "A2_NOME": "DELPI COMPONENTES LTDA",
                "A5_PRODUTO": "90264022",
                "A5_LOJA": "01",
                "A5_CODFOR": "D90264022",
                "A5_DESCFOR": "CHICOTE MOTOR 1.0 – COMPONENTE",
                "A5_PRECO": 2.87,
                "A5_DTREF": "2025-01-15",
                "A5_PRAZO": 30
            },
            {
                "A5_FORNECE": "000002",
                "A2_NOME": "TECFIOS INDÚSTRIA ELÉTRICA",
                "A5_PRODUTO": "90264022",
                "A5_LOJA": "01",
                "A5_CODFOR": "TF90264022",
                "A5_DESCFOR": "CHICOTE MOTOR 1.0 – ALT. FI",
                "A5_PRECO": 2.91,
                "A5_DTREF": "2025-03-01",
                "A5_PRAZO": 45
            }
        ]
    }
}
```

**📗 Origem dos Dados**

| Campo        | Origem | Descrição                          |
| ------------ | ------ | ---------------------------------- |
| `A5_PRODUTO` | SA5010 | Código do produto DELPI            |
| `A5_FORNECE` | SA5010 | Código do fornecedor               |
| `A2_NOME`    | SA2010 | Nome do fornecedor                 |
| `A5_LOJA`    | SA5010 | Loja do fornecedor                 |
| `A5_CODFOR`  | SA5010 | Código do produto no fornecedor    |
| `A5_DESCFOR` | SA5010 | Descrição do produto no fornecedor |
| `A5_PRECO`   | SA5010 | Preço de compra atual              |
| `A5_DTREF`   | SA5010 | Data de referência do preço        |
| `A5_PRAZO`   | SA5010 | Prazo médio de entrega em dias     |

**🧠 Observações Técnicas**

-   Retorna apenas registros ativos (D*E_L_E_T* = '').

-   Junção padrão com SA2010 para obter o nome do fornecedor.

-   Ordenação por fornecedor e loja.

-   Datas convertidas para formato YYYY-MM-DD.

-   Indicada para identificar fontes alternativas de fornecimento de um item.

**📘 Dica para o Agente DELPI**

> Quando o usuário solicitar:
>
> -   “Quais são os fornecedores do produto 90264022?”
> -   “Quem fornece este componente?”
> -   “Existe fornecedor alternativo para este item?”

---

### 🔹 14. Clientes Amarrados ao Produto (Product ↔ Cliente)

_Consulta os clientes vinculados a um produto na tabela SA7010 – Amarração Produto x Cliente, com apoio da tabela SA1010 (Clientes)._

Permite identificar:

-   O código e nome do cliente;

-   O código e a descrição do produto no cliente;

-   Unidades e preços configurados;

-   Datas de referência de preço.

**📘 Endpoint**

```http
GET /products/{code}/customers?page=1&page_size=50
```

**📌 Parâmetros**

| Parâmetro   | Tipo | Obrigatório | Descrição                                    |
| ----------- | ---- | ----------- | -------------------------------------------- |
| `code`      | str  | ✔           | Código do produto (`A7_PRODUTO`)             |
| `page`      | int  | ✖           | Página atual (default: 1)                    |
| `page_size` | int  | ✖           | Registros por página (default: 50, máx: 500) |

**📘 Exemplo de Requisição**

```http
GET /products/90264022/customers?page=1&page_size=10
```

**📘 Exemplo de Resposta**

```json
{
    "success": true,
    "message": "Clientes vinculados ao produto 90264022 retornados com sucesso (página 1/1).",
    "data": {
        "total": 2,
        "page": 1,
        "pageSize": 10,
        "totalPages": 1,
        "data": [
            {
                "A1_COD": "000123",
                "A1_NOME": "FIAT AUTOMOVEIS LTDA",
                "A1_NREDUZ": "FIAT",
                "A1_LOJA": "01",
                "A7_PRODUTO": "90264022",
                "A7_CODCLI": "F123-456",
                "A7_DESCCLI": "CHICOTE MOTOR 1.0",
                "A7_PRECO01": 3.75,
                "A7_DTREF01": "2025-02-01"
            },
            {
                "A1_COD": "000456",
                "A1_NOME": "RENAULT DO BRASIL",
                "A1_NREDUZ": "RENAULT",
                "A1_LOJA": "01",
                "A7_PRODUTO": "90264022",
                "A7_CODCLI": "R90264022",
                "A7_DESCCLI": "FEIXE MOTOR",
                "A7_PRECO01": 3.88,
                "A7_DTREF01": "2025-03-15"
            }
        ]
    }
}
```

**📗 Origem dos Dados**

| Campo           | Origem | Descrição                                |
| --------------- | ------ | ---------------------------------------- |
| `A7_PRODUTO`    | SA7010 | Código do produto DELPI                  |
| `A7_CODCLI`     | SA7010 | Código do produto no cliente             |
| `A7_DESCCLI`    | SA7010 | Descrição do produto conforme cliente    |
| `A1_COD`        | SA1010 | Código do cliente                        |
| `A1_NOME`       | SA1010 | Nome completo do cliente                 |
| `A1_NREDUZ`     | SA1010 | Nome reduzido                            |
| `A1_MSBLQL`     | SA1010 | Situação (bloqueado/liberado)            |
| `A7_PRECO01–09` | SA7010 | Preços configurados por faixa (opcional) |
| `A7_DTREF01–09` | SA7010 | Datas de referência correspondentes      |

**🧠 Observações Técnicas**

-   Apenas registros ativos (D*E_L_E_T* = '') são retornados.

-   A junção é feita por cliente e loja (A1_COD + A1_LOJA).

-   O retorno é paginado e ordenado por cliente e loja.

-   Datas no formato YYYY-MM-DD para legibilidade.

-   Ideal para identificar clientes exclusivos de um produto ou cruzar amarrações comerciais.

**📘 Dica para o Agente DELPI**

> Ao identificar perguntas como:
>
> -   “Quais clientes compram o produto 90264022?”
> -   “Para quem este produto está amarrado?”
> -   “Qual o código do produto no cliente FIAT?”

## 🧠 Dicas para o agente GPT

-   Utilize `/products/{code}/structure` para entender a **árvore de montagem**.
-   Utilize `/products/{code}/parents` para rastrear **onde o item é usado**.
-   Sempre incluir paginação (`page`, `page_size`) para respostas grandes.
-   Campos `max_depth` > 10 podem ser lentos; mantenha entre 5–10.
-   Trate `data["components"]` recursivamente — cada nó contém subcomponentes.
-   **Atente-se para as unidades** de medida das colunas indicadas na documentação.
