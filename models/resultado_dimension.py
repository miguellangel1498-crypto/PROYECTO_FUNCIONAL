from extensions import db


class ResultadoDimension(db.Model):
    __tablename__ = "resultados_dimension"

    id_resultado_dimension = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_resultado = db.Column(db.Integer, db.ForeignKey("resultados_evaluacion.id_resultado", ondelete="CASCADE"), nullable=False)
    id_dimension = db.Column(db.Integer, db.ForeignKey("dimensiones.id_dimension"), nullable=False)
    puntaje = db.Column(db.Numeric(5, 2), nullable=False)
    nivel = db.Column(db.String(20), nullable=False)
    fortalezas = db.Column(db.Text, nullable=True)
    debilidades = db.Column(db.Text, nullable=True)

    dimension = db.relationship("Dimension", backref="resultados_dimension")

    def __repr__(self):
        return f"<ResultadoDimension {self.id_resultado_dimension} nivel={self.nivel}>"
