from datetime import datetime

from extensions import db


class Empresa(db.Model):
    __tablename__ = "empresas"

    id_empresa = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nit = db.Column(db.String(30), unique=True, nullable=True)
    nombre = db.Column(db.String(150), nullable=False)
    id_sector = db.Column(db.Integer, db.ForeignKey("sectores.id_sector"), nullable=False)
    id_tamano = db.Column(db.Integer, db.ForeignKey("tamano_empresa.id_tamano"), nullable=False)
    numero_empleados = db.Column(db.Integer, nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)
    departamento = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(30), nullable=True)
    correo = db.Column(db.String(150), nullable=True)
    sitio_web = db.Column(db.String(200), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), nullable=False, default="ACTIVA")

    usuarios = db.relationship("Usuario", backref="empresa", lazy="dynamic")

    @property
    def esta_activa(self):
        return self.estado == "ACTIVA"

    @property
    def esta_inactiva(self):
        return self.estado == "INACTIVA"

    @property
    def etiqueta_estado(self):
        return {"ACTIVA": "Activa", "INACTIVA": "Inactiva"}.get(self.estado, self.estado)

    def __repr__(self):
        return f"<Empresa {self.nombre}>"
