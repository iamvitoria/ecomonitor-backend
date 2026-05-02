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
    db.flush()
    
    novo_historico = models.HistoricoDenuncia(
        denuncia_id=nova_denuncia.id,
        texto="Denúncia enviada pelo usuário (+50 pts)"
    )
    db.add(novo_historico)
    
    usuario_atual.pontuacao += 50
    
    conquistas_merecidas = db.query(models.Conquista).filter(models.Conquista.pontos_necessarios <= usuario_atual.pontuacao).all()
    
    novas_conquistas = []
    
    for conquista in conquistas_merecidas:
        ja_possui = db.query(models.UsuarioConquista).filter(
            models.UsuarioConquista.usuario_id == usuario_atual.id,
            models.UsuarioConquista.conquista_id == conquista.id
        ).first()
        
        if not ja_possui:
            nova_conquista_usuario = models.UsuarioConquista(
                usuario_id=usuario_atual.id, 
                conquista_id=conquista.id
            )
            db.add(nova_conquista_usuario)
            novas_conquistas.append(conquista.nome)
            
    db.commit()
    
    mensagem_retorno = "Denúncia registrada com sucesso! Você ganhou 50 pontos."
    if novas_conquistas:
        mensagem_retorno += f" Novas conquistas desbloqueadas: {', '.join(novas_conquistas)}"
        
    return {
        "status": "sucesso", 
        "mensagem": mensagem_retorno,
        "pontuacao_atual": usuario_atual.pontuacao,
        "novas_conquistas": novas_conquistas
    }

@router.get("/minhas-denuncias", response_model=List[schemas.DenunciaResposta])
def listar_minhas_denuncias(
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_atual.id).all()
    return denuncias

@router.put("/denuncias/{id}/status") 
def atualizar_status_denuncia(id: int, novo_status: str, db: Session = Depends(get_db)):
    denuncia = db.query(models.Denuncia).filter(models.Denuncia.id == id).first()
    
    if not denuncia:
        raise HTTPException(status_code=404, detail="Denúncia não encontrada")
        
    denuncia.status = novo_status
    
    registro_historico = models.HistoricoDenuncia(
        denuncia_id=id,
        texto=f"Status atualizado para '{novo_status}'"
    )
    db.add(registro_historico)
    
    db.commit()
    db.refresh(denuncia)
    
    return {"mensagem": "Status atualizado com sucesso", "status_atual": denuncia.status}

@router.get("/denuncias/{denuncia_id}/historico")
def buscar_historico(denuncia_id: int, db: Session = Depends(get_db)):
    return db.query(models.HistoricoDenuncia).filter(
        models.HistoricoDenuncia.denuncia_id == denuncia_id
    ).order_by(models.HistoricoDenuncia.data_registro.asc()).all()