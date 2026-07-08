from datetime import datetime
from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional

class UsuarioResumo(BaseModel):
    id: Optional[int] = None
    nome: Optional[str] = "Anônimo"
    cidade: Optional[str] = None

    @computed_field
    def contribuicoes(self) -> int:
        return 0

    class Config:
        from_attributes = True


class CategoriaResposta(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True


class EnderecoResposta(BaseModel):
    id: int
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    cep: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    complemento: Optional[str] = None
    referencia: Optional[str] = None

    class Config:
        orm_mode = True

class HistoricoRegistroResposta(BaseModel):
    id: int
    status_anterior: Optional[str] = None
    status_novo: Optional[str] = None
    texto: str
    data_registro: datetime

    class Config:
        from_attributes = True


class RegistroResposta(BaseModel):
    id: int
    descricao: Optional[str] = None
    foto_url: Optional[str] = None
    status: str
    data_criacao: datetime

    categoria_id: Optional[int] = None
    usuarios_id: int
    endereco_id: Optional[int] = None

    categoria: Optional[CategoriaResposta] = None
    usuario: Optional[UsuarioResumo] = None
    endereco: Optional[EnderecoResposta] = None

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
    cidade: Optional[str] = None
    cargo: Optional[str] = None

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