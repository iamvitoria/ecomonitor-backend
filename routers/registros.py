import utils
from sqlalchemy import func
import models
import schemas
from routers.usuarios import obter_usuario_atual, obter_usuario_opcional
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from database import get_db
from typing import List, Optional
from routers.usuarios import obter_usuario_atual
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="ecomonitor")

import cloudinary
import cloudinary.uploader

router = APIRouter(tags=["Registros"])

@router.get("/registros")
def listar_todos_registros(db: Session = Depends(get_db)):

    registros = (
        db.query(models.Registro)
        .options(
            joinedload(models.Registro.endereco),
            joinedload(models.Registro.categoria),
            joinedload(models.Registro.usuario)   
        )
        .all()
    )

    resultado = []

    for r in registros:
        resultado.append({
            "id": r.id,
            "descricao": r.descricao,
            "status": r.status,
            "data_criacao": r.data_criacao,
            "latitude": r.endereco.latitude if r.endereco else None,
            "longitude": r.endereco.longitude if r.endereco else None,
            "categoria": {
                "id": r.categoria.id,
                "nome": r.categoria.nome
            } if r.categoria else None,
            "usuario_nome": r.usuario.nome if r.usuario else None,
            "endereco": {
                "logradouro": r.endereco.logradouro,
                "numero": r.endereco.numero,
                "bairro": r.endereco.bairro,
                "cidade": r.endereco.cidade
            } if r.endereco else None
        })

    return resultado

def geocoding(endereco):
    try:
        location = geolocator.geocode(endereco)

        if location:
            print("Endereço encontrado:", endereco)
            print("Latitude:", location.latitude)
            print("Longitude:", location.longitude)

            return location.latitude, location.longitude

        print("Endereço não encontrado:", endereco)

    except Exception as e:
        print("Erro no geocoding:", e)

    return None, None

@router.post("/registros")
async def criar_registro(
    categoria_id: int = Form(...),
    descricao: str = Form(""),
    cep: str = Form(...),
    logradouro: str = Form(...),
    numero: str = Form(...),
    complemento: str = Form(None),
    bairro: str = Form(...),
    cidade: str = Form(...),
    referencia: str = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    anonimo: Optional[bool] = Form(False),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    usuario_atual: Optional[models.Usuario] = Depends(obter_usuario_opcional) 
):
    categoria = db.query(models.Categoria).filter(
        models.Categoria.id == categoria_id
    ).first()

    if not categoria:
        raise HTTPException(400, "Categoria inválida")

    foto_url = None

    if foto and foto.filename:
        try:
            resultado = cloudinary.uploader.upload(
                foto.file,
                folder="ecomonitor/registros"
            )
            foto_url = resultado.get("secure_url")

        except Exception:
            raise HTTPException(500, "Erro ao enviar imagem")

    # ------------------------------------
    # GEOCODIFICAÇÃO DO ENDEREÇO
    # ------------------------------------
    endereco_texto = f"{logradouro}, {numero}, {bairro}, {cidade}"

    lat_geo, lon_geo = geocoding(endereco_texto)
    
    print("====================================")
    print("ENDEREÇO ENVIADO:", endereco_texto)
    print("LAT:", lat_geo)
    print("LON:", lon_geo)
    print("====================================")

    if lat_geo is not None and lon_geo is not None:
        latitude = lat_geo
        longitude = lon_geo

    # ------------------------------------

    novo_endereco = models.Endereco(
        cep=cep,
        logradouro=logradouro,
        numero=numero,
        complemento=complemento,
        bairro=bairro,
        cidade=cidade,
        referencia=referencia,
        latitude=latitude,
        longitude=longitude
    )

    db.add(novo_endereco)
    db.flush()


    novo_registro = models.Registro(
        categoria_id=categoria.id,
        usuarios_id=usuario_atual.id if usuario_atual else None, 
        endereco_id=novo_endereco.id,
        descricao=descricao,
        foto_url=foto_url
    )

    db.add(novo_registro)
    db.flush()

    novo_historico = models.HistoricoRegistro(
        registro_id=novo_registro.id,
        texto="Registro criado de forma anônima" if not usuario_atual else "Registro criado",
        status_novo="Em análise"
    )

    db.add(novo_historico)

    if usuario_atual:
        usuario_atual.pontuacao += 50
        utils.verificar_conquistas(
            usuario_atual.id,
            db,
            registro_id=novo_registro.id
        )

    db.commit()

    return {
        "status": "sucesso",
        "mensagem": "Registro criado com sucesso"
    }

@router.put("/registros/{registro_id}")
async def editar_registro(
    registro_id: int,
    categoria_id: int = Form(...),
    descricao: str = Form(""),
    logradouro: str = Form(None),
    numero: str = Form(None),
    bairro: str = Form(None),
    cidade: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    foto: UploadFile = File(None),
    db: Session = Depends(get_db),
    # 1. MUDANÇA AQUI: usuario opcional
    usuario_atual: Optional[models.Usuario] = Depends(obter_usuario_opcional) 
):
    registro = db.query(models.Registro).options(
        joinedload(models.Registro.endereco)
    ).filter(
        models.Registro.id == registro_id
    ).first()

    if not registro:
        raise HTTPException(404, "Registro não encontrado")

    # 2. MUDANÇA AQUI: Só bloqueia se o registro tiver um dono E o dono for diferente
    if registro.usuarios_id is not None:
        if not usuario_atual or registro.usuarios_id != usuario_atual.id:
            raise HTTPException(403, "Sem permissão para editar este registro")

    registro.categoria_id = categoria_id
    registro.descricao = descricao

    if registro.endereco:
        if logradouro is not None:
            registro.endereco.logradouro = logradouro

        if numero is not None:
            registro.endereco.numero = numero

        if bairro is not None:
            registro.endereco.bairro = bairro

        if cidade is not None:
            registro.endereco.cidade = cidade

        # ------------------------------------
        # GEOCODIFICAÇÃO
        # ------------------------------------
        if logradouro and cidade:
            endereco_texto = (
                f"{registro.endereco.logradouro}, "
                f"{registro.endereco.numero}, "
                f"{registro.endereco.bairro}, "
                f"{registro.endereco.cidade}"
            )
            lat_geo, lon_geo = geocoding(endereco_texto)

            if lat_geo is not None and lon_geo is not None:
                registro.endereco.latitude = lat_geo
                registro.endereco.longitude = lon_geo
            else:
                if latitude is not None:
                    registro.endereco.latitude = latitude
                if longitude is not None:
                    registro.endereco.longitude = longitude
        else:
            if latitude is not None:
                registro.endereco.latitude = latitude
            if longitude is not None:
                registro.endereco.longitude = longitude

    if foto and foto.filename:
        try:
            resultado = cloudinary.uploader.upload(
                foto.file,
                folder="ecomonitor/registros"
            )
            registro.foto_url = resultado.get("secure_url")
        except Exception:
            raise HTTPException(500, "Erro ao enviar imagem")

    db.add(models.HistoricoRegistro(
        registro_id=registro.id,
        texto="Registro anônimo editado" if registro.usuarios_id is None else "Registro editado"
    ))

    db.commit()

    return {
        "mensagem": "Registro atualizado com sucesso",
        "registro": {
            "id": registro.id,
            "categoria_id": registro.categoria_id,
            "descricao": registro.descricao,
            "foto_url": registro.foto_url,
            "latitude": registro.endereco.latitude if registro.endereco else None,
            "longitude": registro.endereco.longitude if registro.endereco else None,
            "endereco": {
                "logradouro": registro.endereco.logradouro if registro.endereco else "",
                "numero": registro.endereco.numero if registro.endereco else "",
                "bairro": registro.endereco.bairro if registro.endereco else "",
                "cidade": registro.endereco.cidade if registro.endereco else ""
            }
        }
    }
    
@router.get("/meus-registros", response_model=List[schemas.RegistroResposta])
def listar_meus_registros(
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    registros = db.query(models.Registro).options(
        joinedload(models.Registro.categoria),
        joinedload(models.Registro.endereco)
    ).filter(
        models.Registro.usuarios_id == usuario_atual.id
    ).all()

    return registros

@router.put("/registros/{id}/status")
def atualizar_status(
    id: int,
    novo_status: str,
    db: Session = Depends(get_db)
):
    registro = db.query(models.Registro).filter(
        models.Registro.id == id
    ).first()

    if not registro:
        raise HTTPException(404, "Registro não encontrado")

    status_anterior = registro.status
    registro.status = novo_status

    db.add(models.HistoricoRegistro(
        registro_id=id,
        status_anterior=status_anterior,
        status_novo=novo_status,
        texto=f"Status alterado de {status_anterior} para {novo_status}"
    ))

    db.commit()

    return {"mensagem": "Status atualizado"}

@router.get("/registros/{id}/historico")
def obter_historico_registro(
    id: int, 
    db: Session = Depends(get_db)
):
    registro = db.query(models.Registro).filter(models.Registro.id == id).first()
    if not registro:
        raise HTTPException(404, "Registro não encontrado")

    historico = db.query(models.HistoricoRegistro).filter(
        models.HistoricoRegistro.registro_id == id 
    ).order_by(models.HistoricoRegistro.id.desc()).all()
    
    return historico

@router.get("/registros/{registro_id}")
def obter_registro_por_id(registro_id: int, db: Session = Depends(get_db)):
    registro = (
        db.query(models.Registro)
        .options(
            joinedload(models.Registro.endereco),
            joinedload(models.Registro.categoria),
            joinedload(models.Registro.usuario)   
        )
        .filter(models.Registro.id == registro_id)
        .first()
    )

    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")

    return {
        "id": registro.id,
        "descricao": registro.descricao,
        "status": registro.status,
        "data_criacao": registro.data_criacao,
        "foto_url": registro.foto_url,
        "latitude": registro.endereco.latitude if registro.endereco else None,
        "longitude": registro.endereco.longitude if registro.endereco else None,
        "categoria": {
            "id": registro.categoria.id,
            "nome": registro.categoria.nome
        } if registro.categoria else None,
        "usuario": {
            "nome": registro.usuario.nome if registro.usuario else "Não identificado",
            "regiao": getattr(registro.usuario, 'regiao', 'Não informada') if registro.usuario else "Não informada",
            "contribuicoes": getattr(registro.usuario, 'pontuacao', 0) if registro.usuario else 0
        },
        "endereco": {
            "logradouro": registro.endereco.logradouro,
            "numero": registro.endereco.numero,
            "bairro": registro.endereco.bairro,
            "cidade": registro.endereco.cidade
        } if registro.endereco else None
    }