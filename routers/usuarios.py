import os
from dotenv import load_dotenv
from sqlalchemy import func

from database import get_db

load_dotenv()

import jwt
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import text
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError
from auth import get_current_user, get_current_user_optional
import models
import schemas
import cloudinary
import cloudinary.uploader

cloudinary.config( 
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
    api_key = os.environ.get("CLOUDINARY_API_KEY"), 
    api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
    secure = True
)

router = APIRouter(tags=["Usuários"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get("SECRET_KEY", "chave_super_secreta_do_tcc_da_vitoria_2026_segura")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
oauth2_scheme_opcional = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

async def obter_usuario_opcional(
    token: str = Depends(oauth2_scheme_opcional),
    db: Session = Depends(get_db)
):
    if not token:
        return None  
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = str(payload.get("sub"))
        
        if usuario_id is None:
            return None
            
    except InvalidTokenError:
        return None
        
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    
    return usuario

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
        cidade=" ".join(usuario.cidade.strip().title().split()),
        senha=senha_criptografada,
        perfil="user",
        pontuacao=0
    )
    
    try:
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        return {"status": "sucesso", "mensagem": "Cadastrado!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno ao salvar: {str(e)}")
    
@router.post("/login")
def fazer_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario_bd = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    if not usuario_bd or not pwd_context.verify(form_data.password, usuario_bd.senha):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos.")
    
    tempo_expiracao = datetime.now(timezone.utc) + timedelta(hours=24)
    dados_token = {"sub": str(usuario_bd.id), "exp": tempo_expiracao}
    token_jwt = jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)
    
    print("Usuário autenticado:", usuario_bd.id, usuario_bd.email)
    return {"access_token": token_jwt, "token_type": "bearer", "usuario_id": usuario_bd.id, "perfil": usuario_bd.perfil}

@router.get("/perfil")
def ler_perfil(
    usuario_atual: models.Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):

    # ================= ADMIN =================
    if usuario_atual.perfil == "admin":
        resolvidas = db.query(models.Registro).filter(
            models.Registro.status == "Resolvido"
        ).count()

        pendentes = db.query(models.Registro).filter(
            models.Registro.status.notin_(["Resolvido", "Negado", "Cancelado"])
        ).count()

        return {
            "nome": usuario_atual.nome,
            "email": usuario_atual.email,
            "cargo": usuario_atual.cargo,
            "regiao": usuario_atual.cidade or "Santa Maria",
            "foto_perfil": usuario_atual.foto_perfil,
            "estatisticas": {
                "resolvidas": resolvidas,
                "pendentes": pendentes
            }
        }

    # ================= USUÁRIO =================

    posicao = db.query(models.Usuario).filter(
        models.Usuario.pontuacao > usuario_atual.pontuacao
    ).count() + 1

    total_registros = db.query(models.Registro).filter(
        models.Registro.usuarios_id == usuario_atual.id
    ).count()

    conquistas_do_usuario = db.query(models.Conquista).join(
        models.UsuarioConquista,
        models.Conquista.id == models.UsuarioConquista.conquista_id
    ).filter(
        models.UsuarioConquista.usuario_id == usuario_atual.id
    ).all()

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
        "total_registros": total_registros,
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
                c.pontos_adquiridos,
                CASE
                    WHEN uc.id IS NOT NULL THEN true
                    ELSE false
                END AS desbloqueado
            FROM conquistas c
            LEFT JOIN usuarios_conquistas uc
                ON c.id = uc.conquista_id
                AND uc.usuario_id = :usuario_id
            ORDER BY c.id ASC
        """)

        resultado = db.execute(
            query,
            {"usuario_id": usuario_atual.id}
        ).mappings().all()

        return [dict(row) for row in resultado]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.put("/perfil/editar")
async def editar_perfil(
    dados: schemas.EditarPerfilSchema, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Verifica se o e-mail que o usuário quer colocar já pertence a OUTRA pessoa
    if dados.email != usuario_atual.email:
        email_existente = db.query(models.Usuario).filter(models.Usuario.email == dados.email).first()
        if email_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está em uso por outra conta."
            )

    try:
        # Atualizações comuns para qualquer tipo de usuário
        usuario_atual.nome = dados.nome
        usuario_atual.email = dados.email
        usuario_atual.cidade = dados.cidade  

        # Proteção: Só atualiza a coluna cargo se quem estiver editando for um ADMIN
        if usuario_atual.perfil == "admin" and dados.cargo is not None:
            usuario_atual.cargo = dados.cargo

        db.add(usuario_atual)
        db.commit()      
        db.refresh(usuario_atual) 

        return {
            "status": "sucesso",
            "mensagem": "Perfil atualizado com sucesso!",
            "nome": usuario_atual.nome,
            "email": usuario_atual.email,
            "cidade": usuario_atual.cidade,
            "cargo": usuario_atual.cargo if usuario_atual.perfil == "admin" else None
        }
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar perfil: {e}")  # Ajuda no debug do console do terminal
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao salvar os dados no banco de dados."
        )


@router.put("/perfil/senha")
async def mudar_senha(
    dados: schemas.MudarSenhaSchema, 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(obter_usuario_atual)
):
    # Valida se a senha antiga bate com o hash salvo no banco
    if not pwd_context.verify(dados.senha_atual, usuario_atual.senha):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha atual inserida está incorreta."
        )
        
    try:
        # Encripta a nova senha antes de salvar
        usuario_atual.senha = pwd_context.hash(dados.nova_senha)
        db.add(usuario_atual)
        db.commit()
        
        return {
            "status": "sucesso", 
            "mensagem": "Senha alterada com sucesso!"
        }
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao mudar senha: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar a senha no banco de dados."
        )  

@router.get("/ranking")
def obter_ranking(
    cidade: str = None, 
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_current_user_optional) 
):
    try:
        # Recupera a cidade do usuário logado de forma segura (se ele existir)
        cidade_usuario_logado = usuario_atual.cidade if usuario_atual else None
        cidade_alvo = cidade or cidade_usuario_logado or "Desconhecida"
        
        usuarios_locais = db.query(models.Usuario).filter(
            models.Usuario.perfil == "user",
            models.Usuario.cidade == cidade_alvo
        ).order_by(models.Usuario.pontuacao.desc()).limit(10).all()
        
        lista_local = [
            {"nome": u.nome, "pontos": u.pontuacao, "foto_perfil": u.foto_perfil} 
            for u in usuarios_locais
        ]

        cidades_ranking = db.query(
            models.Usuario.cidade,
            func.count(models.Registro.id).label('total')
        ).join(
            models.Registro, models.Registro.usuarios_id == models.Usuario.id
        ).filter(
            models.Usuario.cidade.isnot(None)
        ).group_by(
            models.Usuario.cidade
        ).order_by(
            func.count(models.Registro.id).desc()
        ).limit(10).all()

        lista_global = [
            {"cidade": r.cidade, "total": r.total} 
            for r in cidades_ranking
        ]
            
        return {
            "local": lista_local,
            "global": lista_global,
            "cidade_buscada": cidade_alvo
        }
        
    except Exception as e:
        print(f"Erro ao buscar ranking: {e}") 
        raise HTTPException(status_code=500, detail="Erro interno ao buscar o ranking.")