from sqlalchemy import Column, Integer, String
from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True, index=True)
    senha = Column(String)
    pontuacao = Column(Integer, default=0)
    foto_perfil = Column(String, nullable=True) 
       
# --- Tabela de Denúncias Ambientais ---
class Denuncia(Base):
    __tablename__ = "denuncias"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String)       # Ex: "Lixo acumulado na calçada"
    descricao = Column(String)    # Ex: "Tem muito lixo na rua X, esquina com a Y"
    localizacao = Column(String)  # Ex: "Rua das Flores, 123"
    status = Column(String, default="Pendente") # Pendente, Em Análise, Resolvida
    
    # A "linha" que liga essa denúncia ao usuário que a fez!
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))