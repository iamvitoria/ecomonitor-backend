import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Carrega as variáveis de segurança do arquivo .env
load_dotenv()

# Pega a URL do banco de dados
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Cria o motor de conexão com o Neon
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Configura a sessão que usaremos para salvar/buscar dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para criarmos as nossas tabelas depois
Base = declarative_base()

# Função para fornecer o banco de dados quando uma requisição chegar
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()