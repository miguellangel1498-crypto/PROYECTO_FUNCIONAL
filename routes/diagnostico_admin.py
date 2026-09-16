from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Dimension, OpcionRespuesta, Pregunta, Recomendacion
from routes.decoradores import superadmin_requerido

diagnostico_admin_bp = Blueprint("diagnostico_admin", __name__, url_prefix="/superadmin/diagnostico")


@diagnostico_admin_bp.route("/")
@login_required
@superadmin_requerido
def panel():
    dimensiones = Dimension.query.order_by(Dimension.nombre.asc()).all()
    total_preguntas = Pregunta.query.count()
    total_recomendaciones = Recomendacion.query.count()
    return render_template(
        "superadmin/diagnostico/panel.html",
        dimensiones=dimensiones,
        total_preguntas=total_preguntas,
        total_recomendaciones=total_recomendaciones,
    )


@diagnostico_admin_bp.route("/dimensiones/nueva", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def dimension_nueva():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip() or None
        peso = request.form.get("peso", "1.0").strip()

        if not nombre:
            flash("El nombre de la dimension es obligatorio.", "error")
            return render_template("superadmin/diagnostico/dimension_form.html", dimension=None)

        try:
            peso = float(peso)
        except ValueError:
            peso = 1.0

        if Dimension.query.filter_by(nombre=nombre).first():
            flash("Ya existe una dimension con ese nombre.", "error")
            return render_template("superadmin/diagnostico/dimension_form.html", dimension=None)

        dim = Dimension(nombre=nombre, descripcion=descripcion, peso=peso)
        db.session.add(dim)
        db.session.commit()

        flash(f"Dimension '{nombre}' creada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/dimension_form.html", dimension=None)


@diagnostico_admin_bp.route("/dimensiones/<int:dim_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def dimension_editar(dim_id):
    dim = Dimension.query.get_or_404(dim_id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip() or None
        peso = request.form.get("peso", "1.0").strip()
        estado = request.form.get("estado", "ACTIVA").strip()

        if not nombre:
            flash("El nombre de la dimension es obligatorio.", "error")
            return render_template("superadmin/diagnostico/dimension_form.html", dimension=dim)

        try:
            peso = float(peso)
        except ValueError:
            peso = 1.0

        duplicado = Dimension.query.filter(Dimension.nombre == nombre, Dimension.id_dimension != dim.id_dimension).first()
        if duplicado:
            flash("Ya existe otra dimension con ese nombre.", "error")
            return render_template("superadmin/diagnostico/dimension_form.html", dimension=dim)

        dim.nombre = nombre
        dim.descripcion = descripcion
        dim.peso = peso
        dim.estado = estado
        db.session.commit()

        flash(f"Dimension '{nombre}' actualizada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/dimension_form.html", dimension=dim)


@diagnostico_admin_bp.route("/dimensiones/<int:dim_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def dimension_eliminar(dim_id):
    dim = Dimension.query.get_or_404(dim_id)
    nombre = dim.nombre
    db.session.delete(dim)
    db.session.commit()
    flash(f"Dimension '{nombre}' eliminada.", "info")
    return redirect(url_for("diagnostico_admin.panel"))


@diagnostico_admin_bp.route("/preguntas/nueva", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def pregunta_nueva():
    dimensiones = Dimension.query.filter_by(estado="ACTIVA").order_by(Dimension.nombre.asc()).all()

    if request.method == "POST":
        dimension_id = request.form.get("dimension_id", type=int)
        texto = request.form.get("texto", "").strip()
        tipo_respuesta = request.form.get("tipo_respuesta", "OPCION_UNICA").strip()
        tipo_medicion = request.form.get("tipo_medicion", "AUTOREPORTADO").strip()
        peso = request.form.get("peso", "1.0").strip()
        orden = request.form.get("orden", "1").strip()
        obligatoria = request.form.get("obligatoria") == "on"

        errores = []
        if not texto:
            errores.append("El texto de la pregunta es obligatorio.")
        if not dimension_id:
            errores.append("Debes seleccionar una dimension.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("superadmin/diagnostico/pregunta_form.html", pregunta=None, dimensiones=dimensiones)

        try:
            peso = float(peso)
            orden = int(orden)
        except ValueError:
            peso = 1.0
            orden = 1

        preg = Pregunta(
            id_dimension=dimension_id,
            pregunta=texto,
            tipo_respuesta=tipo_respuesta,
            tipo_medicion=tipo_medicion,
            peso=peso,
            orden=orden,
            obligatoria=obligatoria,
        )
        db.session.add(preg)
        db.session.flush()

        if tipo_respuesta in ("OPCION_UNICA", "SI_NO", "OPCION_MULTIPLE"):
            textos = request.form.getlist("opcion_texto[]")
            valores = request.form.getlist("opcion_valor[]")
            for i, (txt, val) in enumerate(zip(textos, valores)):
                if txt.strip():
                    try:
                        v = float(val)
                    except ValueError:
                        v = 0
                    db.session.add(OpcionRespuesta(
                        id_pregunta=preg.id_pregunta,
                        texto=txt.strip(),
                        valor=v,
                        orden=i + 1,
                    ))

        db.session.commit()
        flash("Pregunta creada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/pregunta_form.html", pregunta=None, dimensiones=dimensiones)


@diagnostico_admin_bp.route("/preguntas/<int:preg_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def pregunta_editar(preg_id):
    preg = Pregunta.query.get_or_404(preg_id)
    dimensiones = Dimension.query.filter_by(estado="ACTIVA").order_by(Dimension.nombre.asc()).all()

    if request.method == "POST":
        preg.id_dimension = request.form.get("dimension_id", type=int)
        preg.pregunta = request.form.get("texto", "").strip()
        preg.tipo_respuesta = request.form.get("tipo_respuesta", "OPCION_UNICA").strip()
        preg.tipo_medicion = request.form.get("tipo_medicion", "AUTOREPORTADO").strip()
        preg.obligatoria = request.form.get("obligatoria") == "on"

        try:
            preg.peso = float(request.form.get("peso", "1.0").strip())
            preg.orden = int(request.form.get("orden", "1").strip())
        except ValueError:
            pass

        if preg.tipo_respuesta in ("OPCION_UNICA", "SI_NO", "OPCION_MULTIPLE"):
            OpcionRespuesta.query.filter_by(id_pregunta=preg.id_pregunta).delete()
            textos = request.form.getlist("opcion_texto[]")
            valores = request.form.getlist("opcion_valor[]")
            for i, (txt, val) in enumerate(zip(textos, valores)):
                if txt.strip():
                    try:
                        v = float(val)
                    except ValueError:
                        v = 0
                    db.session.add(OpcionRespuesta(
                        id_pregunta=preg.id_pregunta,
                        texto=txt.strip(),
                        valor=v,
                        orden=i + 1,
                    ))

        db.session.commit()
        flash("Pregunta actualizada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    opciones = OpcionRespuesta.query.filter_by(id_pregunta=preg.id_pregunta).order_by(OpcionRespuesta.orden).all()
    return render_template("superadmin/diagnostico/pregunta_form.html", pregunta=preg, dimensiones=dimensiones, opciones=opciones)


@diagnostico_admin_bp.route("/preguntas/<int:preg_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def pregunta_eliminar(preg_id):
    preg = Pregunta.query.get_or_404(preg_id)
    db.session.delete(preg)
    db.session.commit()
    flash("Pregunta eliminada.", "info")
    return redirect(url_for("diagnostico_admin.panel"))


@diagnostico_admin_bp.route("/recomendaciones/nueva", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def recomendacion_nueva():
    dimensiones = Dimension.query.filter_by(estado="ACTIVA").order_by(Dimension.nombre.asc()).all()

    if request.method == "POST":
        dimension_id = request.form.get("dimension_id", type=int)
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        prioridad = request.form.get("prioridad", "MEDIA").strip()
        nivel_minimo = request.form.get("nivel_minimo", "0").strip()
        nivel_maximo = request.form.get("nivel_maximo", "100").strip()

        errores = []
        if not titulo:
            errores.append("El titulo de la recomendacion es obligatorio.")
        if not descripcion:
            errores.append("La descripcion es obligatoria.")
        if not dimension_id:
            errores.append("Debes seleccionar una dimension.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("superadmin/diagnostico/recomendacion_form.html", recomendacion=None, dimensiones=dimensiones)

        try:
            nivel_minimo = float(nivel_minimo)
            nivel_maximo = float(nivel_maximo)
        except ValueError:
            nivel_minimo, nivel_maximo = 0, 100

        rec = Recomendacion(
            id_dimension=dimension_id,
            titulo=titulo,
            descripcion=descripcion,
            prioridad=prioridad,
            nivel_minimo=nivel_minimo,
            nivel_maximo=nivel_maximo,
        )
        db.session.add(rec)
        db.session.commit()

        flash("Recomendacion creada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/recomendacion_form.html", recomendacion=None, dimensiones=dimensiones)


@diagnostico_admin_bp.route("/recomendaciones/<int:rec_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def recomendacion_editar(rec_id):
    rec = Recomendacion.query.get_or_404(rec_id)
    dimensiones = Dimension.query.filter_by(estado="ACTIVA").order_by(Dimension.nombre.asc()).all()

    if request.method == "POST":
        rec.id_dimension = request.form.get("dimension_id", type=int)
        rec.titulo = request.form.get("titulo", "").strip()
        rec.descripcion = request.form.get("descripcion", "").strip()
        rec.prioridad = request.form.get("prioridad", "MEDIA").strip()
        rec.estado = request.form.get("estado", "ACTIVA").strip()

        try:
            rec.nivel_minimo = float(request.form.get("nivel_minimo", "0").strip())
            rec.nivel_maximo = float(request.form.get("nivel_maximo", "100").strip())
        except ValueError:
            pass

        db.session.commit()
        flash("Recomendacion actualizada correctamente.", "success")
        return redirect(url_for("diagnostico_admin.panel"))

    return render_template("superadmin/diagnostico/recomendacion_form.html", recomendacion=rec, dimensiones=dimensiones)


@diagnostico_admin_bp.route("/recomendaciones/<int:rec_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def recomendacion_eliminar(rec_id):
    rec = Recomendacion.query.get_or_404(rec_id)
    db.session.delete(rec)
    db.session.commit()
    flash("Recomendacion eliminada.", "info")
    return redirect(url_for("diagnostico_admin.panel"))
