from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey, func, Float
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
    cidade = Column(String, nullable=True)
    cargo = Column(String, nullable=True, default="")

    registros = relationship(
        "Registro",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )

    conquistas = relationship(
        "UsuarioConquista",
        back_populates="usuario",
        cascade="all, delete-orphan"
    )

    @property
    def contribuicoes(self):
        return len(self.registros) if self.registros else 0


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)

    registros = relationship(
        "Registro",
        back_populates="categoria"
    )


class Endereco(Base):
    __tablename__ = "enderecos"

    id = Column(Integer, primary_key=True, index=True)
    cep = Column(String)
    logradouro = Column(String)
    numero = Column(String)
    complemento = Column(String, nullable=True)
    bairro = Column(String)
    cidade = Column(String)
    referencia = Column(String, nullable=True)
    latitude = Column(Float)
    longitude = Column(Float)

    registros = relationship(
        "Registro",
        back_populates="endereco"
    )


class Registro(Base):
    __tablename__ = "registros"

    id = Column(Integer, primary_key=True, index=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    usuarios_id = Column(Integer, ForeignKey("usuarios.id"))
    endereco_id = Column(Integer, ForeignKey("enderecos.id"))

    descricao = Column(String)
    foto_url = Column(String)
    status = Column(String, default="Em análise")
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship(
        "Usuario",
        back_populates="registros"
    )

    categoria = relationship(
        "Categoria",
        back_populates="registros"
    )

    endereco = relationship(
        "Endereco",
        back_populates="registros"
    )

    historicos = relationship(
        "HistoricoRegistro",
        back_populates="registro",
        cascade="all, delete-orphan"
    )


class HistoricoRegistro(Base):
    __tablename__ = "historico_registros"

    id = Column(Integer, primary_key=True, index=True)
    registro_id = Column(Integer, ForeignKey("registros.id"))

    status_anterior = Column(String, nullable=True)
    status_novo = Column(String, nullable=True)
    texto = Column(String)

    data_registro = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    registro = relationship(
        "Registro",
        back_populates="historicos"
    )


class Conquista(Base):
    __tablename__ = "conquistas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    descricao = Column(String)
    pontos_adquiridos = Column(Integer)

    usuarios = relationship(
        "UsuarioConquista",
        back_populates="conquista"
    )


class UsuarioConquista(Base):
    __tablename__ = "usuarios_conquistas"

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )

    conquista_id = Column(
        Integer,
        ForeignKey("conquistas.id")
    )

    registro_id = Column(
        Integer,
        ForeignKey("registros.id", ondelete="CASCADE"),
        nullable=True
    )

    data_desbloqueio = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    usuario = relationship(
        "Usuario",
        back_populates="conquistas"
    )

    conquista = relationship(
        "Conquista",
        back_populates="usuarios"
    )

    registro = relationship(
        "Registro"
    )