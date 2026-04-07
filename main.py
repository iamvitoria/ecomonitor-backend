import os
import shutil
import uuid
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError

from database import engine, Base, get_db
import models
import schemas

# (Opcional) Se tiver rotas separadas num ficheiro routes.py
try:
    from routes import router
    HAS_ROUTER = True
except ImportError:
    HAS_ROUTER = False

# 1. Cria as tabelas no banco de dados (se não existirem)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoMonitor API")

if HAS_ROUTER:
    app.include_router(router)

# Cria a pasta 'uploads' se ela não existir
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# "Libera" a pasta uploads para a internet ver as fotos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 2. Configura a criptografia de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 3. Libera o acesso do Frontend (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Rota de Teste
@app.get("/")
def home():
    return {"status": "sucesso", "mensagem": "API do EcoMonitor online!"}

# 5. ROTA DE CADASTRO 🚀
@app.post("/cadastro")
def criar_usuario(usuario: schemas.UsuarioCriar, db: Session = Depends(get_db)):
    # Passo A: Verifica se o email já está cadastrado
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este email já está cadastrado.")
    
    # Passo B: Criptografa a senha antes de salvar
    senha_criptografada = pwd_context.hash(usuario.senha)
    
    # Passo C: Cria o utilizador no banco de dados
    novo_usuario = models.Usuario(
        nome=usuario.nome, 
        email=usuario.email, 
        senha=senha_criptografada
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    return {"mensagem": "Usuário criado com sucesso!", "usuario_id": novo_usuario.id}

# --- CONFIGURAÇÕES DO TOKEN ---
SECRET_KEY = "chave_secreta_do_tcc_da_vitoria" # No futuro guardamos isso no .env!
ALGORITHM = "HS256"

# O "Segurança" da API: avisa o Swagger que usamos Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Função que verifica a Pulseira VIP (Token)
def obter_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    excecao_credenciais = HTTPException(
        status_code=401,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Abre o token para ler o ID do utilizador (o "sub")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = str(payload.get("sub"))
        if usuario_id is None:
            raise excecao_credenciais
    except InvalidTokenError:
        raise excecao_credenciais
        
    # Busca o utilizador no banco para confirmar que ele existe
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if usuario is None:
        raise excecao_credenciais
    return usuario

# 6. ROTA DE LOGIN 🔐
@app.post("/login")
def fazer_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario_bd = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    if not usuario_bd or not pwd_context.verify(form_data.password, usuario_bd.senha):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos.")
    
    tempo_expiracao = datetime.now(timezone.utc) + timedelta(hours=24)
    dados_token = {"sub": str(usuario_bd.id), "exp": tempo_expiracao}
    token_jwt = jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": token_jwt, "token_type": "bearer", "usuario_id": usuario_bd.id}

# 7. ROTA DO PERFIL (Protegida! 🛡️)
@app.get("/perfil", response_model=schemas.UsuarioPerfil)
def ler_perfil(usuario_atual: models.Usuario = Depends(obter_usuario_atual)):
    return usuario_atual

# 8. ROTA DE CRIAR DENÚNCIA COM GPS E FOTO (Protegida! 🛡️)
@app.post("/denuncias")
async def criar_denuncia(
    categoria: str = Form(...),
    descricao: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual) # Exige a Pulseira VIP!
):
    # 1. Cria um nome único para a foto da denúncia (para não sobrescrever outras fotos)
    extensao = foto.filename.split(".")[-1]
    nome_arquivo = f"denuncia_{uuid.uuid4().hex}.{extensao}"
    caminho_foto = f"uploads/{nome_arquivo}"

    # 2. Salva o ficheiro fisicamente na pasta 'uploads'
    with open(caminho_foto, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)

    # 3. Cria a denúncia no banco de dados
    nova_denuncia = models.Denuncia(
        categoria=categoria,
        descricao=descricao,
        latitude=latitude,
        longitude=longitude,
        foto_url=caminho_foto,
        usuario_id=usuario_atual.id # Liga a denúncia ao utilizador logado de forma segura!
    )
    db.add(nova_denuncia)
    
    # 4. A MÁGICA DA GAMIFICAÇÃO: Atribuir 50 pontos por reportar com foto e GPS!
    pontos_recompensa = 50
    usuario_atual.pontuacao += pontos_recompensa 
    
    db.commit()
    
    return {
        "status": "sucesso", 
        "mensagem": "Denúncia registada com sucesso!", 
        "pontos_ganhos": pontos_recompensa
    }

# 9. ROTA PARA VER MINHAS DENÚNCIAS (Protegida! 🛡️)
@app.get("/minhas-denuncias")
def listar_minhas_denuncias(
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_atual.id).all()
    return denuncias

# 10. ROTA PARA SUBIR FOTO DE PERFIL 📸 (Protegida! 🛡️)
@app.post("/perfil/foto")
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