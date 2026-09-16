from datetime import datetime

from extensions import db


class Evaluacion(db.Model):
    __tablename__ = "evaluaciones"

    id_evaluacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_empresa = db.Column(db.Integer, db.ForeignKey("empresas.id_empresa"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    fecha_inicio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_finalizacion = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), nullable=False, default="EN_PROCESO")
    version_diagnostico = db.Column(db.String(20), nullable=False, default="1.0")

    empresa = db.relationship("Empresa", backref="evaluaciones")
    usuario = db.relationship("Usuario", backref="evaluaciones")
    respuestas = db.relationship("Respuesta", backref="evaluacion", lazy="dynamic", cascade="all, delete-orphan")
    resultado = db.relationship("ResultadoEvaluacion", backref="evaluacion", uselist=False, cascade="all, delete-orphan")

    @property
    def esta_en_proceso(self):
        return self.estado == "EN_PROCESO"

    @property
    def esta_finalizada(self):
        return self.estado == "FINALIZADA"

    def __repr__(self):
        return f"<Evaluacion {self.id_evaluacion}>"
