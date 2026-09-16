from datetime import datetime

from flask_login import UserMixin

from extensions import db
from models.usuario_rol import usuario_rol


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_empresa = db.Column(db.Integer, db.ForeignKey("empresas.id_empresa"), nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(30), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default="ACTIVO")
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    auditorias = db.relationship("Auditoria", backref="usuario", lazy="dynamic")

    def set_password(self, password):
        from extensions import bcrypt
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        from extensions import bcrypt
        try:
            return bcrypt.check_password_hash(self.password_hash, password)
        except (ValueError, TypeError):
            return False

    def tiene_rol(self, nombre_rol):
        nombre_upper = nombre_rol.upper()
        return any(r.nombre.upper() == nombre_upper for r in self.roles_list)

    @property
    def es_superadmin(self):
        return self.tiene_rol("SUPERADMIN")

    @property
    def es_empresa(self):
        return self.tiene_rol("EMPRESA")

    @property
    def tiene_empresa(self):
        return self.empresa is not None

    @property
    def acceso_empresa_activa(self):
        return self.empresa is None or self.empresa.esta_activa

    @property
    def etiqueta_rol(self):
        for r in self.roles_list:
            return r.nombre
        return "Sin rol"

    def get_id(self):
        return str(self.id_usuario)

    def __repr__(self):
        return f"<Usuario {self.correo}>"
