from extensions import db


class OpcionRespuesta(db.Model):
    __tablename__ = "opciones_respuesta"

    id_opcion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_pregunta = db.Column(db.Integer, db.ForeignKey("preguntas.id_pregunta", ondelete="CASCADE"), nullable=False)
    texto = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Numeric(5, 2), nullable=False)
    orden = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<OpcionRespuesta {self.texto}>"
