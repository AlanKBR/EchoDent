from app import create_app, db
from app.models import Usuario, RoleEnum, Paciente, Anamnese
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone

def main():
    app = create_app('default')
    with app.app_context():
        # Usuários
        dentista = db.session.query(Usuario).filter_by(username='dentista').one_or_none()
        if not dentista:
            dentista = Usuario()
            dentista.username = 'dentista'
            dentista.password_hash = generate_password_hash('dentista123')
            dentista.role = RoleEnum.DENTISTA
            dentista.nome_completo = 'Dr. Dentista'
            dentista.cro_registro = '12345'
            dentista.color = '#00AEEF'
            dentista.is_active = True
            db.session.add(dentista)
        secretaria = db.session.query(Usuario).filter_by(username='secretaria').one_or_none()
        if not secretaria:
            secretaria = Usuario()
            secretaria.username = 'secretaria'
            secretaria.password_hash = generate_password_hash('secretaria123')
            secretaria.role = RoleEnum.SECRETARIA
            secretaria.nome_completo = 'Secretária Teste'
            secretaria.is_active = True
            db.session.add(secretaria)
        # Paciente com Anamnese pendente
        paciente = db.session.query(Paciente).filter_by(nome_completo='Paciente Teste').one_or_none()
        if not paciente:
            paciente = Paciente()
            paciente.nome_completo = 'Paciente Teste'
            paciente.data_nascimento = datetime(1990, 1, 1)
            paciente.cpf = '000.000.000-00'
            paciente.telefone = '11999999999'
            paciente.email = 'paciente@teste.com'
            paciente.cep = '01001-000'
            paciente.cidade = 'São Paulo'
            paciente.estado = 'SP'
            db.session.add(paciente)
            db.session.flush()  # get paciente.id
            anamnese = Anamnese()
            anamnese.paciente_id = paciente.id
            anamnese.status = 'PENDENTE'
            anamnese.data_atualizacao = datetime.now(timezone.utc)
            db.session.add(anamnese)
        db.session.commit()
        print('Seeded dentista, secretaria, paciente com Anamnese pendente.')

if __name__ == '__main__':
    main()
