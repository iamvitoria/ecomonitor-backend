from pydantic import BaseModel

# Isso define o que esperamos receber do frontend quando alguém se cadastra
class UsuarioCriar(BaseModel):
    nome: str
    email: str
    senha: str