from extensions import db

usuario_rol = db.Table(
    "usuario_rol",
    db.Column("id_usuario", db.Integer, db.ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), primary_key=True),
    db.Column("id_rol", db.Integer, db.ForeignKey("roles.id_rol", ondelete="CASCADE"), primary_key=True),
)
