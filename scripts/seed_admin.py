from app import create_app, db
from app.models import Usuario, RoleEnum
from werkzeug.security import generate_password_hash


def main():
    app = create_app('default')
    with app.app_context():
        engine = getattr(db, 'engines', {}).get('users')
        if engine is not None:
            try:
                table = getattr(Usuario, "__table__", None)
                if table is not None:
                    table.create(bind=engine, checkfirst=True)
            except Exception:
                pass
        u = db.session.query(Usuario).filter_by(username='admin').one_or_none()
        if not u:
            u = Usuario()
            u.username = 'admin'
            u.password_hash = generate_password_hash('admin123')
            u.role = RoleEnum.ADMIN
            u.nome_completo = 'Administrador'
            db.session.add(u)
            db.session.commit()
            print('created admin user: admin/admin123')
        else:
            print('admin user already exists')


if __name__ == '__main__':
    main()
