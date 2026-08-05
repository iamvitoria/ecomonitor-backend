import os
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

import models
from database import get_db

SECRET_KEY = os.environ.get("SECRET_KEY", "chave_super_secreta_do_tcc_da_vitoria_2026_segura")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

oauth2_scheme_opcional = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Use em rotas que EXIGEM que o usuário esteja logado (ex: Editar Perfil)."""
    credenciais_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais (Token inválido ou expirado).",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_identificador = payload.get("sub")
        
        if usuario_identificador is None:
            raise credenciais_exception
            
    except InvalidTokenError:
        raise credenciais_exception
        
    user = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_identificador)).first()
    
    if user is None:
        raise credenciais_exception
        
    return user

def get_current_user_optional(token: str = Depends(oauth2_scheme_opcional), db: Session = Depends(get_db)):
    """Use em rotas PÚBLICAS onde o usuário pode ou não estar logado (ex: Ranking)."""
    if not token:
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_identificador = payload.get("sub")
        
        if usuario_identificador is None:
            return None
            
    except InvalidTokenError:
        return None
        
    user = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_identificador)).first()
    
    return user