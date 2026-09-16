import json
from datetime import datetime, timedelta

from sqlalchemy import event

from extensions import db
from models.auditoria import Auditoria
from models.empresa import Empresa
from models.sector import Sector


def _contexto_request():
    from flask import has_request_context, request

    if not has_request_context():
        return {"ip": None, "ua": None}

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip:
        ip = ip.split(",")[0].strip()
    ua = (request.user_agent.string or "")[:255] if request.user_agent else None
    return {"ip": ip, "ua": ua}


def _usuario_actual_id():
    from flask_login import current_user

    try:
        if current_user.is_authenticated:
            return current_user.id_usuario
    except Exception:
        pass
    return None


def registrar(accion, tabla_afectada=None, id_registro=None, descripcion=None):
    ctx = _contexto_request()
    registro = Auditoria(
        id_usuario=_usuario_actual_id(),
        accion=accion,
        tabla_afectada=tabla_afectada,
        id_registro=id_registro,
        descripcion=descripcion,
        direccion_ip=ctx["ip"],
    )
    db.session.add(registro)
    return registro


def registrar_y_commit(accion, tabla_afectada=None, id_registro=None, descripcion=None):
    registro = registrar(accion, tabla_afectada, id_registro, descripcion)
    db.session.commit()
    return registro


def registrar_login(usuario, exitoso=True, motivo=None):
    detalle = f"Acceso de {usuario.correo}"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    accion = "LOGIN_EXITOSO" if exitoso else "LOGIN_FALLIDO"
    return registrar(
        accion=accion,
        tabla_afectada="usuarios",
        id_registro=usuario.id_usuario,
        descripcion=detalle,
    )


def registrar_login_fallido(usuario, motivo=None):
    detalle = f"Acceso fallido de {usuario.correo}"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    return registrar(
        accion="LOGIN_FALLIDO",
        tabla_afectada="usuarios",
        id_registro=usuario.id_usuario,
        descripcion=detalle,
    )


def registrar_alerta_superadmin(usuario, motivo=None):
    detalle = f"ALERTA: Intento de acceso fallido a cuenta superadmin ({usuario.correo})"
    if motivo:
        detalle = f"{detalle} - {motivo}"
    return registrar(
        accion="ALERTA_SUPERADMIN",
        tabla_afectada="usuarios",
        id_registro=usuario.id_usuario,
        descripcion=detalle,
    )


def registrar_bloqueo_login(usuario, minutos_restantes=None):
    detalle = f"Cuenta bloqueada temporalmente por intentos fallidos"
    if minutos_restantes is not None:
        detalle = f"{detalle} ({minutos_restantes} min)"
    return registrar(
        accion="LOGIN_BLOQUEADO",
        tabla_afectada="usuarios",
        id_registro=usuario.id_usuario,
        descripcion=f"{detalle} - {usuario.correo}",
    )


def contar_intentos_fallidos(id_registro, ventana_minutos=None):
    """Cuenta los LOGIN_FALLIDO registrados para el id_registro dado."""
    if id_registro is None:
        return 0
    consulta = Auditoria.query.filter(
        Auditoria.accion == "LOGIN_FALLIDO",
        Auditoria.id_registro == id_registro,
    )
    if ventana_minutos:
        desde = datetime.utcnow() - timedelta(minutes=ventana_minutos)
        consulta = consulta.filter(Auditoria.fecha >= desde)
    return consulta.count()


def ultimo_intento_fallido(id_registro):
    if id_registro is None:
        return None
    return (
        Auditoria.query.filter(
            Auditoria.accion == "LOGIN_FALLIDO",
            Auditoria.id_registro == id_registro,
        )
        .order_by(Auditoria.fecha.desc())
        .first()
    )


def bloqueado_por_intentos(
    id_registro,
    max_intentos=5,
    ventana_minutos=15,
    bloqueo_minutos=10,
):
    """Evalua si el usuario con id_registro esta temporalmente bloqueado.

    Los intentos se leen de la tabla de auditoria usando id_registro en vez de
    un contador en la entidad. Devuelve (bloqueado, minutos_restantes,
    intentos_dentro_ventana). El bloqueo se dispara en el intento que alcanza
    el maximo y expira bloqueo_minutos despues de ese mismo intento (no se
    extiende por nuevos fallos posteriores).
    """
    if id_registro is None:
        return False, 0, 0

    desde = datetime.utcnow() - timedelta(minutes=ventana_minutos)
    intentos = (
        Auditoria.query.filter(
            Auditoria.accion == "LOGIN_FALLIDO",
            Auditoria.id_registro == id_registro,
            Auditoria.fecha >= desde,
        )
        .order_by(Auditoria.fecha.asc())
        .all()
    )
    total = len(intentos)
    if total < max_intentos:
        return False, 0, total

    desencadenante = intentos[total - max_intentos]
    fin_bloqueo = desencadenante.fecha + timedelta(minutes=bloqueo_minutos)
    ahora = datetime.utcnow()

    if ahora >= fin_bloqueo:
        return False, 0, total

    segundos_restantes = (fin_bloqueo - ahora).total_seconds()
    minutos = int(segundos_restantes // 60) + (1 if segundos_restantes % 60 else 0)
    return True, minutos, total


class AutoAuditoria:
    MODELOS_VIGILADOS = (Empresa, Sector)

    @classmethod
    def configurar(cls):
        event.listen(db.session, "before_flush", cls._antes_del_flush)
        event.listen(db.session, "after_flush", cls._despues_del_flush)

    @classmethod
    def _antes_del_flush(cls, sesion, flush_context, instancias=None):
        if not cls._activo():
            return

        pendientes = []
        for obj in sesion.new:
            if isinstance(obj, cls.MODELOS_VIGILADOS):
                pendientes.append((obj, "INSERT", None))
        for obj in sesion.dirty:
            if isinstance(obj, cls.MODELOS_VIGILADOS) and sesion.is_modified(obj, include_collections=False):
                pendientes.append((obj, "UPDATE", cls._cambios(obj)))
        for obj in sesion.deleted:
            if isinstance(obj, cls.MODELOS_VIGILADOS):
                pendientes.append((obj, "DELETE", None))

        if pendientes:
            sesion.info["_gh_audit_pendientes"] = pendientes

    @classmethod
    def _despues_del_flush(cls, sesion, flush_context):
        pendientes = sesion.info.pop("_gh_audit_pendientes", [])
        if not pendientes:
            return

        usuario_id = _usuario_actual_id()
        ctx = _contexto_request()

        for obj, accion, detalle in pendientes:
            sesion.add(
                Auditoria(
                    id_usuario=usuario_id,
                    accion=accion,
                    tabla_afectada=obj.__tablename__,
                    id_registro=cls._id_registro(obj),
                    descripcion=detalle,
                    direccion_ip=ctx["ip"],
                )
            )

    @staticmethod
    def _id_registro(obj):
        identidad = db.inspect(obj).identity
        if identidad:
            return identidad[0]
        columnas_pk = list(obj.__table__.primary_key.columns)
        if columnas_pk:
            return getattr(obj, columnas_pk[0].key, None)
        return None

    @staticmethod
    def _activo():
        from flask import has_request_context
        from flask_login import current_user

        if not has_request_context():
            return False
        try:
            return current_user.is_authenticated
        except Exception:
            return False

    @staticmethod
    def _cambios(obj):
        state = db.inspect(obj)
        cambios = {}
        for col in obj.__table__.columns:
            nombre = col.key
            if nombre in {"created_at", "updated_at", "fecha", "fecha_registro"}:
                continue
            try:
                historia = state.attrs[nombre].history
            except Exception:
                continue
            if historia.has_changes():
                anterior = historia.deleted[0] if historia.deleted else (
                    historia.unchanged[-1] if historia.unchanged else None
                )
                nuevo = historia.added[0] if historia.added else None
                if anterior != nuevo:
                    cambios[nombre] = {"anterior": anterior, "nuevo": nuevo}
        return json.dumps(cambios, ensure_ascii=False, default=str)
