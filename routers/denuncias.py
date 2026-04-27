import shutil
import uuid
import models
import schemas

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from typing import List
from routers.usuarios import obter_usuario_atual
from schemas import DenunciaResposta

router = APIRouter(tags=["Denúncias"])

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
    extensao = foto.filename.split(".")[-1]
    nome_arquivo = f"denuncia_{uuid.uuid4().hex}.{extensao}"
    caminho_foto = f"uploads/{nome_arquivo}"

    with open(caminho_foto, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)

    nova_denuncia = models.Denuncia(
        categoria=categoria,
        descricao=descricao,
        latitude=latitude,
        longitude=longitude,
        foto_url=caminho_foto,
        usuario_id=usuario_atual.id
    )
    db.add(nova_denuncia)
    
    db.commit()
    db.refresh(nova_denuncia)
    
    novo_historico = models.HistoricoDenuncia(
        denuncia_id=nova_denuncia.id,
        texto="Denúncia enviada pelo utilizador\n(+50 pts)"
    )
    db.add(novo_historico)
    
    pontos_recompensa = 50
    usuario_atual.pontuacao += pontos_recompensa 
    
    db.commit()
    
    return {
        "status": "sucesso", 
        "mensagem": "Denúncia registada com sucesso!", 
        "pontos_ganhos": pontos_recompensa
    }

@router.get("/minhas-denuncias", response_model=List[schemas.DenunciaResposta])
def listar_minhas_denuncias(
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_atual.id).all()
    return denuncias

@router.put("/{denuncia_id}/status")
def atualizar_status_denuncia(
    denuncia_id: int, 
    novo_status: str, 
    db: Session = Depends(get_db)
):
    denuncia = db.query(models.Denuncia).filter(models.Denuncia.id == denuncia_id).first()
    
    if not denuncia:
        raise HTTPException(status_code=404, detail="Denúncia não encontrada")

    denuncia.status = novo_status

    texto_historico = f"Status alterado para '{novo_status}'\n(por admin)"
    
    novo_historico = models.HistoricoDenuncia(
        denuncia_id=denuncia.id,
        texto=texto_historico
    )
    
    db.add(novo_historico)
    db.commit()

    return {"status": "sucesso", "mensagem": "Status atualizado e histórico registrado!"}

@router.get("/denuncias", response_model=List[schemas.DenunciaResposta])
def listar_todas_denuncias(db: Session = Depends(get_db)):
    return db.query(models.Denuncia).all()

@router.get("/denuncias/{denuncia_id}", response_model=schemas.DenunciaResposta)
def obter_detalhes_denuncia(denuncia_id: int, db: Session = Depends(get_db)):
    denuncia = db.query(models.Denuncia).filter(models.Denuncia.id == denuncia_id).first()
    
    if not denuncia:
        raise HTTPException(status_code=404, detail="Denúncia não encontrada no banco")
    
    return denuncia