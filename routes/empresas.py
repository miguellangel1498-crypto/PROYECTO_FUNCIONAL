from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Empresa, Evaluacion, ResultadoEvaluacion, Sector, TamanoEmpresa, Usuario
from routes.decoradores import superadmin_requerido

empresas_bp = Blueprint("empresas", __name__, url_prefix="/empresas")


@empresas_bp.route("/")
@login_required
@superadmin_requerido
def listar():
    sector_id = request.args.get("sector", type=int)
    busqueda = request.args.get("q", "").strip()

    consulta = Empresa.query

    if sector_id:
        consulta = consulta.filter(Empresa.id_sector == sector_id)
    if busqueda:
        consulta = consulta.filter(
            db.or_(
                Empresa.nombre.ilike(f"%{busqueda}%"),
                Empresa.nit.ilike(f"%{busqueda}%"),
            )
        )

    empresas = consulta.order_by(Empresa.nombre.asc()).all()
    sectores = Sector.query.order_by(Sector.nombre.asc()).all()
    sector_seleccionado = db.session.get(Sector, sector_id) if sector_id else None

    return render_template(
        "empresas/listar.html",
        empresas=empresas,
        sectores=sectores,
        sector_seleccionado=sector_seleccionado,
        busqueda=busqueda,
    )


@empresas_bp.route("/<int:empresa_id>")
@login_required
@superadmin_requerido
def detalle(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    usuarios = [u for u in empresa.usuarios.all() if u.estado == "ACTIVO"]

    ultimo_eval = (
        Evaluacion.query
        .filter_by(id_empresa=empresa.id_empresa, estado="FINALIZADA")
        .order_by(Evaluacion.fecha_finalizacion.desc())
        .first()
    )
    ultimoResultado = None
    if ultimo_eval:
        ultimoResultado = ResultadoEvaluacion.query.filter_by(id_evaluacion=ultimo_eval.id_evaluacion).first()

    from models import EmpresaRecomendacion
    recomendaciones = []
    if ultimo_eval:
        recomendaciones = EmpresaRecomendacion.query.filter_by(id_evaluacion=ultimo_eval.id_evaluacion).all()

    return render_template(
        "empresas/detalle.html",
        empresa=empresa,
        usuarios=usuarios,
        ultimoResultado=ultimoResultado,
        ultimo_eval=ultimo_eval,
        recomendaciones=recomendaciones,
    )


@empresas_bp.route("/nueva", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def nueva():
    sectores = Sector.query.order_by(Sector.nombre.asc()).all()
    tamanos = TamanoEmpresa.query.order_by(TamanoEmpresa.numero_empleados_min.asc()).all()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        nit = request.form.get("nit", "").strip() or None
        sector_id = request.form.get("sector_id", type=int)
        tamano_id = request.form.get("tamano_id", type=int)
        numero_empleados = request.form.get("numero_empleados", type=int)
        ciudad = request.form.get("ciudad", "").strip() or None
        departamento = request.form.get("departamento", "").strip() or None
        telefono = request.form.get("telefono", "").strip() or None
        correo = request.form.get("correo", "").strip() or None
        sitio_web = request.form.get("sitio_web", "").strip() or None

        if not nombre:
            flash("El nombre de la empresa es obligatorio.", "error")
            return render_template("empresas/form.html", sectores=sectores, tamanos=tamanos, empresa=None)

        if nit and Empresa.query.filter_by(nit=nit).first():
            flash("Ya existe una empresa con ese NIT.", "error")
            return render_template("empresas/form.html", sectores=sectores, tamanos=tamanos, empresa=None)

        empresa = Empresa(
            nombre=nombre,
            nit=nit,
            id_sector=sector_id,
            id_tamano=tamano_id,
            numero_empleados=numero_empleados,
            ciudad=ciudad,
            departamento=departamento,
            telefono=telefono,
            correo=correo,
            sitio_web=sitio_web,
            estado="ACTIVA",
        )
        db.session.add(empresa)
        db.session.commit()

        flash(f"Empresa '{empresa.nombre}' creada correctamente.", "success")
        return redirect(url_for("empresas.listar"))

    return render_template("empresas/form.html", sectores=sectores, tamanos=tamanos, empresa=None)


@empresas_bp.route("/<int:empresa_id>/editar", methods=["GET", "POST"])
@login_required
@superadmin_requerido
def editar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    sectores = Sector.query.order_by(Sector.nombre.asc()).all()
    tamanos = TamanoEmpresa.query.order_by(TamanoEmpresa.numero_empleados_min.asc()).all()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        nit = request.form.get("nit", "").strip() or None

        if not nombre:
            flash("El nombre de la empresa es obligatorio.", "error")
            return render_template("empresas/form.html", sectores=sectores, tamanos=tamanos, empresa=empresa)

        if nit:
            duplicado = Empresa.query.filter(Empresa.nit == nit, Empresa.id_empresa != empresa.id_empresa).first()
            if duplicado:
                flash("Ya existe otra empresa con ese NIT.", "error")
                return render_template("empresas/form.html", sectores=sectores, tamanos=tamanos, empresa=empresa)

        empresa.nombre = nombre
        empresa.nit = nit
        empresa.id_sector = request.form.get("sector_id", type=int)
        empresa.id_tamano = request.form.get("tamano_id", type=int)
        empresa.numero_empleados = request.form.get("numero_empleados", type=int)
        empresa.ciudad = request.form.get("ciudad", "").strip() or None
        empresa.departamento = request.form.get("departamento", "").strip() or None
        empresa.telefono = request.form.get("telefono", "").strip() or None
        empresa.correo = request.form.get("correo", "").strip() or None
        empresa.sitio_web = request.form.get("sitio_web", "").strip() or None

        db.session.commit()
        flash(f"Empresa '{empresa.nombre}' actualizada correctamente.", "success")
        return redirect(url_for("empresas.listar"))

    return render_template("empresas/form.html", sectores=sectores, tamanos=tamanos, empresa=empresa)


@empresas_bp.route("/<int:empresa_id>/eliminar", methods=["POST"])
@login_required
@superadmin_requerido
def eliminar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    nombre = empresa.nombre
    db.session.delete(empresa)
    db.session.commit()
    flash(f"Empresa '{nombre}' eliminada.", "info")
    return redirect(url_for("empresas.listar"))
