from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext

import jwt
from datetime import datetime, timedelta, timezone

from database import engine, Base, get_db
import models
import schemas

# 1. Cria as tabelas no banco de dados (se não existirem)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoMonitor API")

# 2. Configura a criptografia de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 3. Libera o acesso do Frontend (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    
    # Passo C: Cria o usuário no banco de dados
    novo_usuario = models.Usuario(
        nome=usuario.nome, 
        email=usuario.email, 
        senha=senha_criptografada
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario) # Atualiza para pegar o ID que o banco gerou
    
    return {"mensagem": "Usuário criado com sucesso!", "usuario_id": novo_usuario.id}

# --- CONFIGURAÇÕES DO TOKEN ---
SECRET_KEY = "chave_secreta_do_tcc_da_vitoria" # No futuro guardamos isso no .env!
ALGORITHM = "HS256"

# 6. ROTA DE LOGIN 🔐
@app.post("/login")
def fazer_login(usuario_login: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    # Passo A: Procura o usuário no banco pelo email
    usuario_bd = db.query(models.Usuario).filter(models.Usuario.email == usuario_login.email).first()
    
    # Passo B: Verifica se o usuário existe e se a senha bate com a criptografada
    if not usuario_bd or not pwd_context.verify(usuario_login.senha, usuario_bd.senha):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos.")
    
    # Passo C: Gera a "Pulseira VIP" (Token JWT) com validade de 24 horas
    tempo_expiracao = datetime.now(timezone.utc) + timedelta(hours=24)
    dados_token = {"sub": str(usuario_bd.id), "exp": tempo_expiracao}
    token_jwt = jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": token_jwt, "token_type": "bearer", "usuario_id": usuario_bd.id}