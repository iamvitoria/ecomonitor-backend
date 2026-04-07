import shutil
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError

from database import get_db
import models
import schemas

# Criamos o roteador para os Usuários
router = APIRouter(tags=["Usuários"])

# --- 1. CONFIGURAÇÕES DE SEGURANÇA E TOKEN ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "chave_secreta_do_tcc_da_vitoria" # No futuro guardamos isso no .env!
ALGORITHM = "HS256"

# O "Segurança" da API: avisa o Swagger que usamos Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Função que verifica a Pulseira VIP (Token) - O denuncias.py usa isso!
def obter_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    excecao_credenciais = HTTPException(
        status_code=401,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = str(payload.get("sub"))
        if usuario_id is None:
            raise excecao_credenciais
    except InvalidTokenError:
        raise excecao_credenciais
        
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if usuario is None:
        raise excecao_credenciais
    return usuario


# --- 2. ROTA DE CADASTRO 🚀 ---
@router.post("/cadastro")
def criar_usuario(usuario: schemas.UsuarioCriar, db: Session = Depends(get_db)):
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este email já está cadastrado.")
    
    senha_criptografada = pwd_context.hash(usuario.senha)
    
    novo_usuario = models.Usuario(
        nome=usuario.nome, 
        email=usuario.email, 
        senha=senha_criptografada
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    return {"mensagem": "Usuário criado com sucesso!", "usuario_id": novo_usuario.id}


# --- 3. ROTA DE LOGIN 🔐 ---
@router.post("/login")
def fazer_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario_bd = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    if not usuario_bd or not pwd_context.verify(form_data.password, usuario_bd.senha):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos.")
    
    tempo_expiracao = datetime.now(timezone.utc) + timedelta(hours=24)
    dados_token = {"sub": str(usuario_bd.id), "exp": tempo_expiracao}
    token_jwt = jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": token_jwt, "token_type": "bearer", "usuario_id": usuario_bd.id}


# --- 4. ROTA DO PERFIL (Protegida! 🛡️) ---
@router.get("/perfil", response_model=schemas.UsuarioPerfil)
def ler_perfil(usuario_atual: models.Usuario = Depends(obter_usuario_atual)):
    return usuario_atual


# --- 5. ROTA PARA SUBIR FOTO DE PERFIL 📸 (Protegida! 🛡️) ---
@router.post("/perfil/foto")
def upload_foto(
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    extensao = foto.filename.split(".")[-1]
    nome_arquivo = f"foto_perfil_{usuario_atual.id}.{extensao}"
    caminho_completo = f"uploads/{nome_arquivo}"

    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)

    url_foto = f"https://ecomonitor-api.onrender.com/{caminho_completo}"
    usuario_atual.foto_perfil = url_foto
    db.commit()

    return {"mensagem": "Foto salva com sucesso!", "foto_perfil": url_foto}