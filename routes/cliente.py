from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Auditoria, Usuario
from routes.decoradores import admin_empresa_requerido

cliente_bp = Blueprint("cliente", __name__, url_prefix="/mi-empresa")


def _empresa_id():
    if current_user.empresa is None:
        from flask import abort
        abort(403)
    if not current_user.acceso_empresa_activa:
        from flask import abort
        abort(403)
    return current_user.empresa.id_empresa


@cliente_bp.route("/")
@login_required
@admin_empresa_requerido
def panel():
    if not current_user.acceso_empresa_activa:
        from flask import abort
        abort(403)
    empresa = current_user.empresa

    from models import Evaluacion, ResultadoEvaluacion

    ultima_eval = (
        Evaluacion.query
        .filter_by(id_empresa=empresa.id_empresa, estado="FINALIZADA")
        .order_by(Evaluacion.fecha_finalizacion.desc())
        .first()
    )
    ultimoResultado = None
    if ultima_eval:
        ultimoResultado = ResultadoEvaluacion.query.filter_by(id_evaluacion=ultima_eval.id_evaluacion).first()

    total_evaluaciones = Evaluacion.query.filter_by(id_empresa=empresa.id_empresa, estado="FINALIZADA").count()

    return render_template(
        "cliente/panel.html",
        empresa=empresa,
        ultimoResultado=ultimoResultado,
        ultima_eval=ultima_eval,
    )
