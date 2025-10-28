from app import db
from app.models import GlobalSetting, DeveloperLog


def get_logs_session():
    # Retorna uma sessão para o bind 'logs'
    engine = getattr(db, "engines", {}).get("logs")
    if engine is None:
        raise RuntimeError("Engine do bind 'logs' não encontrado.")
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()

 
def test_devlog_integration_flow(client, app):
    # Cenário 1: DevLogs ATIVADO
    with app.app_context():
        setting = db.session.get(GlobalSetting, 'DEV_LOGS_ENABLED')
        if not setting:
            setting = GlobalSetting()
            setting.key = 'DEV_LOGS_ENABLED'
            db.session.add(setting)
        setting.value = 'true'
        db.session.commit()

        # Limpa logs anteriores
        logs_sess = get_logs_session()
        logs_sess.query(DeveloperLog).delete()
        logs_sess.commit()

    long_str = "X" * 6000
    response = client.post(
        "/__dev/test_raise_exception",
        headers={"HX-Request": "true"},
        json={"blob": long_str},
    )
    # Verificação 1: Log criado
    with app.app_context():
        logs_sess = get_logs_session()
        logs = logs_sess.query(DeveloperLog).all()
        assert len(logs) == 1
        log = logs[0]
        # Verificação 2: Conteúdo do log
        assert log.error_type == "ValueError"
        assert "Erro de teste de log" in log.traceback
    # Verificação 2.1: request_body capturado e truncado a 4096
    assert log.request_body is not None and log.request_body != ""
    assert len(log.request_body) == 4096
    # Verificação 3: Status code
    assert response.status_code == 500
    # Verificação 4: Toast OOB
    assert b'hx-swap-oob="beforeend:#global-toast-container"' in response.data
    assert b'Erro de teste de log' in response.data

    # Cenário 2: DevLogs DESATIVADO
    with app.app_context():
        setting = db.session.get(GlobalSetting, 'DEV_LOGS_ENABLED')
        if not setting:
            setting = GlobalSetting()
            setting.key = 'DEV_LOGS_ENABLED'
            db.session.add(setting)
        setting.value = 'false'
        db.session.commit()
        # Limpa logs
        logs_sess = get_logs_session()
        logs_sess.query(DeveloperLog).delete()
        logs_sess.commit()

    response = client.post(
        "/__dev/test_raise_exception",
        headers={"HX-Request": "true"},
        json={"blob": long_str},
    )
    # Verificação 5: Log sempre criado
    with app.app_context():
        logs_sess = get_logs_session()
        logs = logs_sess.query(DeveloperLog).all()
        assert len(logs) == 1
        log = logs[0]
    # Verificação 7.1: request_body capturado e truncado
    assert log.request_body is not None and log.request_body != ""
    assert len(log.request_body) == 4096
    # Verificação 6: Status code
    assert response.status_code == 500
    # Verificação 7: Não deve haver toast OOB
    assert b'hx-swap-oob' not in response.data
