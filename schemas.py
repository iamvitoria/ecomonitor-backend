from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class CategoriaEnum(str, Enum):
    lixo = "Descarte Irregular de Lixo"
    desmatamento = "Desmatamento"
    poluicao_agua = "Poluição da Água"
    queimada = "Queimada"
    poluicao_ar = "Poluição do Ar"
    animais = "Maus-tratos Animais"
    foco_mosquito = "Foco de Mosquito"
    esgoto = "Esgoto Aberto"

class UsuarioResumo(BaseModel):
    id: Optional[int] = None
    nome: Optional[str] = "Anônimo"
    regiao: Optional[str] = "Santa Maria"
    contribuicoes: Optional[int] = 0
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
    descricao: Optional[str] = ""
    status: str
    data_criacao: datetime
    foto_url: Optional[str] = None
    latitude: float
    longitude: float
    usuario_id: Optional[int] = None
    usuario: Optional[UsuarioResumo] = None
    historico: List[HistoricoResposta] = []

    class Config:
        from_attributes = True

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
    pontuacao: Optional[int] = 0
    foto_perfil: Optional[str] = None 
    regiao: Optional[str] = "Santa Maria"
    class Config:
        from_attributes = True