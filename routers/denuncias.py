import shutil
import uuid
import utils

from sqlalchemy import func
import models
import schemas
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
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
            "categoria": d.categoria.nome if d.categoria else "Sem Categoria",
            "descricao": d.descricao,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "foto_url": d.foto_url,
            "status": d.status,
            "data_criacao": d.data_criacao,
            "usuario_id": d.usuario_id,
            "usuario_nome": nome_usuario,
            "endereco": getattr(d, 'endereco', "Localização via GPS"),
            "cidade": getattr(d, 'cidade', "Não informada") 
        })
        
    return resultado

@router.get("/denuncias/{denuncia_id}")
def obter_detalhes_denuncia(denuncia_id: int, db: Session = Depends(get_db)):
    denuncia = db.query(models.Denuncia).options(
        joinedload(models.Denuncia.usuario)
    ).filter(models.Denuncia.id == denuncia_id).first()
    
    if not denuncia:
        raise HTTPException(status_code=404, detail="Denúncia não encontrada")
        
    total_contribuicoes = 0
    if denuncia.usuario_id:
        total_contribuicoes = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == denuncia.usuario_id).count()
        
    resultado = {
        "id": denuncia.id,
        "categoria_id": denuncia.categoria_id,
        "categoria_nome": denuncia.categoria.nome,
        "descricao": denuncia.descricao,
        "latitude": denuncia.latitude,
        "longitude": denuncia.longitude,
        "foto_url": denuncia.foto_url,
        "status": denuncia.status,
        "data_criacao": denuncia.data_criacao,
        "usuario_id": denuncia.usuario_id,
        "endereco": denuncia.endereco,
        "cidade": denuncia.cidade,
        "usuario": {
            "nome": denuncia.usuario.nome if denuncia.usuario else "Anônimo",
            "email": denuncia.usuario.email if denuncia.usuario else "",
            "pontuacao": denuncia.usuario.pontuacao if denuncia.usuario else 0,
            "contribuicoes": total_contribuicoes 
        } if denuncia.usuario else None
    }
        
    return resultado

@router.put("/denuncias/{denuncia_id}")
async def editar_denuncia(
    denuncia_id: int,
    categoria: str = Form(...),
    descricao: str = Form(""),
    endereco: str = Form(None),
    foto: UploadFile = File(None),  
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    denuncia = db.query(models.Denuncia).filter(models.Denuncia.id == denuncia_id).first()
    
    if not denuncia:
        raise HTTPException(status_code=404, detail="Denúncia não encontrada")
        
    if denuncia.usuario_id != usuario_atual.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar este registro")

    dicionario_categorias = {
        "lixo": "Descarte Irregular de Lixo",
        "desmatamento": "Desmatamento",
        "poluicao_agua": "Poluição da Água",
        "queimada": "Queimada",
        "poluicao_ar": "Poluição do Ar",
        "animais": "Maus-tratos aos Animais",
        "foco_mosquito": "Foco de Mosquito",
        "esgoto": "Esgoto a Céu Aberto"
    }
    
    categoria_traduzida = dicionario_categorias.get(categoria, categoria)

    categoria_obj = db.query(models.Categoria).filter(
        models.Categoria.nome == categoria_traduzida
    ).first()

    if not categoria_obj:
        raise HTTPException(status_code=400, detail="Categoria inválida")

    denuncia.categoria_id = categoria_obj.id
    denuncia.descricao = descricao
    if endereco:
        denuncia.endereco = endereco

    if foto and foto.filename:
        try:
            resultado = cloudinary.uploader.upload(
                foto.file, 
                folder="ecomonitor/denuncias"
            )
            denuncia.foto_url = resultado.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Erro ao processar nova imagem no Cloudinary.")
            
    novo_historico = models.HistoricoDenuncia(
        denuncia_id=denuncia.id,
        texto="Registro editado pelo usuário"
    )
    db.add(novo_historico)
    
    db.commit()
    db.refresh(denuncia)
    
    return {
        "status": "sucesso",
        "denuncia": {
            "id": denuncia.id,
            "categoria": denuncia.categoria.nome,
            "descricao": denuncia.descricao,
            "foto_url": denuncia.foto_url,
            "endereco": denuncia.endereco,
            "status": denuncia.status,
            "latitude": denuncia.latitude,   
            "longitude": denuncia.longitude
        }
    }

@router.post("/denuncias")
async def criar_denuncia(
    categoria_id: int = Form(...),
    descricao: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
    endereco: str = Form(None),
    cidade: str = Form(None),
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual) 
):
    categoria_obj = db.query(models.Categoria).filter(
        models.Categoria.id == categoria_id
    ).first()

    if not categoria_obj:
        raise HTTPException(status_code=400, detail="Categoria inválida ou não encontrada")
    
    try:
        resultado = cloudinary.uploader.upload(
            foto.file, 
            folder="ecomonitor/denuncias"
        )
        url_da_foto = resultado.get("secure_url")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao processar imagem da denúncia.")    
    
    nova_denuncia = models.Denuncia(
        categoria_id=categoria_obj.id,
        descricao=descricao,
        latitude=latitude, 
        longitude=longitude,
        endereco=endereco,
        cidade=cidade,
        foto_url=url_da_foto, 
        usuario_id=usuario_atual.id
    )
    db.add(nova_denuncia)
    db.flush() 
    
    novo_historico = models.HistoricoDenuncia(
        denuncia_id=nova_denuncia.id,
        texto="Registro enviado pelo usuário (+50 pts)"
    )
    db.add(novo_historico)
    
    usuario_atual.pontuacao += 50
    
    db.commit()
    db.refresh(usuario_atual)
    
    utils.verificar_conquistas(usuario_atual.id, db, denuncia_id=nova_denuncia.id)
    
    db.refresh(usuario_atual)
    
    return {
        "status": "sucesso", 
        "mensagem": "Registro enviado! +50 pts.",
        "pontuacao_atual": usuario_atual.pontuacao,
        "foto_url": url_da_foto
    }

@router.get("/minhas-denuncias", response_model=List[schemas.DenunciaResposta])
def listar_minhas_denuncias(
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    denuncias = db.query(models.Denuncia).options(
        joinedload(models.Denuncia.categoria)
    ).filter(
        models.Denuncia.usuario_id == usuario_atual.id
    ).all()

    return [
        {
            "id": d.id,
            "categoria": d.categoria.nome if d.categoria else "Sem Categoria",
            "descricao": d.descricao,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "endereco": d.endereco,
            "cidade": d.cidade,
            "foto_url": d.foto_url,
            "status": d.status,
            "usuario_id": d.usuario_id,
            "data_criacao": d.data_criacao
        }
        for d in denuncias
    ]
    
@router.get("/categorias")
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(models.Categoria).all()

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
def get_ranking(
    usuario_atual: models.Usuario = Depends(obter_usuario_atual), 
    db: Session = Depends(get_db)
):
    ranking_cidades_raw = (
        db.query(
            models.Denuncia.cidade.label("nome"),
            func.count(models.Denuncia.id).label("pontos")
        )
        .filter(models.Denuncia.cidade != None)
        .group_by(models.Denuncia.cidade)
        .order_by(func.count(models.Denuncia.id).desc())
        .all()
    )

    cidade_usuario_limpa = func.lower(func.trim(usuario_atual.cidade)) if usuario_atual.cidade else ""

    ranking_usuarios_raw = (
        db.query(
            models.Usuario.nome.label("nome"),
            models.Usuario.pontuacao.label("pontos")
        )
        .filter(
            models.Usuario.perfil == "user",
            func.lower(func.trim(models.Usuario.cidade)) == cidade_usuario_limpa
        )
        .order_by(models.Usuario.pontuacao.desc())
        .limit(10)
        .all()
    )

    return {
        "global": [{"nome": r.nome, "pontos": r.pontos} for r in ranking_cidades_raw],
        "local": [{"nome": r.nome, "pontos": r.pontos} for r in ranking_usuarios_raw],
        "cidade_usuario": usuario_atual.cidade or "Sua Cidade" 
    }