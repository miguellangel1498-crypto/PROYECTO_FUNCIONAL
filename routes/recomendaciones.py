from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import EmpresaRecomendacion
from routes.decoradores import admin_empresa_requerido

recomendaciones_bp = Blueprint("recomendaciones", __name__, url_prefix="/recomendaciones")


def _empresa_id():
    if current_user.empresa is None:
        abort(403)
    if not current_user.acceso_empresa_activa:
        abort(403)
    return current_user.empresa.id_empresa


@recomendaciones_bp.route("/")
@login_required
@admin_empresa_requerido
def listar():
    empresa_id = _empresa_id()
    estado_filtro = request.args.get("estado", "").strip()

    consulta = EmpresaRecomendacion.query.filter_by(id_empresa=empresa_id)
    if estado_filtro in ("PENDIENTE", "EN_PROCESO", "COMPLETADA", "DESCARTADA"):
        consulta = consulta.filter_by(estado=estado_filtro)

    asignaciones = consulta.order_by(EmpresaRecomendacion.fecha_asignacion.desc()).all()
    return render_template(
        "diagnostico/recomendaciones.html",
        asignaciones=asignaciones,
        estado_filtro=estado_filtro,
    )


@recomendaciones_bp.route("/<int:id_asignacion>/cambiar_estado", methods=["POST"])
@login_required
@admin_empresa_requerido
def cambiar_estado(id_asignacion):
    empresa_id = _empresa_id()
    asignacion = EmpresaRecomendacion.query.get_or_404(id_asignacion)
    if asignacion.id_empresa != empresa_id:
        abort(403)

    nuevo_estado = request.form.get("estado", "").strip()
    if nuevo_estado not in ("PENDIENTE", "EN_PROCESO", "COMPLETADA", "DESCARTADA"):
        flash("Estado no valido.", "error")
        return redirect(url_for("recomendaciones.listar"))

    asignacion.estado = nuevo_estado
    if nuevo_estado == "COMPLETADA":
        asignacion.fecha_completada = datetime.utcnow()
    else:
        asignacion.fecha_completada = None

    db.session.commit()
    flash("Estado de recomendacion actualizado.", "success")
    return redirect(url_for("recomendaciones.listar"))
