import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from database import engine
import models

# 1. Importando os nossos "mini-apps" (as rotas separadas da pasta routers)
from routers import denuncias, usuarios

# 2. Cria as tabelas no banco de dados (se não existirem)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoMonitor API")

# 3. Cria a pasta 'uploads' se ela não existir
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# 4. Libera a pasta 'uploads' para a internet conseguir carregar as fotos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 5. Libera o acesso do Frontend para fazer requisições sem erro de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6. Registrando as rotas no app principal! 🚀
app.include_router(usuarios.router)
app.include_router(denuncias.router)

# 7. Rota de Teste
@app.get("/")
def home():
    return {"status": "sucesso", "mensagem": "API do EcoMonitor online e modularizada!"}