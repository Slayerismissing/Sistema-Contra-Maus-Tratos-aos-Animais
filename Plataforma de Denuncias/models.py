
from sqlalchemy import Index, func
from extensions import db


class Perfil(db.Model):
    __tablename__ = "perfis"

    id = db.Column(db.SmallInteger, primary_key=True)
    nome = db.Column(db.String(30), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    ativo = db.Column(
        db.Boolean,
        nullable=False,
        server_default=db.text("TRUE")
    )

    usuarios = db.relationship(
        "Usuario",
        back_populates="perfil"
    )

    def __repr__(self):
        return f"<Perfil {self.nome}>"


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.BigInteger, primary_key=True)
    nome_completo = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    telefone = db.Column(db.String(20))

    perfil_id = db.Column(
        db.SmallInteger,
        db.ForeignKey(
            "perfis.id",
            name="fk_usuarios_perfis",
            onupdate="RESTRICT",
            ondelete="RESTRICT"
        ),
        nullable=False
    )

    ativo = db.Column(
        db.Boolean,
        nullable=False,
        server_default=db.text("TRUE")
    )

    criado_em = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    perfil = db.relationship(
        "Perfil",
        back_populates="usuarios"
    )

    def __repr__(self):
        return f"<Usuario {self.email}>"


class CategoriaDenuncia(db.Model):
    __tablename__ = "categorias_denuncia"

    id = db.Column(db.SmallInteger, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    ativa = db.Column(db.Boolean, nullable=False, default=True)
    criada_em = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.current_timestamp()
    )

    denuncias = db.relationship(
        "Denuncia",
        back_populates="categoria"
    )


class StatusDenuncia(db.Model):
    __tablename__ = "status_denuncia"

    id = db.Column(db.SmallInteger, primary_key=True)
    nome = db.Column(db.String(40), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.SmallInteger, nullable=False, unique=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.current_timestamp()
    )

    denuncias = db.relationship(
        "Denuncia",
        back_populates="status"
    )


class Denuncia(db.Model):
    __tablename__ = "denuncias"

    id = db.Column(db.BigInteger, primary_key=True)
    protocolo = db.Column(db.String(40), nullable=False, unique=True)

    codigo_acompanhamento_hash = db.Column(
        db.String(64),
        nullable=False
    )

    descricao = db.Column(db.Text, nullable=False)
    categoria_id = db.Column(
        db.SmallInteger,
        db.ForeignKey(
            "categorias_denuncia.id",
            name="fk_denuncias_categoria"
        ),
        nullable=False
    )

    data_hora_ocorrencia = db.Column(
        db.DateTime(timezone=False)
    )

    modo_envio = db.Column(db.SmallInteger, nullable=False)

    usuario_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "usuarios.id",
            name="fk_denuncias_usuario"
        )
    )

    status_id = db.Column(
        db.SmallInteger,
        db.ForeignKey(
            "status_denuncia.id",
            name="fk_denuncias_status"
        ),
        nullable=False
    )

    responsavel_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "usuarios.id",
            name="fk_denuncias_responsavel"
        )
    )

    visibilidade = db.Column(
        db.String(15),
        nullable=False,
        default="RESTRITA"
    )

    criado_em = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.current_timestamp(),
        nullable=False
    )

    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.current_timestamp(),
        nullable=False
    )

    categoria = db.relationship(
        "CategoriaDenuncia",
        back_populates="denuncias"
    )

    status = db.relationship(
        "StatusDenuncia",
        back_populates="denuncias"
    )

    usuario = db.relationship(
        "Usuario",
        foreign_keys=[usuario_id]
    )

    responsavel = db.relationship(
        "Usuario",
        foreign_keys=[responsavel_id]
    )

    endereco = db.relationship(
        "EnderecoDenuncia",
        back_populates="denuncia",
        uselist=False
    )

    historicos = db.relationship(
        "HistoricoDenuncia",
        back_populates="denuncia",
        order_by="HistoricoDenuncia.criado_em"
    )


class EnderecoDenuncia(db.Model):
    __tablename__ = "enderecos_denuncia"

    denuncia_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "denuncias.id",
            name="fk_enderecos_denuncia_denuncia"
        ),
        primary_key=True
    )

    cep = db.Column(db.String(9), nullable=False)
    logradouro = db.Column(db.String(150), nullable=False)
    numero = db.Column(db.String(20))
    bairro = db.Column(db.String(100), nullable=False)
    municipio = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    complemento = db.Column(db.String(120))

    denuncia = db.relationship(
        "Denuncia",
        back_populates="endereco"
    )


class HistoricoDenuncia(db.Model):
    __tablename__ = "historico_denuncias"

    id = db.Column(db.BigInteger, primary_key=True)

    denuncia_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "denuncias.id",
            name="fk_historico_denuncia"
        ),
        nullable=False
    )

    status_anterior_id = db.Column(
        db.SmallInteger,
        db.ForeignKey(
            "status_denuncia.id",
            name="fk_historico_status_anterior"
        )
    )

    status_novo_id = db.Column(
        db.SmallInteger,
        db.ForeignKey(
            "status_denuncia.id",
            name="fk_historico_status_novo"
        ),
        nullable=False
    )

    operador_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "usuarios.id",
            name="fk_historico_operador"
        )
    )

    justificativa_interna = db.Column(db.Text)
    resumo_publico = db.Column(db.Text)

    criado_em = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.current_timestamp(),
        nullable=False
    )

    denuncia = db.relationship(
        "Denuncia",
        back_populates="historicos"
    )




# Índice único que ignora diferenças entre maiúsculas
# e minúsculas e espaços nas extremidades do e-mail.
Index(
    "uq_usuarios_email_ci",
    func.lower(func.btrim(Usuario.email)),
    unique=True
)
