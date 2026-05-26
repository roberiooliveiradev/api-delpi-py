# API DELPI — Integração TOTVS Protheus

API RESTful (FastAPI) para integração com o ERP TOTVS Protheus via SQL Server.
Compatível com agentes GPT para consultas automatizadas.

---

## Stack

- Python 3.11 + FastAPI + Uvicorn
- SQL Server via pyodbc (ODBC Driver 17)
- Autenticação JWT
- Docker para deploy

---

## Requisitos

- Docker e Docker Compose
- Acesso de rede ao SQL Server (TOTVS Protheus)

---

## Setup rápido

1. Clone o repositório:
   git clone <URL_DO_REPOSITORIO>
   cd api-delpi-py

2. Configure as variáveis de ambiente:
   cp .env.example .env
   # Edite o .env com seus dados reais

3. Suba o container:
   docker compose up -d --build

4. Teste:
   curl http://127.0.0.1:3000/

---

## Variáveis de ambiente (.env)

| Variável                   | Descrição                    | Padrão  |
|----------------------------|------------------------------|---------|
| DB_HOST                    | Host do SQL Server           | -       |
| DB_USER                    | Usuário do banco             | -       |
| DB_PASSWORD                | Senha do banco               | -       |
| DB_DATABASE                | Nome do banco                | -       |
| DB_PORT                    | Porta do SQL Server          | 1433    |
| PORT                       | Porta interna do container   | 8000    |
| JWT_SECRET                 | Chave secreta JWT            | secret  |
| AUTO_EXECUTE_API           | Config agente GPT            | true    |
| CONFIRM_BEFORE_REQUEST     | Config agente GPT            | false   |
| SHOW_PAYLOAD_BEFORE_EXECUTE| Config agente GPT            | false   |

---

## Comandos úteis

Subir:          docker compose up -d --build
Parar:          docker compose down
Logs:           docker compose logs -f
Status:         docker compose ps
Restart:        docker compose restart
Rebuild limpo:  docker compose build --no-cache

---

## Atualizar em produção

cd ~/projetos/api-delpi-py
git pull
docker compose up -d --build

---

## Endpoints principais

GET  /                  Health check
POST /products/...      Consultas de produtos
POST /system/...        Informações do sistema
POST /data/...          Consultas SQL genéricas (com whitelist)

Documentação interativa: http://127.0.0.1:3000/docs

---

## Arquitetura

app/
├── main.py              Entry point (FastAPI)
├── config.py            Configurações (.env)
├── database.py          Conexão SQL Server
├── config/              Whitelist de tabelas
├── core/                Exceções e respostas
├── middleware/          Autenticação JWT
├── models/              Modelos Pydantic
├── repositories/        Acesso a dados (SQL)
├── routes/              Endpoints da API
├── services/            Lógica de negócio
└── utils/               JWT, logger, validador SQL
