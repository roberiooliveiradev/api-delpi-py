# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings  # Configurações do .env
from app.routes import cliente_routes   # Rotas de exemplo
from app.routes import product_routes   # Rotas de produtos

SERVER_URL = " https://f9d93299af6d.ngrok-free.app"
# Instância principal do app FastAPI
app = FastAPI(
    title="API TOTVS Protheus",
    description="API RESTful para integração com o TOTVS Protheus — compatível com agentes GPT.",
    version="1.0.0",
    contact={
        "name": "Equipe de Integração DELPI",
        "email": "suporte@delpi.com.br",
    },
    servers=[ 
        {"url": SERVER_URL, "description": "Servidor público (ngrok / produção)"}
    ],
)

# Configuração do CORS (para permitir chamadas do agente GPT e outros clientes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua por domínios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rota raiz — teste rápido da API
@app.get("/", tags=["Health Check"])
def root():
    return {"status": "online", "message": "API TOTVS Protheus em execução 🚀"}

# Inclui rotas adicionais (ex: prospecção de dados)
app.include_router(cliente_routes.router, prefix="/dados", tags=["dados"])
app.include_router(product_routes.router, prefix="/products", tags=["products"])

# Execução direta (modo desenvolvimento)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(settings.PORT), reload=True)
