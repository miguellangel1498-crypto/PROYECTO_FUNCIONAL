import re
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from extensions import db
from models import Empresa, Rol, Sector, TamanoEmpresa, Usuario
from services.auditoria import (
    bloqueado_por_intentos,
    contar_intentos_fallidos,
    registrar_alerta_superadmin,
    registrar_bloqueo_login,
    registrar_login,
    registrar_login_fallido,
    registrar_y_commit,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    max_intentos = current_app.config.get("MAX_INTENTOS_LOGIN", 5)
    ventana_minutos = current_app.config.get("VENTANA_INTENTOS_MINUTOS", 15)
    bloqueo_minutos = current_app.config.get("BLOQUEO_LOGIN_MINUTOS", 10)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        recuerdame = request.form.get("recordarme") == "on"

        usuario = Usuario.query.filter(db.func.lower(Usuario.correo) == email).first()

        if usuario is None:
            flash("Credenciales invalidas.", "error")
            return render_template("auth/login.html"), 401

        # Los intentos fallidos se validan leyendo la auditoria por id_registro:
        # si el usuario ya supero el maximo dentro de la ventana, se bloquea
        # temporalmente el acceso.
        bloqueado, minutos_restantes, _ = bloqueado_por_intentos(
            usuario.id_usuario,
            max_intentos=max_intentos,
            ventana_minutos=ventana_minutos,
            bloqueo_minutos=bloqueo_minutos,
        )
        if bloqueado:
            if usuario.es_superadmin:
                db.session.add(
                    registrar_alerta_superadmin(
                        usuario,
                        motivo="Cuenta bloqueada temporalmente por intentos fallidos",
                    )
                )
            registro = registrar_bloqueo_login(usuario, minutos_restantes=minutos_restantes)
            if registro:
                db.session.add(registro)
            db.session.commit()
            flash(
                f"Cuenta temporalmente bloqueada por demasiados intentos fallidos. "
                f"Intenta nuevamente en hasta {minutos_restantes} minuto(s).",
                "error",
            )
            return render_template("auth/login.html"), 423

        if not usuario.check_password(password):
            registro = registrar_login_fallido(usuario, motivo="Contrasena incorrecta")
            if registro:
                db.session.add(registro)
            db.session.commit()

            intentos = contar_intentos_fallidos(
                id_registro=usuario.id_usuario,
                ventana_minutos=ventana_minutos,
            )
            restantes = max(max_intentos - intentos, 0)
            if restantes <= 0:
                flash(
                    "Credenciales invalidas. Por demasiados intentos fallidos la cuenta "
                    f"queda bloqueada temporalmente por {bloqueo_minutos} minuto(s).",
                    "error",
                )
            else:
                flash(
                    f"Credenciales invalidas. Te quedan {restantes} intento(s) antes del bloqueo temporal.",
                    "error",
                )
            return render_template("auth/login.html"), 401

        if usuario.estado != "ACTIVO":
            registro = registrar_login(usuario, exitoso=False, motivo="Cuenta inactiva/bloqueada")
            if registro:
                db.session.add(registro)
            db.session.commit()
            flash("Tu cuenta esta inactiva o bloqueada. Contacta al administrador.", "error")
            return render_template("auth/login.html"), 403

        if usuario.empresa is not None and not usuario.empresa.esta_activa:
            registro = registrar_login(
                usuario,
                exitoso=False,
                motivo=f"Empresa {usuario.empresa.estado}",
            )
            if registro:
                db.session.add(registro)
            db.session.commit()
            flash("El acceso de tu empresa esta inactivo. Contacta al administrador.", "error")
            return render_template("auth/login.html"), 403

        login_user(usuario, remember=recuerdame)
        session.permanent = True
        usuario.ultimo_acceso = datetime.utcnow()
        db.session.commit()
        registrar_y_commit(
            "LOGIN_EXITOSO",
            tabla_afectada="usuarios",
            id_registro=usuario.id_usuario,
            descripcion=f"Ingreso de {usuario.correo}",
        )

        flash(f"Bienvenido/a de nuevo, {usuario.nombre}!", "success")
        siguiente = request.args.get("next")
        if siguiente and siguiente.startswith("/"):
            return redirect(siguiente)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmar = request.form.get("confirmar_password", "")
        telefono = request.form.get("telefono", "").strip() or None

        errores = []
        if not nombre or not apellido or not email or not password:
            errores.append("Todos los campos obligatorios son requeridos.")
        if len(password) < 8:
            errores.append("La contrasena debe tener al menos 8 caracteres.")
        elif not re.search(r"[A-Z]", password) or not re.search(r"[0-9]", password):
            errores.append("La contrasena debe incluir al menos una mayuscula y un numero.")
        if password != confirmar:
            errores.append("Las contrasenas no coinciden.")
        if Usuario.query.filter_by(correo=email).first():
            errores.append("Ya existe una cuenta con ese correo.")

        nombre_empresa = request.form.get("nombre_empresa", "").strip()
        nit = request.form.get("nit", "").strip() or None
        sector_id = request.form.get("sector_id", type=int) or None
        tamano_id = request.form.get("tamano_id", type=int) or None
        ciudad = request.form.get("ciudad", "").strip() or None
        departamento = request.form.get("departamento", "").strip() or None
        correo_empresa = request.form.get("correo_empresa", "").strip() or None
        telefono_empresa = request.form.get("telefono_empresa", "").strip() or None
        sitio_web = request.form.get("sitio_web", "").strip() or None
        numero_empleados = request.form.get("numero_empleados", type=int) or None

        if not nombre_empresa:
            errores.append("El nombre de la empresa es obligatorio.")
        if not sector_id:
            errores.append("Selecciona el sector de la empresa.")
        if not tamano_id:
            errores.append("Selecciona el tamano de la empresa.")
        if nit and Empresa.query.filter_by(nit=nit).first():
            errores.append("Ya existe una empresa con ese NIT.")

        if errores:
            for e in errores:
                flash(e, "error")
            sectores = Sector.query.order_by(Sector.nombre.asc()).all()
            tamanos = TamanoEmpresa.query.order_by(TamanoEmpresa.numero_empleados_min.asc()).all()
            return render_template(
                "auth/registro.html",
                sectores=sectores,
                tamanos=tamanos,
                datos_empresa={
                    "nombre_empresa": nombre_empresa,
                    "nit": nit,
                    "ciudad": ciudad,
                    "departamento": departamento,
                    "correo_empresa": correo_empresa,
                    "telefono_empresa": telefono_empresa,
                    "sitio_web": sitio_web,
                    "numero_empleados": numero_empleados,
                },
            )

        empresa = Empresa(
            nombre=nombre_empresa,
            nit=nit,
            id_sector=sector_id,
            id_tamano=tamano_id,
            numero_empleados=numero_empleados,
            ciudad=ciudad,
            departamento=departamento,
            telefono=telefono_empresa,
            correo=correo_empresa,
            sitio_web=sitio_web,
            estado="ACTIVA",
        )
        db.session.add(empresa)
        db.session.flush()

        usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            correo=email,
            telefono=telefono,
            id_empresa=empresa.id_empresa,
        )
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.flush()

        # Asignacion automatica del rol EMPRESA sobre el usuario recien creado
        rol_empresa = Rol.query.filter_by(nombre="EMPRESA").first()
        if rol_empresa:
            usuario.roles_list.append(rol_empresa)
        db.session.commit()

        login_user(usuario)
        session.permanent = True
        usuario.ultimo_acceso = datetime.utcnow()
        db.session.commit()

        registrar_y_commit(
            "REGISTRO_EMPRESA",
            tabla_afectada="usuarios",
            id_registro=usuario.id_usuario,
            descripcion=f"Nueva empresa {nombre_empresa} ({email})",
        )

        flash(
            "Empresa registrada correctamente. Ya puedes acceder a la plataforma.",
            "success",
        )
        return redirect(url_for("main.index"))

    sectores = Sector.query.order_by(Sector.nombre.asc()).all()
    tamanos = TamanoEmpresa.query.order_by(TamanoEmpresa.numero_empleados_min.asc()).all()
    return render_template(
        "auth/registro.html",
        sectores=sectores,
        tamanos=tamanos,
        datos_empresa=None,
    )


@auth_bp.route("/salir")
def logout():
    if current_user.is_authenticated:
        registrar_y_commit(
            "LOGOUT",
            tabla_afectada="usuarios",
            id_registro=current_user.id_usuario,
            descripcion=f"Cierre de sesion de {current_user.correo}",
        )
    logout_user()
    session.clear()
    respuesta = redirect(url_for("main.index"))
    respuesta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    respuesta.headers["Pragma"] = "no-cache"
    flash("Has cerrado sesion correctamente.", "info")
    return respuesta
