import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import usuarios, denuncias
from database import engine
import models
import cloudinary
from fastapi import UploadFile, File

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoMonitor API")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Lista de endereços permitidos
origins = [
    "http://localhost:5173",    # Vite local
    "http://127.0.0.1:5173",   # Vite local (alternativo)
    "https://tcc-three-mu.vercel.app", # Seu site oficial na Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Usa a lista acima
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config( 
  cloud_name = "drtl7bkgy", 
  api_key = "2249219188561177", 
  api_secret = "nswH3-yGrgpboBiAGnNYQ0SwYn0",
  secure = True
)

def upload_imagem_cloudinary(arquivo: UploadFile):
    try:
        resultado = cloudinary.uploader.upload(arquivo.file)
        return resultado.get("secure_url") 
    except Exception as e:
        print(f"Erro no Cloudinary: {e}")
        return None

app.include_router(usuarios.router)
app.include_router(denuncias.router)

@app.get("/")
def home():
    return {"status": "sucesso", "mensagem": "API Online"}