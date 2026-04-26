from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

class UsuarioCriar(BaseModel):
    nome: str
    email: str
    senha: str
    
class UsuarioLogin(BaseModel):
    email: str
    senha: str
    
class UsuarioPerfil(BaseModel):
    id: int
    nome: str
    email: str
    pontuacao: int
    foto_perfil: str | None = None 

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
    descricao: str
    latitude: float
    longitude: float
    foto_url: str
    status: str
    usuario_id: int
    data_criacao: datetime
    historico: List[HistoricoResposta] = []

    class Config:
        from_attributes = True

class AcaoResposta(BaseModel):
    id: int
    nome_acao: str
    pontos_ganhos: int
    usuario_id: int

    class Config:
        from_attributes = True