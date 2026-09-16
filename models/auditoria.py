from datetime import datetime

from extensions import db


class Auditoria(db.Model):
    __tablename__ = "auditoria"

    id_auditoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=True)
    accion = db.Column(db.String(100), nullable=False)
    tabla_afectada = db.Column(db.String(100), nullable=True)
    id_registro = db.Column(db.Integer, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    direccion_ip = db.Column(db.String(45), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Auditoria {self.accion} {self.fecha}>"
