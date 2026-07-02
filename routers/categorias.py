from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db 
from models import Categoria 

router = APIRouter()

@router.get("/categorias")
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(Categoria).all()