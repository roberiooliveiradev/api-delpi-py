# 🧩 Guia de Uso — Product API

## 📘 Descrição

A API **Product** fornece acesso aos dados de produtos e suas relações no **Protheus**, incluindo:

-   Consulta de produtos (`SB1010`)
-   Estrutura (BOM) e hierarquia de componentes (`SG1010`)
-   Relação inversa (Where Used — pais)
-   Controle de paginação e profundidade (`max_depth`)

---

## ⚙️ Endpoints

| Método | Endpoint                    | Descrição                                   |
| ------ | --------------------------- | ------------------------------------------- |
| `GET`  | `/product/`                 | Lista produtos com limite definido          |
| `GET`  | `/product/{code}`           | Consulta produto específico                 |
| `GET`  | `/product/{code}/structure` | Estrutura do produto (componentes) via CTE  |
| `GET`  | `/product/{code}/parents`   | Produtos que utilizam o item (pais) via CTE |
| `GET`  | `/product/{code}/suppliers` | Lista fornecedores de um produto            |

---

## 🔍 Parâmetros

| Parâmetro   | Tipo | Padrão | Descrição                                     |
| ----------- | ---- | ------ | --------------------------------------------- |
| `limit`     | int  | 50     | Limite de registros retornados em `/product/` |
| `code`      | str  | —      | Código do produto (`B1_COD`)                  |
| `max_depth` | int  | 10     | Profundidade máxima da recursão               |
| `page`      | int  | 1      | Página atual                                  |
| `page_size` | int  | 100    | Registros por página (máx: 500)               |

---

## 🧩 Exemplo de Requisição

### 🔹 1. Listar produtos

```http
GET /product?limit=20
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

### 🔹 2. Consultar produto específico

```http
GET /product/10080522
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

### 🔹 3. Estrutura do produto (BOM)

```http
GET /product/10080522/structure?max_depth=10&page=1&page_size=50
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

### 🔹 4. Produtos pais (Where Used)

```http
GET /product/20010001/parents?max_depth=5&page=1&page_size=50
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

## 🧠 Dicas para o agente GPT

-   Utilize `/product/{code}/structure` para entender a **árvore de montagem**.
-   Utilize `/product/{code}/parents` para rastrear **onde o item é usado**.
-   Sempre incluir paginação (`page`, `page_size`) para respostas grandes.
-   Campos `max_depth` > 10 podem ser lentos; mantenha entre 5–10.
-   Trate `data["components"]` recursivamente — cada nó contém subcomponentes.
