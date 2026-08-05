import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import registros, usuarios, categorias
from database import engine
import models
import cloudinary
from fastapi import UploadFile

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoMonitor API")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

origins = [
    "http://localhost:5173",  
    "http://localhost:4173",
    "http://127.0.0.1:5173",   
    "http://localhost:3000",
    "https://tcc-three-mu.vercel.app", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config( 
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
    api_key = os.environ.get("CLOUDINARY_API_KEY"), 
    api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
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
app.include_router(registros.router)
app.include_router(categorias.router)

@app.get("/")
def home():
    return {"status": "sucesso", "mensagem": "API Online"}
