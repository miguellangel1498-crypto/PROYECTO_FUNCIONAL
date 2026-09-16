from extensions import db


class Dimension(db.Model):
    __tablename__ = "dimensiones"

    id_dimension = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    peso = db.Column(db.Numeric(5, 2), nullable=False, default=1.00)
    estado = db.Column(db.String(20), nullable=False, default="ACTIVA")

    preguntas = db.relationship("Pregunta", backref="dimension", lazy="dynamic", cascade="all, delete-orphan")
    recomendaciones = db.relationship("Recomendacion", backref="dimension", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Dimension {self.nombre}>"
