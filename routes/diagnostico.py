from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Dimension, Evaluacion, Pregunta, Respuesta
from routes.decoradores import admin_empresa_requerido

diagnostico_bp = Blueprint("diagnostico", __name__, url_prefix="/diagnostico")


def _empresa_id():
    if current_user.empresa is None:
        abort(403)
    if not current_user.acceso_empresa_activa:
        abort(403)
    return current_user.empresa.id_empresa


@diagnostico_bp.route("/iniciar")
@login_required
@admin_empresa_requerido
def iniciar():
    empresa_id = _empresa_id()
    evaluacion_pendiente = (
        Evaluacion.query
        .filter_by(id_empresa=empresa_id, estado="EN_PROCESO")
        .order_by(Evaluacion.fecha_inicio.desc())
        .first()
    )
    if evaluacion_pendiente:
        return redirect(url_for("diagnostico.responder", id_evaluacion=evaluacion_pendiente.id_evaluacion))

    evaluacion = Evaluacion(
        id_empresa=empresa_id,
        id_usuario=current_user.id_usuario,
        estado="EN_PROCESO",
    )
    db.session.add(evaluacion)
    db.session.commit()
    flash("Nueva evaluacion iniciada.", "success")
    return redirect(url_for("diagnostico.responder", id_evaluacion=evaluacion.id_evaluacion))


@diagnostico_bp.route("/responder/<int:id_evaluacion>", methods=["GET", "POST"])
@login_required
@admin_empresa_requerido
def responder(id_evaluacion):
    empresa_id = _empresa_id()
    evaluacion = Evaluacion.query.get_or_404(id_evaluacion)
    if evaluacion.id_empresa != empresa_id:
        abort(403)
    if evaluacion.estado != "EN_PROCESO":
        flash("Esta evaluacion ya fue finalizada y no puede editarse.", "warning")
        return redirect(url_for("diagnostico.resultados", id_evaluacion=id_evaluacion))

    if request.method == "POST":
        preguntas_activas = (
            Pregunta.query
            .join(Dimension)
            .filter(Pregunta.estado == "ACTIVA", Pregunta.tipo_medicion == "AUTOREPORTADO")
            .order_by(Dimension.id_dimension, Pregunta.orden)
            .all()
        )
        for preg in preguntas_activas:
            valor_texto = request.form.get(f"pregunta_texto_{preg.id_pregunta}", "").strip()
            valor_numerico = request.form.get(f"pregunta_num_{preg.id_pregunta}", "").strip()
            opcion_id = request.form.get(f"pregunta_opcion_{preg.id_pregunta}", type=int)

            respuesta_existente = (
                Respuesta.query
                .filter_by(id_evaluacion=id_evaluacion, id_pregunta=preg.id_pregunta)
                .first()
            )

            if preg.tipo_respuesta in ("OPCION_UNICA", "SI_NO") and opcion_id:
                if respuesta_existente:
                    respuesta_existente.id_opcion = opcion_id
                    respuesta_existente.respuesta_texto = None
                    respuesta_existente.respuesta_numerica = None
                else:
                    db.session.add(Respuesta(
                        id_evaluacion=id_evaluacion,
                        id_pregunta=preg.id_pregunta,
                        id_opcion=opcion_id,
                    ))
            elif preg.tipo_respuesta == "OPCION_MULTIPLE":
                opciones_ids = request.form.getlist(f"pregunta_multi_{preg.id_pregunta}")
                if respuesta_existente:
                    respuesta_existente.id_opcion = None
                    respuesta_existente.respuesta_texto = ",".join(str(x) for x in opciones_ids) if opciones_ids else None
                else:
                    db.session.add(Respuesta(
                        id_evaluacion=id_evaluacion,
                        id_pregunta=preg.id_pregunta,
                        respuesta_texto=",".join(str(x) for x in opciones_ids) if opciones_ids else None,
                    ))
            elif preg.tipo_respuesta == "NUMERICA" and valor_numerico:
                try:
                    num_val = float(valor_numerico)
                except ValueError:
                    continue
                if respuesta_existente:
                    respuesta_existente.respuesta_numerica = num_val
                    respuesta_existente.id_opcion = None
                    respuesta_existente.respuesta_texto = None
                else:
                    db.session.add(Respuesta(
                        id_evaluacion=id_evaluacion,
                        id_pregunta=preg.id_pregunta,
                        respuesta_numerica=num_val,
                    ))
            elif preg.tipo_respuesta == "TEXTO" and valor_texto:
                if respuesta_existente:
                    respuesta_existente.respuesta_texto = valor_texto
                    respuesta_existente.id_opcion = None
                    respuesta_existente.respuesta_numerica = None
                else:
                    db.session.add(Respuesta(
                        id_evaluacion=id_evaluacion,
                        id_pregunta=preg.id_pregunta,
                        respuesta_texto=valor_texto,
                    ))

        db.session.commit()
        flash("Respuestas guardadas correctamente.", "success")
        return redirect(url_for("diagnostico.responder", id_evaluacion=id_evaluacion))

    dimensiones = Dimension.query.filter_by(estado="ACTIVA").order_by(Dimension.nombre.asc()).all()
    preguntas_por_dim = {}
    for dim in dimensiones:
        preguntas = (
            Pregunta.query
            .filter_by(id_dimension=dim.id_dimension, estado="ACTIVA")
            .order_by(Pregunta.orden.asc())
            .all()
        )
        if preguntas:
            preguntas_por_dim[dim] = preguntas

    respuestas_existentes = {}
    respuestas_db = Respuesta.query.filter_by(id_evaluacion=id_evaluacion).all()
    for r in respuestas_db:
        respuestas_existentes[r.id_pregunta] = r

    total_obligatorias = sum(
        1 for dim in preguntas_por_dim for p in preguntas_por_dim[dim] if p.obligatoria
    )
    respondidas = sum(
        1 for dim in preguntas_por_dim for p in preguntas_por_dim[dim]
        if p.id_pregunta in respuestas_existentes and p.obligatoria
    )
    faltan = total_obligatorias - respondidas

    return render_template(
        "diagnostico/cuestionario.html",
        evaluacion=evaluacion,
        dimensiones=preguntas_por_dim,
        respuestas_existentes=respuestas_existentes,
        total_obligatorias=total_obligatorias,
        respondidas=respondidas,
        faltan=faltan,
    )


@diagnostico_bp.route("/finalizar/<int:id_evaluacion>", methods=["POST"])
@login_required
@admin_empresa_requerido
def finalizar(id_evaluacion):
    empresa_id = _empresa_id()
    evaluacion = Evaluacion.query.get_or_404(id_evaluacion)
    if evaluacion.id_empresa != empresa_id:
        abort(403)
    if evaluacion.estado != "EN_PROCESO":
        flash("Esta evaluacion ya fue finalizada.", "warning")
        return redirect(url_for("diagnostico.resultados", id_evaluacion=id_evaluacion))

    preguntas_obligatorias = (
        Pregunta.query
        .filter_by(estado="ACTIVA", tipo_medicion="AUTOREPORTADO", obligatoria=True)
        .all()
    )
    ids_obligatorias = {p.id_pregunta for p in preguntas_obligatorias}
    respuestas_ids = {
        r.id_pregunta for r in Respuesta.query.filter_by(id_evaluacion=id_evaluacion).all()
    }
    faltan = ids_obligatorias - respuestas_ids
    if faltan:
        flash(f"Faltan {len(faltan)} preguntas obligatorias por responder.", "error")
        return redirect(url_for("diagnostico.responder", id_evaluacion=id_evaluacion))

    evaluacion.estado = "FINALIZADA"
    evaluacion.fecha_finalizacion = datetime.utcnow()
    db.session.commit()

    from routes.analisis import calcular_resultados_evaluacion
    calcular_resultados_evaluacion(id_evaluacion)

    flash("Evaluacion finalizada y resultados calculados.", "success")
    return redirect(url_for("diagnostico.resultados", id_evaluacion=id_evaluacion))


@diagnostico_bp.route("/resultados/<int:id_evaluacion>")
@login_required
@admin_empresa_requerido
def resultados(id_evaluacion):
    empresa_id = _empresa_id()
    evaluacion = Evaluacion.query.get_or_404(id_evaluacion)
    if evaluacion.id_empresa != empresa_id:
        abort(403)
    if evaluacion.estado != "FINALIZADA":
        flash("Esta evaluacion aun no ha sido finalizada.", "warning")
        return redirect(url_for("diagnostico.responder", id_evaluacion=id_evaluacion))

    from models import EmpresaRecomendacion, ResultadoDimension, ResultadoEvaluacion

    resultado = ResultadoEvaluacion.query.filter_by(id_evaluacion=id_evaluacion).first()
    dimensiones_resultado = []
    if resultado:
        dimensiones_resultado = (
            ResultadoDimension.query
            .filter_by(id_resultado=resultado.id_resultado)
            .all()
        )

    recomendaciones = EmpresaRecomendacion.query.filter_by(id_evaluacion=id_evaluacion).all()

    return render_template(
        "diagnostico/resultados.html",
        evaluacion=evaluacion,
        resultado=resultado,
        dimensiones_resultado=dimensiones_resultado,
        recomendaciones=recomendaciones,
    )


@diagnostico_bp.route("/historial")
@login_required
@admin_empresa_requerido
def historial():
    empresa_id = _empresa_id()
    evaluaciones = (
        Evaluacion.query
        .filter_by(id_empresa=empresa_id, estado="FINALIZADA")
        .order_by(Evaluacion.fecha_finalizacion.desc())
        .all()
    )
    return render_template("diagnostico/historial.html", evaluaciones=evaluaciones)
