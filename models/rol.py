from extensions import db


class Rol(db.Model):
    __tablename__ = "roles"

    id_rol = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(255), nullable=True)

    usuarios = db.relationship(
        "Usuario", secondary="usuario_rol", backref=db.backref("roles_list", lazy="dynamic")
    )

    def __repr__(self):
        return f"<Rol {self.nombre}>"
