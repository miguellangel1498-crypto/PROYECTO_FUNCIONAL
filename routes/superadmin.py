from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Empresa, Evaluacion, ResultadoEvaluacion, Rol, Sector, TamanoEmpresa, Usuario
from routes.decoradores import superadmin_requerido
from services.auditoria import registrar_y_commit

superadmin_bp = Blueprint("superadmin", __name__, url_prefix="/superadmin")


def _empresa_o_404(empresa_id):
    return Empresa.query.get_or_404(empresa_id)


@superadmin_bp.route("/")
@login_required
@superadmin_requerido
def panel():
    total_empresas = Empresa.query.count()
    empresas_activas = Empresa.query.filter_by(estado="ACTIVA").count()
    empresas_inactivas = Empresa.query.filter_by(estado="INACTIVA").count()
    total_usuarios = Usuario.query.count()
    total_evaluaciones = Evaluacion.query.filter_by(estado="FINALIZADA").count()

    return render_template(
        "superadmin/panel.html",
        total_empresas=total_empresas,
        empresas_activas=empresas_activas,
        empresas_inactivas=empresas_inactivas,
        total_usuarios=total_usuarios,
        total_evaluaciones=total_evaluaciones,
    )


@superadmin_bp.route("/empresas")
@login_required
@superadmin_requerido
def empresas():
    estado = request.args.get("estado", "").strip()
    busqueda = request.args.get("q", "").strip()

    consulta = Empresa.query
    if estado in ("ACTIVA", "INACTIVA"):
        consulta = consulta.filter(Empresa.estado == estado)
    if busqueda:
        consulta = consulta.filter(
            db.or_(
                Empresa.nombre.ilike(f"%{busqueda}%"),
                Empresa.nit.ilike(f"%{busqueda}%"),
            )
        )

    empresas = consulta.order_by(Empresa.nombre.asc()).all()
    return render_template(
        "superadmin/empresas.html",
        empresas=empresas,
        estado=estado,
        busqueda=busqueda,
    )


@superadmin_bp.route("/empresas/<int:empresa_id>/activar", methods=["POST"])
@login_required
@superadmin_requerido
def activar_empresa(empresa_id):
    empresa = _empresa_o_404(empresa_id)
    empresa.estado = "ACTIVA"
    db.session.commit()
    registrar_y_commit(
        "EMPRESA_ACTIVADA",
        tabla_afectada="empresas",
        id_registro=empresa.id_empresa,
        descripcion=f"Empresa {empresa.nombre} activada por {current_user.correo}",
    )
    flash(f"La empresa '{empresa.nombre}' fue activada.", "success")
    return redirect(url_for("superadmin.empresas"))


@superadmin_bp.route("/empresas/<int:empresa_id>/inactivar", methods=["POST"])
@login_required
@superadmin_requerido
def inactivar_empresa(empresa_id):
    empresa = _empresa_o_404(empresa_id)
    empresa.estado = "INACTIVA"
    db.session.commit()
    registrar_y_commit(
        "EMPRESA_INACTIVADA",
        tabla_afectada="empresas",
        id_registro=empresa.id_empresa,
        descripcion=f"Empresa {empresa.nombre} inactivada por {current_user.correo}",
    )
    flash(f"La empresa '{empresa.nombre}' fue inactivada.", "info")
    return redirect(url_for("superadmin.empresas"))


@superadmin_bp.route("/empresas/<int:empresa_id>")
@login_required
@superadmin_requerido
def detalle_empresa(empresa_id):
    empresa = _empresa_o_404(empresa_id)

    usuarios = (
        Usuario.query.filter_by(id_empresa=empresa.id_empresa)
        .order_by(Usuario.nombre.asc())
        .all()
    )

    ultimo_eval = (
        Evaluacion.query
        .filter_by(id_empresa=empresa.id_empresa, estado="FINALIZADA")
        .order_by(Evaluacion.fecha_finalizacion.desc())
        .first()
    )
    ultimoResultado = None
    if ultimo_eval:
        ultimoResultado = ResultadoEvaluacion.query.filter_by(id_evaluacion=ultimo_eval.id_evaluacion).first()

    return render_template(
        "superadmin/detalle_empresa.html",
        empresa=empresa,
        usuarios=usuarios,
        ultimoResultado=ultimoResultado,
        ultimo_eval=ultimo_eval,
    )


@superadmin_bp.route("/sectores")
@login_required
@superadmin_requerido
def sectores():
    sectores = Sector.query.order_by(Sector.nombre.asc()).all()
    return render_template("superadmin/sectores.html", sectores=sectores)


@superadmin_bp.route("/sectores/nuevo", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def sector_nuevo():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip() or None

        if not nombre:
            flash("El nombre del sector es obligatorio.", "error")
            return render_template("superadmin/sector_form.html", sector=None)

        if Sector.query.filter_by(nombre=nombre).first():
            flash("Ya existe un sector con ese nombre.", "error")
            return render_template("superadmin/sector_form.html", sector=None)

        sector = Sector(nombre=nombre, descripcion=descripcion)
        db.session.add(sector)
        db.session.commit()
        flash(f"Sector '{sector.nombre}' creado correctamente.", "success")
        return redirect(url_for("superadmin.sectores"))

    return render_template("superadmin/sector_form.html", sector=None)


@superadmin_bp.route("/sectores/<int:sector_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def sector_editar(sector_id):
    sector = Sector.query.get_or_404(sector_id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre del sector es obligatorio.", "error")
            return render_template("superadmin/sector_form.html", sector=sector)

        duplicado = Sector.query.filter(Sector.nombre == nombre, Sector.id_sector != sector.id_sector).first()
        if duplicado:
            flash("Ya existe otro sector con ese nombre.", "error")
            return render_template("superadmin/sector_form.html", sector=sector)

        sector.nombre = nombre
        sector.descripcion = request.form.get("descripcion", "").strip() or None
        db.session.commit()
        flash(f"Sector '{sector.nombre}' actualizado correctamente.", "success")
        return redirect(url_for("superadmin.sectores"))

    return render_template("superadmin/sector_form.html", sector=sector)


@superadmin_bp.route("/sectores/<int:sector_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def sector_eliminar(sector_id):
    sector = Sector.query.get_or_404(sector_id)
    if sector.empresas.count() > 0:
        flash("No se puede eliminar el sector porque tiene empresas asociadas.", "error")
        return redirect(url_for("superadmin.sectores"))
    nombre = sector.nombre
    db.session.delete(sector)
    db.session.commit()
    flash(f"Sector '{nombre}' eliminado.", "info")
    return redirect(url_for("superadmin.sectores"))


@superadmin_bp.route("/tamanos")
@login_required
@superadmin_requerido
def tamanos():
    tamanos = TamanoEmpresa.query.order_by(TamanoEmpresa.numero_empleados_min.asc()).all()
    return render_template("superadmin/tamanos.html", tamanos=tamanos)


@superadmin_bp.route("/tamanos/nuevo", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def tamano_nuevo():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip() or None
        min_emp = request.form.get("numero_empleados_min", type=int)
        max_emp = request.form.get("numero_empleados_max", type=int)

        if not nombre:
            flash("El nombre es obligatorio.", "error")
            return render_template("superadmin/tamano_form.html", tamano=None)

        if TamanoEmpresa.query.filter_by(nombre=nombre).first():
            flash("Ya existe un tamano con ese nombre.", "error")
            return render_template("superadmin/tamano_form.html", tamano=None)

        tamano = TamanoEmpresa(nombre=nombre, descripcion=descripcion, numero_empleados_min=min_emp, numero_empleados_max=max_emp)
        db.session.add(tamano)
        db.session.commit()
        flash(f"Tamano '{tamano.nombre}' creado correctamente.", "success")
        return redirect(url_for("superadmin.tamanos"))

    return render_template("superadmin/tamano_form.html", tamano=None)


@superadmin_bp.route("/tamanos/<int:tamano_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def tamano_editar(tamano_id):
    tamano = TamanoEmpresa.query.get_or_404(tamano_id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "error")
            return render_template("superadmin/tamano_form.html", tamano=tamano)

        duplicado = TamanoEmpresa.query.filter(TamanoEmpresa.nombre == nombre, TamanoEmpresa.id_tamano != tamano.id_tamano).first()
        if duplicado:
            flash("Ya existe otro tamano con ese nombre.", "error")
            return render_template("superadmin/tamano_form.html", tamano=tamano)

        tamano.nombre = nombre
        tamano.descripcion = request.form.get("descripcion", "").strip() or None
        tamano.numero_empleados_min = request.form.get("numero_empleados_min", type=int)
        tamano.numero_empleados_max = request.form.get("numero_empleados_max", type=int)
        db.session.commit()
        flash(f"Tamano '{tamano.nombre}' actualizado correctamente.", "success")
        return redirect(url_for("superadmin.tamanos"))

    return render_template("superadmin/tamano_form.html", tamano=tamano)


@superadmin_bp.route("/tamanos/<int:tamano_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def tamano_eliminar(tamano_id):
    tamano = TamanoEmpresa.query.get_or_404(tamano_id)
    if tamano.empresas.count() > 0:
        flash("No se puede eliminar porque tiene empresas asociadas.", "error")
        return redirect(url_for("superadmin.tamanos"))
    nombre = tamano.nombre
    db.session.delete(tamano)
    db.session.commit()
    flash(f"Tamano '{nombre}' eliminado.", "info")
    return redirect(url_for("superadmin.tamanos"))


@superadmin_bp.route("/ranking")
@login_required
@superadmin_requerido
def ranking():
    from routes.analisis import _ranking_empresas

    ranking = _ranking_empresas()
    empresas_ranking = []
    for emp_id, nombre, indice, nivel in ranking:
        empresas_ranking.append({
            "id": emp_id,
            "nombre": nombre,
            "indice": round(float(indice), 2),
            "nivel": nivel,
        })
    return render_template("superadmin/ranking.html", empresas_ranking=empresas_ranking)
