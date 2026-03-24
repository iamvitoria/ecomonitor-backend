from pydantic import BaseModel

class UsuarioCriar(BaseModel):
    nome: str
    email: str
    senha: str
    
class UsuarioLogin(BaseModel):
    email: str
    senha: str
    
# Como os dados do usuário vão aparecer no Perfil do App (sem a senha!)
class UsuarioPerfil(BaseModel):
    id: int
    nome: str
    email: str
    pontuacao: int

    class Config:
        from_attributes = True # Isso ajuda o FastAPI a ler direto do banco de dados