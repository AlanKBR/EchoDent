from app import create_app, db
from app.models import GlobalSetting

app = create_app()
with app.app_context():
    setting = db.session.get(GlobalSetting, 'DEV_LOGS_ENABLED')
    if not setting:
        setting = GlobalSetting(key='DEV_LOGS_ENABLED', value='false')
        db.session.add(setting)
        db.session.commit()
        print('DEV_LOGS_ENABLED inserido.')
    else:
        print('DEV_LOGS_ENABLED já existe.')
