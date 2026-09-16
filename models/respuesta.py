from datetime import datetime

from extensions import db


class Respuesta(db.Model):
    __tablename__ = "respuestas"

    id_respuesta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_evaluacion = db.Column(db.Integer, db.ForeignKey("evaluaciones.id_evaluacion", ondelete="CASCADE"), nullable=False)
    id_pregunta = db.Column(db.Integer, db.ForeignKey("preguntas.id_pregunta"), nullable=False)
    id_opcion = db.Column(db.Integer, db.ForeignKey("opciones_respuesta.id_opcion"), nullable=True)
    respuesta_texto = db.Column(db.Text, nullable=True)
    respuesta_numerica = db.Column(db.Numeric(10, 2), nullable=True)
    fecha_respuesta = db.Column(db.DateTime, default=datetime.utcnow)

    pregunta = db.relationship("Pregunta", backref="respuestas")
    opcion = db.relationship("OpcionRespuesta", backref="respuestas")

    def __repr__(self):
        return f"<Respuesta {self.id_respuesta}>"
