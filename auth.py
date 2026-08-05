import os
from typing import Optional
import jwt
import models

from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from database import get_db

load_dotenv()

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

SECRET_KEY = os.environ.get("SECRET_KEY", "chave_super_secreta_do_tcc_da_vitoria_2026_segura")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

oauth2_scheme_opcional = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
):
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("sub")
        
        if usuario_id is None:
            return None
            
        usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
        return usuario
    except Exception:
        return None