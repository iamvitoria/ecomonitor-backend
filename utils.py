from sqlalchemy.orm import Session
import models


def desbloquear_conquista(usuario, conquista, registro_id, db):
    if not conquista:
        return

    ja_possui = db.query(models.UsuarioConquista).filter_by(
        usuario_id=usuario.id,
        conquista_id=conquista.id
    ).first()

    if ja_possui:
        return

    nova = models.UsuarioConquista(
        usuario_id=usuario.id,
        conquista_id=conquista.id,
        registro_id=registro_id
    )

    db.add(nova)

    # soma pontos da conquista
    usuario.pontuacao += conquista.pontos_adquiridos
    db.add(usuario)


def verificar_conquistas(usuario_id: int, db: Session, registro_id: int):
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id
    ).first()

    if not usuario:
        return

    registro = db.query(models.Registro).filter(
        models.Registro.id == registro_id
    ).first()

    if not registro:
        return

    conquistas = {
        c.nome: c for c in db.query(models.Conquista).all()
    }

    total_registros = db.query(models.Registro).filter(
        models.Registro.usuarios_id == usuario_id,
    ).count()

    total_validados = db.query(models.Registro).filter(
        models.Registro.usuarios_id == usuario_id,
        models.Registro.status == "Validado"
    ).count()

    total_resolvidos = db.query(models.Registro).filter(
        models.Registro.usuarios_id == usuario_id,
        models.Registro.status == "Resolvido"
    ).count()

    categorias_distintas = db.query(models.Registro.categoria_id).filter(
        models.Registro.usuarios_id == usuario_id
    ).distinct().count()

    # registros em 3 semanas consecutivas
    tres_semanas = False
    datas = db.query(models.Registro.data_criacao).filter(
        models.Registro.usuarios_id == usuario_id
    ).order_by(models.Registro.data_criacao.asc()).all()

    semanas = set()
    for d in datas:
        if d[0]:
            ano, semana, _ = d[0].isocalendar()
            semanas.add((ano, semana))

    semanas_ordenadas = sorted(list(semanas))
    contador = 1

    for i in range(1, len(semanas_ordenadas)):
        anterior = semanas_ordenadas[i - 1]
        atual = semanas_ordenadas[i]

        if atual[1] == anterior[1] + 1:
            contador += 1
            if contador >= 3:
                tres_semanas = True
                break
        else:
            contador = 1

    # ranking local
    usuarios_mesma_cidade = db.query(models.Usuario).filter(
        models.Usuario.cidade == usuario.cidade
    ).order_by(models.Usuario.pontuacao.desc()).all()

    primeiro_local = False
    if usuarios_mesma_cidade:
        primeiro_local = usuarios_mesma_cidade[0].id == usuario.id

    # REGRAS

    if total_registros >= 1:
        desbloquear_conquista(usuario, conquistas.get("Primeiro Passo"), registro_id, db)

    if registro.status == "Validado" and total_validados >= 1:
        desbloquear_conquista(usuario, conquistas.get("Cidadão Ativo"), registro_id, db)

    if total_registros >= 5:
        desbloquear_conquista(usuario, conquistas.get("Guardião do Bairro"), registro_id, db)

    if tres_semanas:
        desbloquear_conquista(usuario, conquistas.get("Eco-Sentinela"), registro_id, db)

    if registro.descricao and registro.descricao.strip():
        desbloquear_conquista(usuario, conquistas.get("Paparazzi Ambiental"), registro_id, db)

    if total_registros >= 10:
        desbloquear_conquista(usuario, conquistas.get("Repórter do Bairro"), registro_id, db)

    if categorias_distintas >= 3:
        desbloquear_conquista(usuario, conquistas.get("Mestre da Diversidade"), registro_id, db)

    if total_validados >= 2:
        desbloquear_conquista(usuario, conquistas.get("Olhar Atento"), registro_id, db)

    if total_validados >= 3:
        desbloquear_conquista(usuario, conquistas.get("Fiscal da Natureza"), registro_id, db)

    if total_registros >= 15:
        desbloquear_conquista(usuario, conquistas.get("Herói Comunitário"), registro_id, db)

    if total_resolvidos >= 10:
        desbloquear_conquista(usuario, conquistas.get("Zelador da Cidade"), registro_id, db)

    if primeiro_local:
        desbloquear_conquista(usuario, conquistas.get("Lenda do EcoMonitor"), registro_id, db)

    db.commit()
    db.refresh(usuario)