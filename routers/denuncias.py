import shutil
import uuid
from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
import models

# IMPORTANTE: Puxamos a função que checa a "Pulseira VIP" (Token) lá do usuarios.py
from routers.usuarios import obter_usuario_atual
from schemas import DenunciaResposta

# Criamos o roteador para as denúncias
router = APIRouter(tags=["Denúncias"])

# ROTA DE CRIAR DENÚNCIA COM GPS E FOTO (Protegida! 🛡️)
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
    # Cria um nome único e salva a foto
    extensao = foto.filename.split(".")[-1]
    nome_arquivo = f"denuncia_{uuid.uuid4().hex}.{extensao}"
    caminho_foto = f"uploads/{nome_arquivo}"

    with open(caminho_foto, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)

    # Salva no banco
    nova_denuncia = models.Denuncia(
        categoria=categoria,
        descricao=descricao,
        latitude=latitude,
        longitude=longitude,
        foto_url=caminho_foto,
        usuario_id=usuario_atual.id
    )
    db.add(nova_denuncia)
    
    # Gamificação: 50 pontos!
    pontos_recompensa = 50
    usuario_atual.pontuacao += pontos_recompensa 
    
    db.commit()
    
    return {
        "status": "sucesso", 
        "mensagem": "Denúncia registrada com sucesso!", 
        "pontos_ganhos": pontos_recompensa
    }

@router.get("/minhas-denuncias", response_model=list[DenunciaResposta])
def listar_minhas_denuncias(
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_atual.id).all()
    return denuncias