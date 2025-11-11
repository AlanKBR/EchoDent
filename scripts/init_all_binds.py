from app import create_app, db


def main():
    app = create_app("default")
    with app.app_context():
        # Create LogAuditoria table explicitly for history bind
        if "history" in db.engines:
            print("Creating log_auditoria table for history bind")
            from app.models import LogAuditoria

            if hasattr(LogAuditoria, "__table__"):
                table = getattr(LogAuditoria, "__table__", None)
                if table is not None:
                    table.create(bind=db.engines["history"], checkfirst=True)
        # Create 'usuarios' table explicitly for users bind
        if "users" in db.engines:
            print("Creating usuarios table for users bind")
            from app.models import Usuario

            if hasattr(Usuario, "__table__"):
                table = getattr(Usuario, "__table__", None)
                if table is not None:
                    table.create(bind=db.engines["users"], checkfirst=True)
        # Create tables for each bind
        for bind_name, engine in db.engines.items():
            print(f"Creating tables for bind: {bind_name}")
            db.Model.metadata.create_all(bind=engine)
        # Create calendario tables explicitly if not covered
        if "calendario" in db.engines:
            from app.models import CalendarEvent, Holiday

            if hasattr(CalendarEvent, "__table__"):
                table = getattr(CalendarEvent, "__table__", None)
                if table is not None:
                    table.create(
                        bind=db.engines["calendario"], checkfirst=True
                    )
            if hasattr(Holiday, "__table__"):
                table = getattr(Holiday, "__table__", None)
                if table is not None:
                    table.create(
                        bind=db.engines["calendario"], checkfirst=True
                    )
        print("All tables created for all binds.")


if __name__ == "__main__":
    main()
