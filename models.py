from sqlalchemy import Column, DateTime, Integer, String, Float, ForeignKey, func
from database import Base
from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from database import get_db
import os
import shutil

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
    categoria = Column(String)        # Ex: "lixo", "desmatamento"
    descricao = Column(String)        # Ex: "Entulho na calçada"
    latitude = Column(Float)          # Lat do GPS
    longitude = Column(Float)         # Lng do GPS
    foto_url = Column(String)         # Caminho de onde a foto foi salva
    status = Column(String, default="Pendente") # Pendente, Em Análise, Resolvida
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    # A "linha" que liga essa denúncia ao usuário que a fez
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))