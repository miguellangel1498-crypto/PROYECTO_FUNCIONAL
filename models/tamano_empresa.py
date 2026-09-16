from extensions import db


class TamanoEmpresa(db.Model):
    __tablename__ = "tamano_empresa"

    id_tamano = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(255), nullable=True)
    numero_empleados_min = db.Column(db.Integer, nullable=True)
    numero_empleados_max = db.Column(db.Integer, nullable=True)

    empresas = db.relationship("Empresa", backref="tamano", lazy="dynamic")

    def __repr__(self):
        return f"<TamanoEmpresa {self.nombre}>"
