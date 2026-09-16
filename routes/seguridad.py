from flask import Blueprint, render_template, request
from flask_login import login_required

from extensions import db
from models import Auditoria, Usuario
from routes.decoradores import superadmin_requerido

seguridad_bp = Blueprint("seguridad", __name__, url_prefix="/seguridad")


@seguridad_bp.route("/auditoria")
@login_required
@superadmin_requerido
def auditoria():
    pagina = request.args.get("page", 1, type=int)
    accion = request.args.get("accion", "").strip()
    email = request.args.get("usuario", "").strip()
    busqueda = request.args.get("q", "").strip()

    consulta = Auditoria.query.outerjoin(Usuario, Auditoria.id_usuario == Usuario.id_usuario)

    if accion:
        consulta = consulta.filter(Auditoria.accion == accion)
    if email:
        consulta = consulta.filter(Usuario.correo.ilike(f"%{email}%"))
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.filter(
            db.or_(
                Auditoria.accion.ilike(patron),
                Auditoria.tabla_afectada.ilike(patron),
                Auditoria.descripcion.ilike(patron),
                Auditoria.direccion_ip.ilike(patron),
                Usuario.correo.ilike(patron),
            )
        )

    registros = consulta.order_by(Auditoria.fecha.desc()).paginate(
        page=pagina, per_page=20, error_out=False
    )
    acciones = [r[0] for r in (Auditoria.query.with_entities(Auditoria.accion).distinct().all())]
    acciones.sort()

    return render_template(
        "seguridad/auditoria.html",
        registros=registros,
        acciones=acciones,
        accion=accion,
        email=email,
        busqueda=busqueda,
    )
