from datetime import datetime

from extensions import db


class EmpresaRecomendacion(db.Model):
    __tablename__ = "empresa_recomendacion"

    id_empresa_recomendacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_empresa = db.Column(db.Integer, db.ForeignKey("empresas.id_empresa"), nullable=False)
    id_recomendacion = db.Column(db.Integer, db.ForeignKey("recomendaciones.id_recomendacion"), nullable=False)
    id_evaluacion = db.Column(db.Integer, db.ForeignKey("evaluaciones.id_evaluacion"), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="PENDIENTE")
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_completada = db.Column(db.DateTime, nullable=True)

    empresa = db.relationship("Empresa", backref="recomendaciones_asignadas")
    recomendacion = db.relationship("Recomendacion", backref="asignaciones")
    evaluacion = db.relationship("Evaluacion", backref="recomendaciones_asignadas")

    def __repr__(self):
        return f"<EmpresaRecomendacion {self.id_empresa_recomendacion} estado={self.estado}>"
