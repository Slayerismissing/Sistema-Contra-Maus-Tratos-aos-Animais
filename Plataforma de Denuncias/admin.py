
from getpass import getpass

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app import app
from extensions import db
from models import Usuario, Perfil


def criar_administrador():

    print("\n===== CADASTRO DE ADMINISTRADOR =====\n")

    nome = input("Nome completo: ").strip()
    email = input("E-mail administrativo: ").strip().lower()

    senha = getpass("Senha: ")
    confirmar_senha = getpass("Confirme a senha: ")

    if not nome or not email or not senha:
        print("Erro: todos os campos são obrigatórios.")
        return

    if len(senha) < 8:
        print("Erro: a senha precisa ter pelo menos 8 caracteres.")
        return

    if senha != confirmar_senha:
        print("Erro: as senhas não coincidem.")
        return

    with app.app_context():

        try:
            # Verificar se o e-mail já existe
            existente = db.session.execute(
                db.select(Usuario).where(
                    func.lower(func.btrim(Usuario.email)) == email
                )
            ).scalar_one_or_none()

            if existente:
                print("Erro: esse e-mail já está cadastrado.")
                return

            # Buscar perfil administrativo
            perfil_admin = db.session.execute(
                db.select(Perfil).where(
                    Perfil.nome == "ADMINISTRADOR",
                    Perfil.ativo.is_(True)
                )
            ).scalar_one_or_none()

            if not perfil_admin:
                print("Erro: perfil ADMINISTRADOR não encontrado.")
                return

            # Criar administrador
            administrador = Usuario(
                nome_completo=nome,
                email=email,
                senha_hash=generate_password_hash(senha),
                perfil_id=perfil_admin.id,
                ativo=True
            )

            db.session.add(administrador)
            db.session.commit()

            print("\nAdministrador criado com sucesso!")
            print(f"ID: {administrador.id}")
            print(f"E-mail: {administrador.email}")
            print(f"Perfil: {perfil_admin.nome}")

        except SQLAlchemyError:
            db.session.rollback()
            print("Erro ao cadastrar administrador.")
            app.logger.exception("Falha na criação do administrador.")


if __name__ == "__main__":
    criar_administrador()
