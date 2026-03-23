from sqlalchemy import Column, Integer, String
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False) # Aqui vamos guardar a senha criptografada!
    pontuacao = Column(Integer, default=0) # Todo mundo começa com 0 pontos