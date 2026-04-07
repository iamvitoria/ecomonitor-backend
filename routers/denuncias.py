from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from database import get_db
import os
import shutil

router = APIRouter()

# Cria a pasta para salvar as fotos, se não existir
os.makedirs("uploads", exist_ok=True)

@router.post("/api/denuncias")
async def registrar_denuncia(
    usuario_id: int = Form(...),       
    categoria: str = Form(...),        # Alterado para string (texto)
    descricao: str = Form(""),         # Opcional
    latitude: float = Form(...),       
    longitude: float = Form(...),      
    foto: UploadFile = File(...),      
    db: Session = Depends(get_db)      # Injeção do banco de dados
):
    # 1. Salvar a foto localmente
    caminho_foto = f"uploads/{foto.filename}"
    with open(caminho_foto, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)
    
    # 2. Criar a denúncia no banco de dados
    nova_denuncia = Denuncia(
        categoria=categoria,
        descricao=descricao,
        latitude=latitude,
        longitude=longitude,
        foto_url=caminho_foto,
        usuario_id=usuario_id
    )
    db.add(nova_denuncia)
    
    # 3. Dar a recompensa (Gamificação)
    pontos_recompensa = 50
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario:
        usuario.pontuacao += pontos_recompensa
    
    db.commit()
    
    return {
        "status": "sucesso",
        "mensagem": "Denúncia registrada com sucesso!",
        "pontos_ganhos": pontos_recompensa
    }