from extensions import db


class Sector(db.Model):
    __tablename__ = "sectores"

    id_sector = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.String(255), nullable=True)

    empresas = db.relationship("Empresa", backref="sector", lazy="dynamic")

    def __repr__(self):
        return f"<Sector {self.nombre}>"
