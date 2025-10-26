import os
from app import create_app, db
from app.models import CalendarEvent, Holiday
from typing import Any, cast

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
with app.app_context():
    engine = db.engines['calendario']
    # Create only calendario-bound tables explicitly
    cast(Any, CalendarEvent).__table__.create(bind=engine, checkfirst=True)
    cast(Any, Holiday).__table__.create(bind=engine, checkfirst=True)
    print('Created tables for bind: calendario')
