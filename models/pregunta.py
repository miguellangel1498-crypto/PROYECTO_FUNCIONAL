from extensions import db


class Pregunta(db.Model):
    __tablename__ = "preguntas"

    id_pregunta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_dimension = db.Column(db.Integer, db.ForeignKey("dimensiones.id_dimension"), nullable=False)
    pregunta = db.Column(db.Text, nullable=False)
    tipo_respuesta = db.Column(
        db.String(20), nullable=False, default="OPCION_UNICA"
    )
    tipo_medicion = db.Column(db.String(20), nullable=False, default="AUTOREPORTADO")
    peso = db.Column(db.Numeric(5, 2), nullable=False, default=1.00)
    orden = db.Column(db.Integer, nullable=False)
    obligatoria = db.Column(db.Boolean, nullable=False, default=True)
    estado = db.Column(db.String(20), nullable=False, default="ACTIVA")

    opciones = db.relationship("OpcionRespuesta", backref="pregunta", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Pregunta {self.id_pregunta}>"
