from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import models 

def verificar_conquistas(usuario_id: int, db: Session, denuncia_id: int = None):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).populate_existing().first()
    if not usuario:
        return

    if denuncia_id is None:
        print("DEBUG: Verificação abortada - denuncia_id é None")
        return

    conquistas_sistema = db.query(models.Conquista).all()
    hoje = datetime.now()
    
    denuncia_atual = db.query(models.Denuncia).filter(models.Denuncia.id == denuncia_id).first()
    if not denuncia_atual:
        return

    total_denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_id).count()
    total_resolvidas = db.query(models.Denuncia).filter(
        models.Denuncia.usuario_id == usuario_id, 
        models.Denuncia.status == "Validado"
    ).count()

    for conquista in conquistas_sistema:
        ganhou = False
        
        if conquista.nome in ["Olhar Atento", "Zelador da Cidade", "Cidadão Ativo"]:
            if denuncia_atual.status != "Validado":
                continue 

            if conquista.nome == "Olhar Atento" and total_resolvidas >= 1:
                ganhou = True
            elif conquista.nome == "Zelador da Cidade" and total_resolvidas >= 10:
                ganhou = True
            elif conquista.nome == "Cidadão Ativo" and usuario.pontuacao >= 200:
                ganhou = True

        elif conquista.nome == "Primeiro Passo":
            if total_denuncias >= 1: ganhou = True

        elif conquista.nome == "Paparazzi Ambiental":
            if denuncia_atual.foto_url: ganhou = True

        elif conquista.nome == "Repórter de Bairro":
            if total_denuncias >= 5: ganhou = True

        if ganhou:
            ja_possui = db.query(models.UsuarioConquista).filter_by(
                usuario_id=usuario_id, 
                conquista_id=conquista.id
            ).first()
            
            if not ja_possui:
                nova_ligacao = models.UsuarioConquista(
                    usuario_id=usuario_id, 
                    conquista_id=conquista.id,
                    denuncia_id=denuncia_id 
                )
                db.add(nova_ligacao)
                usuario.pontuacao += conquista.pontos_adquiridos
                db.add(usuario)
                db.commit()
                db.refresh(usuario)