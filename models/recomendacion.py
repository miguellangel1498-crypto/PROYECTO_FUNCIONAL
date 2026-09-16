from extensions import db


class Recomendacion(db.Model):
    __tablename__ = "recomendaciones"

    id_recomendacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_dimension = db.Column(db.Integer, db.ForeignKey("dimensiones.id_dimension"), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    prioridad = db.Column(db.String(20), nullable=False, default="MEDIA")
    nivel_minimo = db.Column(db.Numeric(5, 2), nullable=True)
    nivel_maximo = db.Column(db.Numeric(5, 2), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default="ACTIVA")

    def __repr__(self):
        return f"<Recomendacion {self.titulo}>"
