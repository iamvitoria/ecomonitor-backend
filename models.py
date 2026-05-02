from sqlalchemy import Column, DateTime, Integer, String, Float, ForeignKey, func
from database import Base
from sqlalchemy.orm import relationship

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True, index=True)
    senha = Column(String)
    perfil = Column(String, default="user")
    pontuacao = Column(Integer, default=0)
    foto_perfil = Column(String, nullable=True)
    regiao = Column(String, nullable=True)
    denuncias = relationship("Denuncia", viewonly=True)
    @property
    def contribuicoes(self):
        return len(self.denuncias)

class Denuncia(Base):
    __tablename__ = "denuncias"
    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String)        
    descricao = Column(String)        
    latitude = Column(Float)          
    longitude = Column(Float)         
    foto_url = Column(String)         
    status = Column(String, default="Em análise")
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    usuario = relationship("Usuario")
    
class HistoricoDenuncia(Base):
    __tablename__ = "historico_denuncias"
    id = Column(Integer, primary_key=True, index=True)
    denuncia_id = Column(Integer, ForeignKey("denuncias.id"))
    texto = Column(String)
    data_registro = Column(DateTime(timezone=True), server_default=func.now())
    
class Conquista(Base):
    __tablename__ = "conquistas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    descricao = Column(String)
    pontos_necessarios = Column(Integer)
    icone_url = Column(String)

class UsuarioConquista(Base):
    __tablename__ = "usuarios_conquistas"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    conquista_id = Column(Integer, ForeignKey("conquistas.id"), nullable=False)
    data_desbloqueio = Column(DateTime(timezone=True), server_default=func.now())  