import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

_EN_PRODUCCION = os.environ.get("FLASK_ENV", "development") == "production"


def _resolver_secret_key():
    clave = os.environ.get("SECRET_KEY")
    if clave:
        return clave
    if _EN_PRODUCCION:
        raise RuntimeError(
            "SECRET_KEY es obligatoria en produccion. Define la variable de entorno "
            "SECRET_KEY antes de iniciar la aplicacion."
        )
    return "growth-horizon-dev-secret"


class Config:
    SECRET_KEY = _resolver_secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root@localhost/growthhorizon?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Sesiones ──────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "gh_session"
    SESSION_COOKIE_SECURE = _EN_PRODUCCION

    # ── Cookie "Recuerdame" ───────────────────────────────────
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = _EN_PRODUCCION

    WTF_CSRF_ENABLED = True

    # ── Seguridad de acceso: intentos fallidos y bloqueo ─────
    # Los intentos fallidos se cuentan vía la tabla de auditoría
    # (accion='LOGIN_FALLIDO', id_registro=<id del usuario>).
    MAX_INTENTOS_LOGIN = int(os.environ.get("MAX_INTENTOS_LOGIN", "5"))
    VENTANA_INTENTOS_MINUTOS = int(os.environ.get("VENTANA_INTENTOS_MINUTOS", "15"))
    BLOQUEO_LOGIN_MINUTOS = int(os.environ.get("BLOQUEO_LOGIN_MINUTOS", "10"))
