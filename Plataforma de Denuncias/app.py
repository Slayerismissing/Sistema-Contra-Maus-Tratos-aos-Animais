import os

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from flask import Flask, render_template, request, redirect, url_for, flash, session
import secrets
import string
import datetime

from extensions import db
from models import Perfil, Usuario

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import hashlib
import hmac

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models import (
    Usuario,
    Perfil,
    CategoriaDenuncia,
    StatusDenuncia,
    Denuncia,
    EnderecoDenuncia,
    HistoricoDenuncia
)


load_dotenv()


app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY não configurada no .env")

if not app.config["SQLALCHEMY_DATABASE_URI"]:
    raise RuntimeError("DATABASE_URL não configurada no .env")

db.init_app(app)


def gerar_protocolo():
    ano = datetime.datetime.now().year
    sufixo = secrets.token_hex(6).upper()

    return f"DEN-{ano}-{sufixo}"


def gerar_codigo_acompanhamento():
    alphabet = string.ascii_uppercase + string.digits

    return ''.join(
        secrets.choice(alphabet) for _ in range(20)
    )


def gerar_hash_codigo(codigo):
    return hashlib.sha256(
        codigo.encode("utf-8")
    ).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        if not email or not senha:
            flash("Informe seu e-mail e sua senha.", "error")
            return redirect(url_for('login'))

        try:
            usuario = db.session.execute(
                db.select(Usuario).where(
                    func.lower(func.btrim(Usuario.email)) == email
                )
            ).scalar_one_or_none()

            if (
                usuario
                and usuario.ativo
                and usuario.perfil.ativo
                and check_password_hash(usuario.senha_hash, senha)
            ):

                # Limpar sessão anterior
                session.clear()

                session['user_id'] = usuario.id
                session['user_email'] = usuario.email
                session['user_name'] = usuario.nome_completo
                session['user_role'] = usuario.perfil.nome

                flash(
                    f"Bem-vindo(a), {usuario.nome_completo}!",
                    "success"
                )

                if usuario.perfil.nome == 'ADMINISTRADOR':
                    return redirect(url_for('admin_dashboard'))

                return redirect(url_for('index'))

            flash("E-mail ou senha incorretos.", "error")

        except SQLAlchemyError:
            app.logger.exception("Erro durante a autenticação.")
            flash("Não foi possível realizar o login.", "error")

    return render_template('login.html')



@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():

    if request.method == 'POST':

        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        # Validar campos obrigatórios
        if not nome or not email or not senha:
            flash("Preencha todos os campos obrigatórios.", "error")
            return redirect(url_for('cadastro'))

        if len(senha) < 8:
            flash("A senha deve possuir pelo menos 8 caracteres.", "error")
            return redirect(url_for('cadastro'))

        try:
            # Verificar se o e-mail já existe
            usuario_existente = db.session.execute(
                db.select(Usuario).where(
                    func.lower(func.btrim(Usuario.email)) == email
                )
            ).scalar_one_or_none()

            if usuario_existente:
                flash("E-mail já cadastrado.", "error")
                return redirect(url_for('cadastro'))

            # Buscar perfil padrão de usuário comum
            perfil = db.session.execute(
                db.select(Perfil).where(
                    Perfil.nome == 'USUARIO_COMUM',
                    Perfil.ativo.is_(True)
                )
            ).scalar_one_or_none()

            if not perfil:
                flash("Perfil de usuário não encontrado.", "error")
                return redirect(url_for('cadastro'))

            # Criar usuário
            novo_usuario = Usuario(
                nome_completo=nome,
                email=email,
                senha_hash=generate_password_hash(senha),
                perfil_id=perfil.id
            )

            db.session.add(novo_usuario)
            db.session.commit()

            flash(
                "Cadastro realizado com sucesso! Faça login.",
                "success"
            )

            return redirect(url_for('login'))

        except IntegrityError:
            db.session.rollback()
            flash("Não foi possível cadastrar. Verifique os dados.", "error")

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Erro ao cadastrar usuário.")
            flash("Erro interno ao realizar cadastro.", "error")

    return render_template('cadastro.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for('index'))


@app.route('/denunciar', methods=['GET', 'POST'])
def registrar_denuncia():

    if request.method == 'GET':
        return render_template('denunciar.html')

    # Dados da ocorrência
    categoria_valor = request.form.get('categoria', '').strip()
    descricao = request.form.get('descricao', '').strip()
    data_hora_raw = request.form.get('data_hora', '').strip()

    # Endereço
    cep = request.form.get('cep', '').strip()
    logradouro = request.form.get('logradouro', '').strip()
    numero = request.form.get('numero', '').strip() or None
    bairro = request.form.get('bairro', '').strip()
    municipio = request.form.get('municipio', '').strip()
    estado = request.form.get('estado', '').strip().upper()
    complemento = request.form.get('complemento', '').strip() or None

    # Verificar campos obrigatórios
    if not all([
        categoria_valor,
        descricao,
        cep,
        logradouro,
        bairro,
        municipio,
        estado
    ]):
        flash("Preencha todos os campos obrigatórios.", "error")
        return redirect(url_for('registrar_denuncia'))

    if len(estado) != 2 or not estado.isalpha():
        flash("Informe uma sigla de estado válida.", "error")
        return redirect(url_for('registrar_denuncia'))

    # Localizar categoria pelo ID ou nome
    try:
        if categoria_valor.isdigit():
            categoria = db.session.get(
                CategoriaDenuncia,
                int(categoria_valor)
            )
        else:
            categoria = db.session.execute(
                db.select(CategoriaDenuncia).where(
                    CategoriaDenuncia.nome == categoria_valor
                )
            ).scalar_one_or_none()

        if not categoria or not categoria.ativa:
            flash("Categoria inválida ou indisponível.", "error")
            return redirect(url_for('registrar_denuncia'))

        # Localizar status inicial
        status_inicial = db.session.execute(
            db.select(StatusDenuncia).where(
                StatusDenuncia.nome == 'Recebida',
                StatusDenuncia.ativo.is_(True)
            )
        ).scalar_one_or_none()

        if not status_inicial:
            raise RuntimeError("Status inicial não configurado.")

        # Determinar modo de envio
        anonimo_raw = request.form.get('anonimo', '').strip().lower()

        opcao_anonimo = anonimo_raw in (
            'true', '1', 'on', 'sim', 'yes'
        )

        usuario_id = None
        modo_envio = 1

        if session.get('user_id') and not opcao_anonimo:

            usuario = db.session.get(
                Usuario,
                int(session['user_id'])
            )

            if not usuario or not usuario.ativo:
                session.clear()
                flash("Sua sessão expirou. Entre novamente.", "warning")
                return redirect(url_for('login'))

            modo_envio = 2
            usuario_id = usuario.id

        # Interpretar data e hora aproximada
        data_hora = None

        if data_hora_raw:
            try:
                data_hora = datetime.datetime.fromisoformat(
                    data_hora_raw
                )

                if data_hora.tzinfo is not None:
                    raise ValueError(
                        "Utilize uma data e hora local."
                    )

            except ValueError:
                flash("Data ou horário inválido.", "error")
                return redirect(url_for('registrar_denuncia'))

        # Gerar protocolo e código sigiloso
        protocolo = gerar_protocolo()
        codigo_segredo = gerar_codigo_acompanhamento()
        codigo_hash = gerar_hash_codigo(codigo_segredo)

        # Criar denúncia
        denuncia = Denuncia(
            protocolo=protocolo,
            codigo_acompanhamento_hash=codigo_hash,
            descricao=descricao,
            categoria_id=categoria.id,
            data_hora_ocorrencia=data_hora,
            modo_envio=modo_envio,
            usuario_id=usuario_id,
            status_id=status_inicial.id,
            visibilidade='RESTRITA'
        )

        db.session.add(denuncia)

        # Gerar ID da denúncia
        db.session.flush()

        # Criar endereço
        endereco = EnderecoDenuncia(
            denuncia_id=denuncia.id,
            cep=cep,
            logradouro=logradouro,
            numero=numero,
            bairro=bairro,
            municipio=municipio,
            estado=estado,
            complemento=complemento
        )

        # Criar primeiro registro do histórico
        historico = HistoricoDenuncia(
            denuncia_id=denuncia.id,
            status_anterior_id=None,
            status_novo_id=status_inicial.id,
            operador_id=None,
            resumo_publico=(
                "Denúncia registrada com sucesso. "
                "Aguardando triagem."
            )
        )

        db.session.add_all([endereco, historico])

        # Salvar tudo na mesma transação
        db.session.commit()

        flash("Denúncia registrada com sucesso!", "success")

        return render_template(
            'confirmacao.html',
            protocolo=protocolo,
            codigo=codigo_segredo
        )

    except IntegrityError:
        db.session.rollback()
        app.logger.exception("Erro de integridade ao registrar denúncia.")

        flash("Não foi possível registrar a denúncia. Verifique os dados.", "error")
        return redirect(url_for('registrar_denuncia'))

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro no banco ao registrar denúncia.")

        flash("Erro interno ao registrar a denúncia.", "error")
        return redirect(url_for('registrar_denuncia'))

    except RuntimeError:
        db.session.rollback()
        app.logger.exception("Configuração inválida para registro.")

        flash("O sistema não está preparado para receber denúncias.", "error")
        return redirect(url_for('registrar_denuncia'))



@app.route('/acompanhar', methods=['GET', 'POST'])
def acompanhar_denuncia():

    resultado = None
    erro = None

    if request.method == 'POST':

        protocolo = request.form.get(
            'protocolo', ''
        ).strip().upper()

        codigo = request.form.get(
            'codigo', ''
        ).strip().upper()

        if protocolo and codigo:

            try:
                denuncia = db.session.execute(
                    db.select(Denuncia).where(
                        Denuncia.protocolo == protocolo
                    )
                ).scalar_one_or_none()

                codigo_hash = gerar_hash_codigo(codigo)

                if (
                    denuncia
                    and hmac.compare_digest(
                        denuncia.codigo_acompanhamento_hash.strip(),
                        codigo_hash
                    )
                ):

                    historico = db.session.execute(
                        db.select(HistoricoDenuncia)
                        .where(
                            HistoricoDenuncia.denuncia_id == denuncia.id
                        )
                        .order_by(
                            HistoricoDenuncia.criado_em.desc()
                        )
                        .limit(1)
                    ).scalar_one_or_none()

                    resultado = {
                        'status': denuncia.status.nome,
                        'data_registro': denuncia.criado_em.strftime(
                            "%d/%m/%Y %H:%M"
                        ),
                        'mensagem': (
                            historico.resumo_publico
                            if historico and historico.resumo_publico
                            else "Denúncia em acompanhamento."
                        )
                    }

                else:
                    erro = "Protocolo ou código de acompanhamento inválido."

            except SQLAlchemyError:
                db.session.rollback()
                app.logger.exception("Erro ao consultar denúncia.")

                erro = "Não foi possível consultar a denúncia."

        else:
            erro = "Informe o protocolo e o código de acompanhamento."

    return render_template(
        'acompanhar.html',
        resultado=resultado,
        erro=erro
    )



@app.route('/minhas-denuncias')
def minhas_denuncias():

    if 'user_id' not in session:
        flash("Faça login para visualizar suas denúncias.", "warning")
        return redirect(url_for('login'))

    try:
        denuncias_db = db.session.execute(
            db.select(Denuncia)
            .where(Denuncia.usuario_id == int(session['user_id']))
            .order_by(Denuncia.criado_em.desc())
        ).scalars().all()

        minhas = []

        for d in denuncias_db:

            endereco = d.endereco

            localizacao = (
                f"{endereco.logradouro}, {endereco.numero or 'S/N'}"
                if endereco else ""
            )

            resumo = (
                d.historicos[-1].resumo_publico
                if d.historicos and d.historicos[-1].resumo_publico
                else "Sem atualizações públicas."
            )

            minhas.append({
                'protocolo': d.protocolo,
                'categoria': d.categoria.nome,
                'descricao': d.descricao,
                'data_hora': d.data_hora_ocorrencia,
                'localizacao': localizacao,
                'municipio_uf': (
                    f"{endereco.municipio}/{endereco.estado}"
                    if endereco else ""
                ),
                'anonimo': d.modo_envio == 1,
                'status': d.status.nome,
                'data_registro': d.criado_em.strftime(
                    "%d/%m/%Y %H:%M"
                ),
                'mensagem_publica': resumo
            })

        return render_template(
            'minhas_denuncias.html',
            denuncias=minhas
        )

    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Erro ao listar denúncias do usuário.")

        flash("Não foi possível carregar suas denúncias.", "error")
        return redirect(url_for('index'))


# Área Administrativa (RF006, RF008, RS003)
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user_role') != 'ADMINISTRADOR':
        flash("Acesso restrito a administradores.", "error")
        return redirect(url_for('login'))
    
    total = len(DENUNCIAS_DB)
    recebidas = sum(1 for d in DENUNCIAS_DB.values() if d['status'] == 'Recebida')
    
    return render_template('admin/dashboard.html', total=total, recebidas=recebidas)

@app.route('/admin/denuncias')
def admin_denuncias():
    if session.get('user_role') != 'ADMINISTRADOR':
        flash("Acesso restrito a administradores.", "error")
        return redirect(url_for('login'))
        
    return render_template('admin/denuncias.html', denuncias=list(DENUNCIAS_DB.values()))

if __name__ == "__main__":

    try:
        with app.app_context():
            resultado = db.session.execute(
                text("""
                    SELECT
                        current_database(),
                        current_user
                """)
            ).fetchone()

            print("\n================================")
            print("CONEXÃO COM POSTGRESQL OK!")
            print(f"Banco: {resultado[0]}")
            print(f"Usuário: {resultado[1]}")
            print("================================\n")

    except SQLAlchemyError:
        app.logger.exception(
            "Não foi possível conectar ao PostgreSQL."
        )
        raise

    with app.app_context():

        perfis = db.session.execute(
            db.select(Perfil).order_by(Perfil.id)
        ).scalars().all()

        print("\n===== TESTE SQLALCHEMY =====")

        for perfil in perfis:
            print(f"ID: {perfil.id} | Perfil: {perfil.nome}")

        print("============================\n")

    app.run(debug=True)
