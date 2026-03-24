from pydantic import BaseModel

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
               
# O que o React vai enviar quando o usuário preencher o formulário de denúncia
class DenunciaCriar(BaseModel):
    titulo: str
    descricao: str
    localizacao: str

# O que o Backend vai devolver e mostrar no App
class DenunciaResposta(BaseModel):
    id: int
    titulo: str
    descricao: str
    localizacao: str
    status: str
    usuario_id: int

    class Config:
        from_attributes = True

# O que o Backend vai devolver (como recibo)
class AcaoResposta(BaseModel):
    id: int
    nome_acao: str
    pontos_ganhos: int
    usuario_id: int

    class Config:
        from_attributes = True