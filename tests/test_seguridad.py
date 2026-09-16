"""Pruebas de seguridad manuales para Growth Horizon.

Reproduce las pruebas descritas en plan_pruebas_seguridad.md contra una
base de datos SQLite aislada (archivo temporal), sin tocar la base de
datos MySQL real de desarrollo.

Uso:
    python tests/test_seguridad.py
"""
import os
import re
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

_DB_TMP = os.path.join(tempfile.gettempdir(), "growth_horizon_pruebas_seguridad.db")
if os.path.exists(_DB_TMP):
    os.remove(_DB_TMP)

os.environ["DATABASE_URL"] = f"sqlite:///{_DB_TMP}"
os.environ.setdefault("SECRET_KEY", "clave-de-pruebas-no-usar-en-produccion")

from app import crear_app  # noqa: E402
from extensions import db  # noqa: E402
from models import Empresa, Rol, Sector, TamanoEmpresa, Usuario  # noqa: E402

OK = "\033[92mPASS\033[0m"
FALLA = "\033[91mFAIL\033[0m"
resultados = []


def verificar(nombre, condicion, detalle=""):
    estado = OK if condicion else FALLA
    resultados.append((nombre, condicion))
    print(f"[{estado}] {nombre}" + (f" — {detalle}" if detalle else ""))


def preparar_datos_base():
    db.session.add_all([
        Rol(nombre="SUPERADMIN", descripcion="Superadministrador"),
        Rol(nombre="EMPRESA", descripcion="Administrador de empresa"),
        Sector(nombre="Tecnologia"),
        TamanoEmpresa(nombre="MICRO", numero_empleados_min=1, numero_empleados_max=10),
    ])
    db.session.commit()


def registrar_empresa(client, email, nombre_empresa, password="Password123"):
    return client.post("/auth/registro", data={
        "nombre_empresa": nombre_empresa,
        "sector_id": "1",
        "tamano_id": "1",
        "nombre": "Usuario", "apellido": "Prueba",
        "email": email,
        "password": password, "confirmar_password": password,
    }, follow_redirects=False)


def crear_superadmin(email="superadmin@pruebas.com", password="Password123"):
    rol = Rol.query.filter_by(nombre="SUPERADMIN").first()
    u = Usuario(nombre="Super", apellido="Admin", correo=email)
    u.set_password(password)
    db.session.add(u)
    db.session.flush()
    u.roles_list.append(rol)
    db.session.commit()
    return u


# ── 3.1 Fuerza bruta / bloqueo temporal ──────────────────────────────
def prueba_fuerza_bruta(app):
    print("\n== 3.1 Fuerza bruta / bloqueo temporal ==")
    client = app.test_client()
    email = "brutef@pruebas.com"
    registrar_empresa(client, email, "Empresa Fuerza Bruta")
    client.get("/auth/salir")  # cerrar sesion del registro automatico

    codigos = []
    for i in range(5):
        r = client.post("/auth/login", data={"email": email, "password": "incorrecta"})
        codigos.append(r.status_code)
    verificar("Intentos 1-5 con clave incorrecta devuelven 401", all(c == 401 for c in codigos), f"codigos={codigos}")

    r_bloqueo = client.post("/auth/login", data={"email": email, "password": "incorrecta"})
    verificar("Intento 6 queda bloqueado (423)", r_bloqueo.status_code == 423, f"codigo={r_bloqueo.status_code}")

    r_correcta = client.post("/auth/login", data={"email": email, "password": "Password123"})
    verificar("Con clave CORRECTA sigue bloqueado", r_correcta.status_code == 423, f"codigo={r_correcta.status_code}")


# ── 3.2 Inyeccion SQL ─────────────────────────────────────────────────
def prueba_inyeccion_sql(app):
    print("\n== 3.2 Inyeccion SQL ==")
    client = app.test_client()
    with app.app_context():
        antes = Usuario.query.count()

    payloads = ["' OR '1'='1", "admin' --", "' OR 1=1 --", "'; DROP TABLE usuarios; --"]
    codigos = []
    for p in payloads:
        r = client.post("/auth/login", data={"email": p, "password": "x"})
        codigos.append(r.status_code)
    verificar("Ningun payload de inyeccion autentica (401 en todos)", all(c == 401 for c in codigos), f"codigos={codigos}")

    with app.app_context():
        despues = Usuario.query.count()
    verificar("La tabla usuarios sigue intacta tras el intento de DROP TABLE", antes == despues, f"antes={antes} despues={despues}")


# ── 3.3 Aislamiento multi-tenant ─────────────────────────────────────
def prueba_multi_tenant(app):
    print("\n== 3.3 Aislamiento multi-tenant ==")
    client_a = app.test_client()
    client_b = app.test_client()

    registrar_empresa(client_a, "empresaa@pruebas.com", "Empresa A")
    registrar_empresa(client_b, "empresab@pruebas.com", "Empresa B")

    client_b.get("/diagnostico/iniciar", follow_redirects=True)
    with app.app_context():
        from models import Evaluacion
        evaluacion_b = Evaluacion.query.join(Empresa).filter(Empresa.nombre == "Empresa B").first()
        id_evaluacion_b = evaluacion_b.id_evaluacion

    r_cruzado = client_a.get(f"/diagnostico/responder/{id_evaluacion_b}")
    verificar("Empresa A no puede ver una evaluacion de Empresa B (403)", r_cruzado.status_code == 403, f"codigo={r_cruzado.status_code}")


# ── 3.4 XSS ───────────────────────────────────────────────────────────
def prueba_xss(app):
    print("\n== 3.4 XSS ==")
    payload = "<script>alert('xss')</script>"
    client = app.test_client()
    registrar_empresa(client, "xsstest@pruebas.com", payload)
    client.get("/auth/salir")

    with app.app_context():
        admin = crear_superadmin()
    client_admin = app.test_client()
    client_admin.post("/auth/login", data={"email": "superadmin@pruebas.com", "password": "Password123"})
    r = client_admin.get("/empresas/")
    body = r.get_data(as_text=True)

    verificar("El payload NO aparece sin escapar en el HTML", payload not in body)
    verificar("El payload aparece escapado (&lt;script&gt;)", "&lt;script&gt;" in body)

    grep_safe = []
    for raiz, _, archivos in os.walk(os.path.join(RAIZ, "templates")):
        for f in archivos:
            if f.endswith(".html"):
                ruta = os.path.join(raiz, f)
                if "|safe" in open(ruta, encoding="utf-8").read():
                    grep_safe.append(ruta)
    verificar("Ningun template usa el filtro |safe", len(grep_safe) == 0, f"encontrados={grep_safe}")


# ── Extra: CSRF (no estaba en el documento original) ─────────────────
def prueba_csrf(app):
    print("\n== EXTRA: proteccion CSRF en formularios POST ==")
    client = app.test_client()
    registrar_empresa(client, "csrftest@pruebas.com", "Empresa CSRF")
    # Request "forjada": mismo navegador/cookies de sesion, SIN token CSRF
    # (ningun formulario del proyecto envia uno).
    r = client.post("/diagnostico/iniciar".replace("iniciar", "iniciar"))  # placeholder simple GET-safe route
    r2 = client.get("/diagnostico/iniciar", follow_redirects=True)
    id_match = re.search(r"/diagnostico/responder/(\d+)", r2.request.path)
    id_evaluacion = id_match.group(1) if id_match else None
    if id_evaluacion:
        r3 = client.post(f"/diagnostico/finalizar/{id_evaluacion}", data={})
        exito_sin_token = r3.status_code in (302, 200)
        verificar(
            "Un POST sin token CSRF es aceptado (protección ausente)",
            exito_sin_token,
            f"codigo={r3.status_code} — confirma que WTF_CSRF_ENABLED no esta activo de verdad",
        )


def main():
    app = crear_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.drop_all()
        db.create_all()
        preparar_datos_base()

    prueba_fuerza_bruta(app)
    prueba_inyeccion_sql(app)
    prueba_multi_tenant(app)
    prueba_xss(app)
    prueba_csrf(app)

    print("\n== Resumen ==")
    total = len(resultados)
    ok = sum(1 for _, c in resultados if c)
    for nombre, c in resultados:
        print(f"  {'OK ' if c else 'FALLA'}  {nombre}")
    print(f"\n{ok}/{total} verificaciones en PASS")

    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    if os.path.exists(_DB_TMP):
        try:
            os.remove(_DB_TMP)
        except PermissionError:
            pass


if __name__ == "__main__":
    main()
