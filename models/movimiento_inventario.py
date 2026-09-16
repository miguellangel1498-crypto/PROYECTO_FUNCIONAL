from datetime import datetime

from extensions import db


class MovimientoInventario(db.Model):
    __tablename__ = "movimientos_inventario"

    id_movimiento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_producto = db.Column(db.Integer, db.ForeignKey("productos.id_producto", ondelete="CASCADE"), nullable=False)
    tipo_movimiento = db.Column(db.String(20), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    stock_resultante = db.Column(db.Integer, nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MovimientoInventario {self.tipo_movimiento} cantidad={self.cantidad}>"
