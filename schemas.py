from datetime import datetime
from pydantic import BaseModel, EmailStr, computed_field
from typing import List, Optional

class UsuarioResumo(BaseModel):
    id: Optional[int] = None
    nome: Optional[str] = "Anônimo"
    cidade: Optional[str] = "Santa Maria"
    
    @computed_field
    def contribuicoes(self) -> int:
        return 0

    class Config:
        from_attributes = True

class HistoricoResposta(BaseModel):
    id: int
    texto: str
    data_registro: datetime
    class Config:
        from_attributes = True

class DenunciaResposta(BaseModel):
    id: int
    categoria: str
    descricao: Optional[str] = None
    latitude: float
    longitude: float
    endereco: Optional[str] = None
    foto_url: Optional[str] = None
    status: str
    data_criacao: datetime
    usuario_id: Optional[int] = None
    usuario: Optional[UsuarioResumo] = None

    class Config:
        from_attributes = True

class UsuarioCriar(BaseModel):
    nome: str
    email: str
    cidade: str
    senha: str

class UsuarioLogin(BaseModel):
    email: str
    senha: str

class UsuarioPerfil(BaseModel):
    id: int
    nome: str
    email: str
    pontuacao: Optional[int] = 0
    foto_perfil: Optional[str] = None 
    regiao: Optional[str] = "Santa Maria"
    class Config:
        from_attributes = True
        
class EditarPerfilSchema(BaseModel):
    nome: str
    email: EmailStr
    cidade: str    
    cargo: Optional[str] = None

class MudarSenhaSchema(BaseModel):
    senha_atual: str
    nova_senha: str  