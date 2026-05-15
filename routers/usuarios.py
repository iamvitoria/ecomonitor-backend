import shutil
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import text
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError

from database import get_db
import models
import schemas
import cloudinary
import cloudinary.uploader

cloudinary.config( 
  cloud_name = "drt17bkgy", 
  api_key = "249219188561177", 
  api_secret = "nswH3-yGrgpboBiAGnNYQ0SwYn0",
  secure = True
)

router = APIRouter(tags=["Usuários"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "chave_secreta_do_tcc_da_vitoria" 
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

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


@router.post("/cadastro")
def criar_usuario(usuario: schemas.UsuarioCriar, db: Session = Depends(get_db)):
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este email já está cadastrado.")
    
    senha_criptografada = pwd_context.hash(usuario.senha)
    
    novo_usuario = models.Usuario(
        nome=usuario.nome, 
        email=usuario.email, 
        senha=senha_criptografada,
        perfil="user"
    )
    
    try:
        db.add(novo_usuario)
        db.commit()
        
        return {"status": "sucesso", "mensagem": "Cadastrado!"}
        
    except Exception as e:
        db.rollback()
        print(f"ERRO NO COMMIT: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar.")

@router.post("/login")
def fazer_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario_bd = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    if not usuario_bd or not pwd_context.verify(form_data.password, usuario_bd.senha):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos.")
    
    tempo_expiracao = datetime.now(timezone.utc) + timedelta(hours=24)
    dados_token = {"sub": str(usuario_bd.id), "exp": tempo_expiracao}
    token_jwt = jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": token_jwt, "token_type": "bearer", "usuario_id": usuario_bd.id, "perfil": usuario_bd.perfil}

@router.get("/perfil")
def ler_perfil(usuario_atual: models.Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    posicao = db.query(models.Usuario).filter(models.Usuario.pontuacao > usuario_atual.pontuacao).count() + 1
    
    total_denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_atual.id).count()
    
    conquistas_sistema = db.query(models.Conquista).all()
    for conquista in conquistas_sistema:
        if usuario_atual.pontuacao >= conquista.pontos_adquiridos:
            ja_possui = db.query(models.UsuarioConquista).filter(
                models.UsuarioConquista.usuario_id == usuario_atual.id,
                models.UsuarioConquista.conquista_id == conquista.id
            ).first()
            
            if not ja_possui:
                try:
                    nova_ligacao = models.UsuarioConquista(
                        usuario_id=usuario_atual.id,
                        conquista_id=conquista.id
                    )
                    db.add(nova_ligacao)
                    db.commit() 
                except Exception:
                    db.rollback()

    conquistas_do_usuario = db.query(models.Conquista).join(
        models.UsuarioConquista, models.Conquista.id == models.UsuarioConquista.conquista_id
    ).filter(models.UsuarioConquista.usuario_id == usuario_atual.id).all()

    nomes_vistos = set()
    lista_formatada = []

    for c in conquistas_do_usuario:
        if c.nome not in nomes_vistos:
            lista_formatada.append({
                "nome": c.nome,
                "descricao": c.descricao,
                "pontos": c.pontos_adquiridos 
            })
            nomes_vistos.add(c.nome)

    return {
        "nome": usuario_atual.nome,
        "email": usuario_atual.email,
        "pontuacao": usuario_atual.pontuacao,
        "foto_perfil": usuario_atual.foto_perfil,
        "posicao_ranking": posicao,
        "cidade": usuario_atual.cidade, 
        "total_denuncias": total_denuncias, 
        "conquistas": lista_formatada 
    }
@router.post("/perfil/foto")
def upload_foto(
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    try:
        resultado = cloudinary.uploader.upload(
            foto.file, 
            folder="ecomonitor/perfis",
            public_id=f"user_{usuario_atual.id}"
        )

        url_foto = resultado.get("secure_url")

        usuario_atual.foto_perfil = url_foto
        db.commit()

        return {
            "mensagem": "Foto salva com sucesso!", 
            "foto_perfil": url_foto
        }

    except Exception as e:
        print(f"Erro ao subir para Cloudinary: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar imagem.")
    
@router.get("/conquistas")
def listar_conquistas(
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    try:
        query = text("""
            SELECT 
                c.id, 
                c.nome, 
                c.descricao, 
                c.icone_url,
                CASE WHEN uc.id IS NOT NULL THEN true ELSE false END AS desbloqueado
            FROM conquistas c
            LEFT JOIN usuarios_conquistas uc 
                ON c.id = uc.conquista_id AND uc.usuario_id = :usuario_id
            ORDER BY c.pontos_necessarios ASC;
        """)
        
        resultado = db.execute(query, {"usuario_id": usuario_atual.id}).mappings().all()
        return [dict(row) for row in resultado]

    except Exception as e:
        print(f"Erro ao buscar conquistas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao carregar conquistas.")

def verificar_e_dar_conquista(usuario_id: int, conquista_id: int, db: Session):
    ja_possui = db.query(models.UsuarioConquista).filter(
        models.UsuarioConquista.usuario_id == usuario_id,
        models.UsuarioConquista.conquista_id == conquista_id
    ).first()

    if not ja_possui:
        nova_conquista = models.UsuarioConquista(
            usuario_id=usuario_id, 
            conquista_id=conquista_id
        )
        db.add(nova_conquista)
        return True
    return False

@router.put("/perfil/editar")
async def editar_perfil(
    dados: schemas.EditarPerfilSchema, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verifica se o e-mail que ele quer mudar já não pertence a outra pessoa
    if dados.email != usuario_atual.email:
        email_existente = db.query(models.Usuario).filter(models.Usuario.email == dados.email).first()
        if email_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está em uso por outra conta."
            )

    try:
        # Atualiza os campos do usuário logado diretamente com os dados recebidos do Pop-up
        usuario_atual.nome = dados.nome
        usuario_atual.email = dados.email
        usuario_atual.cidade = dados.cidade  # Salva o texto livre digitado no React

        db.add(usuario_atual)
        db.commit()      # Grava de fato no banco de dados
        db.refresh(usuario_atual) 

        return {
            "status": "sucesso",
            "mensagem": "Perfil atualizado com sucesso!",
            "nome": usuario_atual.nome,
            "email": usuario_atual.email,
            "cidade": usuario_atual.cidade
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao salvar os dados no banco de dados."
        )