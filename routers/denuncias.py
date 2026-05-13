import shutil
import uuid

from sqlalchemy import func
import models
import schemas
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from typing import List
from routers.usuarios import obter_usuario_atual

import cloudinary
import cloudinary.uploader

router = APIRouter(tags=["Denúncias"])

@router.get("/denuncias")
def listar_todas_denuncias(db: Session = Depends(get_db)):
    denuncias = db.query(models.Denuncia).outerjoin(models.Usuario).all()
    
    resultado = []
    for d in denuncias:
        nome_usuario = d.usuario.nome if d.usuario else "Anônimo"
        
        resultado.append({
            "id": d.id,
            "categoria": d.categoria,
            "descricao": d.descricao,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "foto_url": d.foto_url,
            "status": d.status,
            "data_criacao": d.data_criacao,
            "usuario_id": d.usuario_id,
            "usuario_nome": nome_usuario,
            "endereco": getattr(d, 'endereco', "Localização via GPS")
        })
        
    return resultado

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

    try:
        resultado = cloudinary.uploader.upload(
            foto.file, 
            folder="ecomonitor/denuncias"
        )
        url_da_foto = resultado.get("secure_url")
    except Exception as e:
        print(f"Erro Cloudinary: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar imagem da denúncia.")
        
    nova_denuncia = models.Denuncia(
        categoria=categoria_traduzida, 
        descricao=descricao,
        latitude=latitude, 
        longitude=longitude,
        foto_url=url_da_foto, 
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
    
    return {
        "status": "sucesso", 
        "mensagem": f"Denúncia registrada! +50 pts. {f'Novas conquistas: {list(novas_conquistas)}' if novas_conquistas else ''}",
        "pontuacao_atual": usuario_atual.pontuacao,
        "foto_url": url_da_foto
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
    
@router.get("/ranking")
def get_ranking(db: Session = Depends(get_db)):
    ranking_cidades = (
        db.query(
            models.Denuncia.endereco,
            func.count(models.Denuncia.id).label("total")
        )
        .filter(models.Denuncia.endereco != None)
        .group_by(models.Denuncia.endereco)
        .order_by(func.count(models.Denuncia.id).desc())
        .all()
    )

    ranking_usuarios = (
        db.query(
            models.Usuario.nome,
            models.Usuario.pontuacao
        )
        .filter(models.Usuario.perfil == "user") 
        .order_by(models.Usuario.pontuacao.desc())
        .limit(10)
        .all()
    )

    return {
        "global": [{"nome": r.endereco, "pontos": r.total} for r in ranking_cidades],
        "local": [{"nome": r.nome, "pontos": r.pontuacao} for r in ranking_usuarios]
    }