from datetime import datetime

from extensions import db


class ResultadoEvaluacion(db.Model):
    __tablename__ = "resultados_evaluacion"

    id_resultado = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_evaluacion = db.Column(db.Integer, db.ForeignKey("evaluaciones.id_evaluacion", ondelete="CASCADE"), nullable=False, unique=True)
    indice_madurez = db.Column(db.Numeric(5, 2), nullable=False)
    nivel = db.Column(db.String(20), nullable=False)
    fecha_calculo = db.Column(db.DateTime, default=datetime.utcnow)
    metodologia = db.Column(db.String(100), nullable=False, default="IME_V1")

    dimensiones = db.relationship("ResultadoDimension", backref="resultado", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ResultadoEvaluacion {self.id_resultado} nivel={self.nivel}>"
