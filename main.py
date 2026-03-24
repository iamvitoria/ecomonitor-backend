from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

import jwt
from datetime import datetime, timedelta, timezone

from database import engine, Base, get_db
import models
import schemas

# 1. Cria as tabelas no banco de dados (se não existirem)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoMonitor API")

# --- CONFIGURAÇÃO DO CORS (A Ponte entre o React e o Backend) ---
# Permite que o frontend converse com a nossa API sem ser bloqueado pelo navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # O "*" permite qualquer origem (perfeito para a fase de testes local)
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"], # Permite todos os cabeçalhos (incluindo o nosso Token JWT)
)

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
        # Abre o token para ler o ID do usuário (o "sub")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = str(payload.get("sub"))
        if usuario_id is None:
            raise excecao_credenciais
    except InvalidTokenError:
        raise excecao_credenciais
        
    # Busca o usuário no banco para confirmar que ele existe
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if usuario is None:
        raise excecao_credenciais
    return usuario

# 6. ROTA DE LOGIN 🔐 (Atualizada para o Cadeado do Swagger)
@app.post("/login")
def fazer_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # O cadeado do Swagger sempre manda o email dentro de um campo chamado "username"
    usuario_bd = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    # Verifica se o usuário existe e se a senha bate
    if not usuario_bd or not pwd_context.verify(form_data.password, usuario_bd.senha):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos.")
    
    # Gera a "Pulseira VIP" (Token JWT)
    tempo_expiracao = datetime.now(timezone.utc) + timedelta(hours=24)
    dados_token = {"sub": str(usuario_bd.id), "exp": tempo_expiracao}
    token_jwt = jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": token_jwt, "token_type": "bearer", "usuario_id": usuario_bd.id}

# 7. ROTA DO PERFIL (Protegida! 🛡️)
@app.get("/perfil", response_model=schemas.UsuarioPerfil)
def ler_perfil(usuario_atual: models.Usuario = Depends(obter_usuario_atual)):
    # Se o FastAPI chegou até aqui, é porque o Token era válido!
    # Então, é só devolver os dados do usuário.
    return usuario_atual

# 8. ROTA DE CRIAR DENÚNCIA (Protegida! 🛡️)
@app.post("/denuncias", response_model=schemas.DenunciaResposta)
def criar_denuncia(
    denuncia: schemas.DenunciaCriar, 
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual) # Exige a Pulseira VIP!
):
    # Cria a denúncia no banco de dados
    nova_denuncia = models.Denuncia(
        titulo=denuncia.titulo,
        descricao=denuncia.descricao,
        localizacao=denuncia.localizacao,
        usuario_id=usuario_atual.id # Liga a denúncia ao usuário logado
    )
    db.add(nova_denuncia)
    
    # Bônus: O usuário ganha 10 pontos de "Cidadão Consciente" por ajudar!
    usuario_atual.pontuacao += 10 
    
    db.commit()
    db.refresh(nova_denuncia)
    
    return nova_denuncia

# 9. ROTA PARA VER MINHAS DENÚNCIAS (Protegida! 🛡️)
@app.get("/minhas-denuncias", response_model=list[schemas.DenunciaResposta])
def listar_minhas_denuncias(
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Vai no banco e busca só as denúncias que tem o ID do usuário logado
    denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_atual.id).all()
    return denuncias