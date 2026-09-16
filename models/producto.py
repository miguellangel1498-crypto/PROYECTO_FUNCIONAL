from datetime import datetime

from extensions import db


class Producto(db.Model):
    __tablename__ = "productos"

    id_producto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_empresa = db.Column(db.Integer, db.ForeignKey("empresas.id_empresa", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(100), nullable=True)
    stock_actual = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_ultima_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa = db.relationship("Empresa", backref="productos")
    movimientos = db.relationship("MovimientoInventario", backref="producto", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Producto {self.nombre}>"
