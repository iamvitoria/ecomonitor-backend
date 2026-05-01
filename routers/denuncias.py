import shutil
import uuid
import models
import schemas
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from typing import List
from routers.usuarios import obter_usuario_atual

router = APIRouter(tags=["Denúncias"])

@router.get("/denuncias", response_model=List[schemas.DenunciaResposta])
def listar_todas_denuncias(db: Session = Depends(get_db)):
    return db.query(models.Denuncia).all()

@router.get("/denuncias/{denuncia_id}", response_model=schemas.DenunciaResposta)
def obter_detalhes_denuncia(denuncia_id: int, db: Session = Depends(get_db)):
    denuncia = db.query(models.Denuncia).filter(models.Denuncia.id == denuncia_id).first()
    if not denuncia:
        raise HTTPException(status_code=404, detail="Denúncia não encontrada")
    return denuncia

@router.post("/denuncias")
async def criar_denuncia(
    categoria: str = Form(...),
    descricao: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual) 
):
    dicionario_categorias = {
        "lixo": "Descarte Irregular de Lixo",
        "desmatamento": "Desmatamento",
        "poluicao_agua": "Poluição da Água",
        "queimada": "Queimada",
        "poluicao_ar": "Poluição do Ar",
        "animais": "Maus-tratos Animais",
        "foco_mosquito": "Foco de Mosquito",
        "esgoto": "Esgoto Aberto"
    }
    
    categoria_traduzida = dicionario_categorias.get(categoria, categoria)

    extensao = foto.filename.split(".")[-1]
    nome_arquivo = f"denuncia_{uuid.uuid4().hex}.{extensao}"
    caminho_foto = f"uploads/{nome_arquivo}"
    
    with open(caminho_foto, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)
        
    nova_denuncia = models.Denuncia(
        categoria=categoria_traduzida, 
        descricao=descricao,
        latitude=latitude, 
        longitude=longitude,
        foto_url=caminho_foto, 
        usuario_id=usuario_atual.id
    )
    db.add(nova_denuncia)
    db.commit()
    return {"status": "sucesso", "mensagem": "Denúncia registrada!"}

@router.get("/minhas-denuncias", response_model=List[schemas.DenunciaResposta])
def listar_minhas_denuncias(
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_atual.id).all()
    return denuncias