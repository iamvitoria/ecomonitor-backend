import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import usuarios, denuncias
from database import engine
import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoMonitor API")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuarios.router)
app.include_router(denuncias.router)

@app.get("/")
def home():
    return {"status": "sucesso", "mensagem": "API do EcoMonitor online e modularizada!"}