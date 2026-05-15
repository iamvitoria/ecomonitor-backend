from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import models 

def verificar_conquistas(usuario_id: int, db: Session, denuncia_id: int = None):
    """
    Analisa e atribui conquistas, garantindo que a pontuação bônus 
    seja somada corretamente ao saldo do usuário.
    """
    # populate_existing() força o SQLAlchemy a ler os dados mais recentes do banco
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).populate_existing().first()
    if not usuario:
        return

    conquistas_sistema = db.query(models.Conquista).all()
    hoje = datetime.now()
    
    # Busca a denúncia que disparou a verificação para checar foto e status
    denuncia_atual = db.query(models.Denuncia).filter(models.Denuncia.id == denuncia_id).first()
    
    # Contagens gerais para conquistas de quantidade
    total_denuncias = db.query(models.Denuncia).filter(models.Denuncia.usuario_id == usuario_id).count()
    total_resolvidas = db.query(models.Denuncia).filter(
        models.Denuncia.usuario_id == usuario_id, 
        models.Denuncia.status == "Validado"
    ).count()

    for conquista in conquistas_sistema:
        ganhou = False
        
        # 1. Primeiro Passo (Qualquer denúncia enviada)
        if conquista.nome == "Primeiro Passo":
            if total_denuncias >= 1: ganhou = True

        # 2. Paparazzi Ambiental (Denúncia atual tem foto?)
        elif conquista.nome == "Paparazzi Ambiental":
            if denuncia_atual and denuncia_atual.foto_url:
                ganhou = True

        # 3. Conquistas que exigem Status "Validado"
        elif conquista.nome in ["Olhar Atento", "Zelador da Cidade", "Cidadão Ativo"]:
            # Se a denúncia atual não for a validada, ignoramos nesta execução
            if not denuncia_atual or denuncia_atual.status != "Validado":
                continue 
            
            if conquista.nome == "Olhar Atento":
                if total_resolvidas >= 1: ganhou = True
            elif conquista.nome == "Zelador da Cidade":
                if total_resolvidas >= 10: ganhou = True
            elif conquista.nome == "Cidadão Ativo":
                if usuario.pontuacao >= 200: ganhou = True

        # 4. Eco-Sentinela (Frequência: 3 semanas seguidas)
        elif conquista.nome == "Eco-Sentinela":
            semanas = []
            for i in range(3):
                inicio = hoje - timedelta(days=(i+1)*7)
                fim = hoje - timedelta(days=i*7)
                count = db.query(models.Denuncia).filter(
                    models.Denuncia.usuario_id == usuario_id,
                    models.Denuncia.data_criacao.between(inicio, fim)
                ).count()
                semanas.append(count > 0)
            if all(semanas): ganhou = True

        # 5. Mestre da Diversidade (3 categorias diferentes)
        elif conquista.nome == "Mestre da Diversidade":
            categorias = db.query(models.Denuncia.categoria).filter(
                models.Denuncia.usuario_id == usuario_id
            ).distinct().count()
            if categorias >= 3: ganhou = True

        # 6. Repórter de Bairro (Quantidade total)
        elif conquista.nome == "Repórter de Bairro":
            if total_denuncias >= 5: ganhou = True

        # 7. Outras conquistas baseadas puramente em pontuação
        elif conquista.nome in ["Guardião do Bairro", "Fiscal da Natureza", "Herói Comunitário", "Lenda do EcoMonitor"]:
            if usuario.pontuacao >= conquista.pontos_adquiridos: # Ajuste o nome da coluna se necessário
                ganhou = True

        # --- PROCESSO DE ATRIBUIÇÃO ---
        if ganhou:
            # Verifica se já possui para não duplicar pontos e registros
            ja_possui = db.query(models.UsuarioConquista).filter_by(
                usuario_id=usuario_id, 
                conquista_id=conquista.id
            ).first()
            
            if not ja_possui:
                # Cria o vínculo com a denúncia geradora
                nova_ligacao = models.UsuarioConquista(
                    usuario_id=usuario_id, 
                    conquista_id=conquista.id,
                    denuncia_id=denuncia_id
                )
                db.add(nova_ligacao)

                # Soma o bônus da conquista (pontos_adquiridos)
                # IMPORTANTE: Se você não renomeou no banco, use conquista.pontos_necessarios
                usuario.pontuacao += conquista.pontos_adquiridos
                
                db.add(usuario)
                db.commit() # Salva a conquista e os novos pontos bônus
                db.refresh(usuario) # Atualiza o objeto para a próxima conquista do loop
                print(f"Conquista Desbloqueada: {conquista.nome} (+{conquista.pontos_adquiridos} pts)")