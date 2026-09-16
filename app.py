from flask import Flask, render_template

from config import Config
from extensions import bcrypt, db, login_manager
from services.auditoria import AutoAuditoria


def crear_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from models import Auditoria, Empresa, Sector, Usuario

    @login_manager.user_loader
    def cargar_usuario(usuario_id):
        try:
            return db.session.get(Usuario, int(usuario_id))
        except Exception:
            return None

    @app.template_filter("moneda")
    def formato_moneda(valor):
        if valor is None:
            return "---"
        try:
            v = float(valor)
        except (TypeError, ValueError):
            return valor
        texto = f"{v:,.2f}"
        texto = texto.replace(",", "@").replace(".", ",").replace("@", ".")
        return f"$ {texto} COP"

    @app.context_processor
    def contexto_global():
        try:
            return {
                "cantidad_sectores": db.session.query(Sector).count(),
                "cantidad_empresas": db.session.query(Empresa).count(),
            }
        except Exception:
            return {"cantidad_sectores": 0, "cantidad_empresas": 0}

    @app.errorhandler(403)
    def sin_permiso(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def no_encontrado(e):
        return render_template("404.html"), 404

    from routes.analisis import analisis_bp
    from routes.auth import auth_bp
    from routes.cliente import cliente_bp
    from routes.diagnostico import diagnostico_bp
    from routes.diagnostico_admin import diagnostico_admin_bp
    from routes.empresas import empresas_bp
    from routes.main import main_bp
    from routes.recomendaciones import recomendaciones_bp
    from routes.seguridad import seguridad_bp
    from routes.superadmin import superadmin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(empresas_bp)
    app.register_blueprint(seguridad_bp)
    app.register_blueprint(cliente_bp)
    app.register_blueprint(analisis_bp)
    app.register_blueprint(superadmin_bp)
    app.register_blueprint(diagnostico_bp)
    app.register_blueprint(diagnostico_admin_bp)
    app.register_blueprint(recomendaciones_bp)

    @app.after_request
    def _no_cache_protected(response):
        from flask_login import current_user

        if current_user.is_authenticated:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    AutoAuditoria.configurar()

    with app.app_context():
        try:
            db.create_all()
            print("Base de datos inicializada correctamente.")
        except Exception as e:
            print(f"Advertencia: No se pudo conectar a la BD: {e}")
            print("La app iniciara sin BD. Ejecuta 'flask seed' cuando la BD este disponible.")

        @app.cli.command("init-db")
        def init_db():
            db.create_all()
            print("Base de datos inicializada correctamente.")

    @app.cli.command("seed")
    def seed():
        from datetime import datetime

        from models import (
            Dimension, Empresa, EmpresaRecomendacion, MovimientoInventario, OpcionRespuesta,
            Producto, Pregunta, Recomendacion, ResultadoDimension, ResultadoEvaluacion,
            Respuesta, Evaluacion, Rol, Sector, TamanoEmpresa, Usuario,
        )

        db.create_all()

        if Rol.query.count() == 0:
            db.session.add_all([
                Rol(nombre="SUPERADMIN", descripcion="Superadministrador de la plataforma"),
                Rol(nombre="EMPRESA", descripcion="Administrador de empresa"),
            ])
            db.session.commit()
            print("Roles creados.")

        if TamanoEmpresa.query.count() == 0:
            db.session.add_all([
                TamanoEmpresa(nombre="MICRO", descripcion="Microempresa", numero_empleados_min=1, numero_empleados_max=10),
                TamanoEmpresa(nombre="PEQUENA", descripcion="Pequena empresa", numero_empleados_min=11, numero_empleados_max=50),
                TamanoEmpresa(nombre="MEDIANA", descripcion="Empresa mediana", numero_empleados_min=51, numero_empleados_max=200),
                TamanoEmpresa(nombre="GRANDE", descripcion="Gran empresa", numero_empleados_min=201, numero_empleados_max=None),
            ])
            db.session.commit()
            print("Tamano de empresas creado.")

        if Sector.query.count() == 0:
            db.session.add_all([
                Sector(nombre="Tecnologia", descripcion="Software, hardware y servicios digitales"),
                Sector(nombre="Manufactura", descripcion="Produccion industrial y transformacion"),
                Sector(nombre="Comercio", descripcion="Venta de bienes y servicios"),
                Sector(nombre="Agroindustria", descripcion="Produccion agricola y procesamiento"),
                Sector(nombre="Financiero", descripcion="Banca, seguros y fintech"),
            ])
            db.session.commit()
            print("Sectores creados.")

        if Usuario.query.count() == 0:
            admin = Usuario(nombre="Super", apellido="Admin", correo="admin@growthhorizon.com")
            admin.set_password("Admin123!")
            db.session.add(admin)
            db.session.flush()

            rol_superadmin = Rol.query.filter_by(nombre="SUPERADMIN").first()
            db.session.execute(
                db.text("INSERT INTO usuario_rol (id_usuario, id_rol) VALUES (:u, :r)"),
                {"u": admin.id_usuario, "r": rol_superadmin.id_rol},
            )
            db.session.commit()
            print("Superadministrador creado: admin@growthhorizon.com / Admin123!")

        if Dimension.query.count() == 0:
            dimensiones_datos = [
                ("Financiera", "Salud financiera, control de ingresos y gastos, planificacion presupuestaria", 1.0),
                ("Operacion", "Procesos internos, eficiencia operativa, control de inventario", 1.0),
                ("Clientes/Ventas", "Gestion de clientes, estrategia comercial, canales de venta", 1.0),
                ("Digitalizacion", "Uso de herramientas digitales, presencia online, transformacion digital", 1.2),
                ("Datos", "Gestion de datos, toma de decisiones basada en datos", 1.0),
                ("Seguridad", "Proteccion de datos, ciberseguridad, respaldos", 0.8),
                ("Automatizacion", "Automatizacion de procesos, uso de tecnologia para reducir tareas manuales", 1.0),
                ("Analitica", "Analisis de datos, metricas, reportes, inteligencia de negocio", 1.0),
            ]
            dims_creadas = {}
            for nombre, desc, peso in dimensiones_datos:
                d = Dimension(nombre=nombre, descripcion=desc, peso=peso)
                db.session.add(d)
                db.session.flush()
                dims_creadas[nombre] = d

            preguntas_datos = [
                ("Financiera", "Llevas un registro organizado de tus ingresos y gastos mensuales?", "OPCION_UNICA", 1.0, 1, True, [
                    ("No tengo registro", 10), ("Algo desorganizado", 30), ("Organizado basico", 60), ("Completo y detallado", 90),
                ]),
                ("Financiera", "Cual fue tu ingreso aproximado el ultimo mes (en pesos)?", "NUMERICA", 1.0, 2, True, []),
                ("Financiera", "Cuentas con un presupuesto mensual definido?", "SI_NO", 1.0, 3, True, [
                    ("No", 10), ("Si", 90),
                ]),
                ("Financiera", "Indicador de control de inventario calculado", "NUMERICA", 0.5, 4, False, []),
                ("Operacion", "Llevas un control organizado de tu inventario?", "OPCION_UNICA", 1.0, 1, True, [
                    ("No tengo control", 10), ("Algo basico", 40), ("Organizado", 70), ("Sistema completo", 95),
                ]),
                ("Operacion", "Tus procesos principales estan documentados o estandarizados?", "OPCION_UNICA", 1.0, 2, True, [
                    ("Nada documentado", 10), ("Algunos procesos", 40), ("Mayormente documentados", 70), ("Todo documentado", 95),
                ]),
                ("Operacion", "Que porcentaje de tus ingresos proviene de canales digitales?", "OPCION_UNICA", 1.0, 3, True, [
                    ("0%", 10), ("1-25%", 30), ("26-50%", 60), ("51-75%", 80), ("Mas del 75%", 95),
                ]),
                ("Operacion", "Frecuencia de actualizacion de inventario calculada", "NUMERICA", 0.5, 4, False, []),
                ("Clientes/Ventas", "Tienes una base de datos de tus clientes?", "OPCION_UNICA", 1.0, 1, True, [
                    ("No tengo", 10), ("En hoja de calculo", 40), ("Software basico", 70), ("CRM completo", 95),
                ]),
                ("Clientes/Ventas", "Utilizas alguna herramienta para gestionar clientes (CRM)?", "OPCION_UNICA", 1.0, 2, True, [
                    ("No", 10), ("Herramientas gratuitas", 50), ("CRM pagado basico", 75), ("CRM avanzado", 95),
                ]),
                ("Clientes/Ventas", "Mides la satisfaccion de tus clientes?", "OPCION_UNICA", 1.0, 3, True, [
                    ("Nunca", 10), ("A veces informal", 30), ("Periodicamente", 70), ("Sistema continuo", 95),
                ]),
                ("Digitalizacion", "Tu negocio tiene presencia online (pagina web, redes sociales)?", "OPCION_UNICA", 1.2, 1, True, [
                    ("No tiene nada", 10), ("Solo redes sociales", 40), ("Pagina web basica", 70), ("Presencia completa", 95),
                ]),
                ("Digitalizacion", "Utilizas herramientas digitales para gestionar tu negocio?", "OPCION_UNICA", 1.2, 2, True, [
                    ("Ninguna", 10), ("Algunas basicas", 40), ("Varias herramientas", 70), ("Ecosistema digital completo", 95),
                ]),
                ("Digitalizacion", "Vendes o promocionas tus productos/servicios por internet?", "OPCION_UNICA", 1.0, 3, True, [
                    ("No", 10), ("Redes sociales", 40), ("Tienda online basica", 70), ("E-commerce avanzado", 95),
                ]),
                ("Datos", "Generas reportes periodicos de tu negocio?", "OPCION_UNICA", 1.0, 1, True, [
                    ("No", 10), ("Manuales y esporadicos", 40), ("Periodicos automatizados", 75), ("Dashboard en tiempo real", 95),
                ]),
                ("Datos", "Tomas decisiones de negocio basadas en datos o estadisticas?", "OPCION_UNICA", 1.0, 2, True, [
                    ("No, por intuicion", 10), ("A veces miro numeros", 40), ("Regularmente", 70), ("Siempre basado en datos", 95),
                ]),
                ("Seguridad", "Cuentas con respaldos (backups) de tu informacion?", "OPCION_UNICA", 1.0, 1, True, [
                    ("No", 10), ("Manuales ocasionales", 40), ("Automaticos periodicos", 80), ("Sistema robusto", 95),
                ]),
                ("Seguridad", "Tus empleados conocen buenas practicas de seguridad digital?", "OPCION_UNICA", 1.0, 2, True, [
                    ("No", 10), ("Algo basico", 40), ("Capacitados", 75), ("Expertos", 95),
                ]),
                ("Automatizacion", "Utilizas software para tareas repetitivas (contabilidad, inventario)?", "OPCION_UNICA", 1.0, 1, True, [
                    ("No, todo manual", 10), ("Algo de software", 40), ("Software especializado", 75), ("Sistema integrado", 95),
                ]),
                ("Automatizacion", "Algunos de tus procesos se ejecutan automaticamente?", "OPCION_UNICA", 1.0, 2, True, [
                    ("No, nada automatico", 10), ("Algunos procesos", 40), ("Varios procesos", 70), ("Casi todo automatico", 95),
                ]),
                ("Analitica", "Revisas metricas o indicadores de tu negocio regularmente?", "OPCION_UNICA", 1.0, 1, True, [
                    ("Nunca", 10), ("A veces", 40), ("Semanalmente", 75), ("Diariamente", 95),
                ]),
                ("Analitica", "Utilizas herramientas de analisis (Excel avanzado, BI, dashboards)?", "OPCION_UNICA", 1.0, 2, True, [
                    ("Ninguna", 10), ("Excel basico", 40), ("Excel avanzado/BI basico", 70), ("Herramientas BI avanzadas", 95),
                ]),
                ("Analitica", "Indicador de tendencia de mejora calculado", "NUMERICA", 0.5, 3, False, []),
            ]

            for dim_nombre, texto, tipo, peso, orden, obligatoria, opciones in preguntas_datos:
                dim = dims_creadas.get(dim_nombre)
                if dim:
                    preg = Pregunta(
                        id_dimension=dim.id_dimension,
                        pregunta=texto,
                        tipo_respuesta=tipo,
                        tipo_medicion="CALCULADO" if tipo == "NUMERICA" and not obligatoria else "AUTOREPORTADO",
                        peso=peso,
                        orden=orden,
                        obligatoria=obligatoria,
                    )
                    db.session.add(preg)
                    db.session.flush()

                    for i, (txt, val) in enumerate(opciones):
                        db.session.add(OpcionRespuesta(
                            id_pregunta=preg.id_pregunta,
                            texto=txt,
                            valor=val,
                            orden=i + 1,
                        ))

            db.session.commit()
            print("Dimensiones, preguntas y opciones creadas.")

        if Recomendacion.query.count() == 0:
            dims_recs = Dimension.query.all()
            dim_ids = {d.nombre: d.id_dimension for d in dims_recs}

            recomendaciones_datos = [
                ("Financiera", 0, 20, "Implementa un sistema basico de registro de ingresos y gastos.", "ALTA", "Registro basico de finanzas"),
                ("Financiera", 21, 40, "Organiza tus finanzas con hojas de calculo y define un presupuesto.", "ALTA", "Organizacion financiera"),
                ("Financiera", 41, 60, "Define un presupuesto mensual y compara con resultados reales.", "MEDIA", "Presupuesto mensual"),
                ("Financiera", 61, 80, "Implementa software contable y analisis financiero regular.", "MEDIA", "Software contable"),
                ("Financiera", 81, 100, "Considera software contable avanzado y proyecciones trimestrales.", "BAJA", "Finanzas avanzadas"),
                ("Operacion", 0, 20, "Documenta tus procesos principales y crea un inventario basico.", "ALTA", "Documentacion basica"),
                ("Operacion", 21, 40, "Organiza tus procesos y empieza a controlar tu inventario.", "ALTA", "Control de procesos"),
                ("Operacion", 41, 60, "Implementa herramientas de gestion de inventario y estandariza flujos.", "MEDIA", "Estandarizacion"),
                ("Operacion", 61, 80, "Automatiza procesos repetitivos e integra sistemas.", "MEDIA", "Automatizacion de procesos"),
                ("Operacion", 81, 100, "Optimiza todos los procesos para eficiencia optima.", "BAJA", "Eficiencia optima"),
                ("Clientes/Ventas", 0, 20, "Crea una lista de clientes con datos de contacto.", "ALTA", "Base de clientes basica"),
                ("Clientes/Ventas", 21, 40, "Organiza tu base de clientes y registra interacciones.", "ALTA", "Gestion de clientes"),
                ("Clientes/Ventas", 41, 60, "Implementa un CRM basico y mide satisfaccion periodicamente.", "MEDIA", "CRM basico"),
                ("Clientes/Ventas", 61, 80, "Usa segmentacion avanzada y automatiza comunicaciones.", "MEDIA", "Segmentacion avanzada"),
                ("Clientes/Ventas", 81, 100, "Implementa marketing automatizado y fidelizacion.", "BAJA", "Marketing automatizado"),
                ("Digitalizacion", 0, 20, "Crea perfiles en redes sociales y considera una pagina web.", "ALTA", "Presencia digital basica"),
                ("Digitalizacion", 21, 40, "Desarrolla tu presencia online con redes sociales activas.", "ALTA", "Redes sociales activas"),
                ("Digitalizacion", 41, 60, "Integra herramientas digitales para gestion interna y presencia online.", "MEDIA", "Herramientas digitales"),
                ("Digitalizacion", 61, 80, "Implementa un ecosistema digital integrado.", "MEDIA", "Ecosistema digital"),
                ("Digitalizacion", 81, 100, "Optimiza tu ecosistema digital con omnicanalidad.", "BAJA", "Omnicanalidad"),
                ("Datos", 0, 20, "Empieza a registrar datos clave del negocio en hojas de calculo.", "ALTA", "Registro de datos"),
                ("Datos", 21, 40, "Organiza tus datos y crea reportes basicos.", "ALTA", "Datos organizados"),
                ("Datos", 41, 60, "Crea dashboards basicos y reportes mensuales con metricas.", "MEDIA", "Dashboards basicos"),
                ("Datos", 61, 80, "Implementa herramientas de analisis avanzado.", "MEDIA", "Analisis avanzado"),
                ("Datos", 81, 100, "Implementa analitica predictiva y toma de decisiones basada en datos.", "BAJA", "Analitica predictiva"),
                ("Seguridad", 0, 20, "Configura respaldos automaticos y crea contrasenas seguras.", "ALTA", "Respaldos basicos"),
                ("Seguridad", 21, 40, "Capacita a tu equipo en seguridad digital basica.", "ALTA", "Capacitacion basica"),
                ("Seguridad", 41, 60, "Implementa politicas de seguridad y respaldos periodicos.", "MEDIA", "Politicas de seguridad"),
                ("Seguridad", 61, 80, "Audita regularmente tu seguridad y cumple normativas.", "MEDIA", "Auditoria de seguridad"),
                ("Seguridad", 81, 100, "Implementa ciberseguridad avanzada y cumplimiento total.", "BAJA", "Ciberseguridad avanzada"),
                ("Automatizacion", 0, 20, "Identifica tareas repetitivas que puedan automatizarse.", "ALTA", "Identificacion de tareas"),
                ("Automatizacion", 21, 40, "Empieza a automatizar tareas simples con herramientas basicas.", "ALTA", "Automatizacion basica"),
                ("Automatizacion", 41, 60, "Implementa software especializado para automatizar procesos clave.", "MEDIA", "Software especializado"),
                ("Automatizacion", 61, 80, "Integra sistemas y crea flujos de trabajo automatizados.", "MEDIA", "Flujos automatizados"),
                ("Automatizacion", 81, 100, "Logra una automatizacion completa de procesos criticos.", "BAJA", "Automatizacion completa"),
                ("Analitica", 0, 20, "Define 3-5 metricas clave y revisaselas semanalmente.", "ALTA", "Metricas basicas"),
                ("Analitica", 21, 40, "Empieza a analizar tus metricas regularmente.", "ALTA", "Analisis regular"),
                ("Analitica", 41, 60, "Implementa herramientas de visualizacion y reportes automatizados.", "MEDIA", "Visualizacion de datos"),
                ("Analitica", 61, 80, "Usa herramientas BI para analisis avanzado.", "MEDIA", "Herramientas BI"),
                ("Analitica", 81, 100, "Implementa inteligencia de negocio y analitica predictiva.", "BAJA", "Inteligencia de negocio"),
            ]

            for dim_nombre, r_min, r_max, desc, prioridad, titulo in recomendaciones_datos:
                dim_id = dim_ids.get(dim_nombre)
                if dim_id:
                    db.session.add(Recomendacion(
                        id_dimension=dim_id,
                        titulo=titulo,
                        descripcion=desc,
                        prioridad=prioridad,
                        nivel_minimo=r_min,
                        nivel_maximo=r_max,
                    ))

            db.session.commit()
            print("Recomendaciones creadas.")

        if Empresa.query.filter_by(nit="20555500001").first() is None:
            comercio = Sector.query.filter_by(nombre="Comercio").first()
            tecnologia = Sector.query.filter_by(nombre="Tecnologia").first()
            tamano_micro = TamanoEmpresa.query.filter_by(nombre="MICRO").first()
            tamano_mediana = TamanoEmpresa.query.filter_by(nombre="MEDIANA").first()

            empresa_micro = Empresa(
                nombre="Cafe Horizonte S.A.C.",
                nit="20555500001",
                id_sector=comercio.id_sector,
                id_tamano=tamano_micro.id_tamano,
                numero_empleados=5,
                ciudad="Bogota",
                departamento="Cundinamarca",
                telefono="3001234567",
                correo="info@cafehorizonte.com",
                estado="ACTIVA",
            )
            empresa_mediana = Empresa(
                nombre="Innovatech Solutions",
                nit="20100011112",
                id_sector=tecnologia.id_sector,
                id_tamano=tamano_mediana.id_tamano,
                numero_empleados=120,
                ciudad="Medellin",
                departamento="Antioquia",
                telefono="3009876543",
                correo="info@innovatech.com",
                estado="ACTIVA",
            )
            db.session.add_all([empresa_micro, empresa_mediana])
            db.session.flush()

            if Usuario.query.filter_by(correo="admin@cafehorizonte.com").first() is None:
                admin_micro = Usuario(
                    nombre="Maria",
                    apellido="Lopez",
                    correo="admin@cafehorizonte.com",
                    id_empresa=empresa_micro.id_empresa,
                )
                admin_micro.set_password("Cliente123!")
                db.session.add(admin_micro)
                db.session.flush()

                rol_empresa = Rol.query.filter_by(nombre="EMPRESA").first()
                db.session.execute(
                    db.text("INSERT INTO usuario_rol (id_usuario, id_rol) VALUES (:u, :r)"),
                    {"u": admin_micro.id_usuario, "r": rol_empresa.id_rol},
                )

            if Usuario.query.filter_by(correo="admin@innovatech.com").first() is None:
                admin_med = Usuario(
                    nombre="Carlos",
                    apellido="Ruiz",
                    correo="admin@innovatech.com",
                    id_empresa=empresa_mediana.id_empresa,
                )
                admin_med.set_password("Cliente123!")
                db.session.add(admin_med)
                db.session.flush()

                db.session.execute(
                    db.text("INSERT INTO usuario_rol (id_usuario, id_rol) VALUES (:u, :r)"),
                    {"u": admin_med.id_usuario, "r": rol_empresa.id_rol},
                )

            db.session.commit()
            print("Empresas demo creadas.")

            prod1 = Producto(id_empresa=empresa_micro.id_empresa, nombre="Cafe en grano", categoria="Materia prima", stock_actual=50, stock_minimo=10)
            prod2 = Producto(id_empresa=empresa_micro.id_empresa, nombre="Taza de cafe", categoria="Insumo", stock_actual=100, stock_minimo=20)
            prod3 = Producto(id_empresa=empresa_mediana.id_empresa, nombre="Licencia software", categoria="Servicio", stock_actual=30, stock_minimo=5)
            db.session.add_all([prod1, prod2, prod3])
            db.session.flush()

            db.session.add(MovimientoInventario(id_producto=prod1.id_producto, tipo_movimiento="ENTRADA", cantidad=100, stock_resultante=100))
            db.session.add(MovimientoInventario(id_producto=prod1.id_producto, tipo_movimiento="SALIDA", cantidad=50, stock_resultante=50))
            db.session.add(MovimientoInventario(id_producto=prod2.id_producto, tipo_movimiento="ENTRADA", cantidad=150, stock_resultante=150))
            db.session.add(MovimientoInventario(id_producto=prod2.id_producto, tipo_movimiento="AJUSTE", cantidad=10, stock_resultante=100))
            db.session.add(MovimientoInventario(id_producto=prod3.id_producto, tipo_movimiento="ENTRADA", cantidad=30, stock_resultante=30))
            db.session.commit()
            print("Productos y movimientos demo creados.")

            preguntas_autoreportadas = Pregunta.query.filter_by(tipo_medicion="AUTOREPORTADO", estado="ACTIVA").all()

            respuestas_micro = {
                "Llevas un registro organizado de tus ingresos y gastos mensuales?": 30,
                "Cual fue tu ingreso aproximado el ultimo mes (en pesos)?": 5000000,
                "Cuentas con un presupuesto mensual definido?": 10,
                "Llevas un control organizado de tu inventario?": 40,
                "Tus procesos principales estan documentados o estandarizados?": 30,
                "Que porcentaje de tus ingresos proviene de canales digitales?": 30,
                "Tienes una base de datos de tus clientes?": 40,
                "Utilizas alguna herramienta para gestionar clientes (CRM)?": 10,
                "Mides la satisfaccion de tus clientes?": 30,
                "Tu negocio tiene presencia online (pagina web, redes sociales)?": 40,
                "Utilizas herramientas digitales para gestionar tu negocio?": 30,
                "Vendes o promocionas tus productos/servicios por internet?": 30,
                "Generas reportes periodicos de tu negocio?": 30,
                "Tomas decisiones de negocio basadas en datos o estadisticas?": 20,
                "Cuentas con respaldos (backups) de tu informacion?": 40,
                "Tus empleados conocen buenas practicas de seguridad digital?": 30,
                "Utilizas software para tareas repetitivas (contabilidad, inventario)?": 30,
                "Algunos de tus procesos se ejecutan automaticamente?": 20,
                "Revisas metricas o indicadores de tu negocio regularmente?": 30,
                "Utilizas herramientas de analisis (Excel avanzado, BI, dashboards)?": 20,
            }

            respuestas_mediana = {
                "Llevas un registro organizado de tus ingresos y gastos mensuales?": 80,
                "Cual fue tu ingreso aproximado el ultimo mes (en pesos)?": 80000000,
                "Cuentas con un presupuesto mensual definido?": 90,
                "Llevas un control organizado de tu inventario?": 70,
                "Tus procesos principales estan documentados o estandarizados?": 65,
                "Que porcentaje de tus ingresos proviene de canales digitales?": 80,
                "Tienes una base de datos de tus clientes?": 75,
                "Utilizas alguna herramienta para gestionar clientes (CRM)?": 70,
                "Mides la satisfaccion de tus clientes?": 60,
                "Tu negocio tiene presencia online (pagina web, redes sociales)?": 90,
                "Utilizas herramientas digitales para gestionar tu negocio?": 80,
                "Vendes o promocionas tus productos/servicios por internet?": 75,
                "Generas reportes periodicos de tu negocio?": 70,
                "Tomas decisiones de negocio basadas en datos o estadisticas?": 65,
                "Cuentas con respaldos (backups) de tu informacion?": 85,
                "Tus empleados conocen buenas practicas de seguridad digital?": 60,
                "Utilizas software para tareas repetitivas (contabilidad, inventario)?": 70,
                "Algunos de tus procesos se ejecutan automaticamente?": 55,
                "Revisas metricas o indicadores de tu negocio regularmente?": 75,
                "Utilizas herramientas de analisis (Excel avanzado, BI, dashboards)?": 65,
            }

            for preg in preguntas_autoreportadas:
                texto = preg.pregunta
                opciones = OpcionRespuesta.query.filter_by(id_pregunta=preg.id_pregunta).order_by(OpcionRespuesta.orden).all()

                if texto in respuestas_micro:
                    valor = respuestas_micro[texto]
                    opcion_match = None
                    if preg.tipo_respuesta == "OPCION_UNICA":
                        for opt in opciones:
                            if abs(float(opt.valor) - valor) < 15:
                                opcion_match = opt
                                break
                        if not opcion_match and opciones:
                            min_dist = min(abs(float(opt.valor) - valor) for opt in opciones)
                            for opt in opciones:
                                if abs(float(opt.valor) - valor) == min_dist:
                                    opcion_match = opt
                                    break

                    evaluacion_micro = Evaluacion.query.filter_by(id_empresa=empresa_micro.id_empresa, estado="FINALIZADA").first()
                    if not evaluacion_micro:
                        evaluacion_micro = Evaluacion(
                            id_empresa=empresa_micro.id_empresa,
                            id_usuario=admin_micro.id_usuario,
                            estado="FINALIZADA",
                            fecha_finalizacion=datetime.utcnow(),
                        )
                        db.session.add(evaluacion_micro)
                        db.session.flush()

                    if preg.tipo_respuesta in ("OPCION_UNICA", "SI_NO") and opcion_match:
                        db.session.add(Respuesta(
                            id_evaluacion=evaluacion_micro.id_evaluacion,
                            id_pregunta=preg.id_pregunta,
                            id_opcion=opcion_match.id_opcion,
                        ))
                    elif preg.tipo_respuesta == "NUMERICA":
                        db.session.add(Respuesta(
                            id_evaluacion=evaluacion_micro.id_evaluacion,
                            id_pregunta=preg.id_pregunta,
                            respuesta_numerica=valor,
                        ))

                if texto in respuestas_mediana:
                    valor = respuestas_mediana[texto]
                    opcion_match = None
                    if preg.tipo_respuesta == "OPCION_UNICA":
                        for opt in opciones:
                            if abs(float(opt.valor) - valor) < 15:
                                opcion_match = opt
                                break
                        if not opcion_match and opciones:
                            min_dist = min(abs(float(opt.valor) - valor) for opt in opciones)
                            for opt in opciones:
                                if abs(float(opt.valor) - valor) == min_dist:
                                    opcion_match = opt
                                    break

                    evaluacion_med = Evaluacion.query.filter_by(id_empresa=empresa_mediana.id_empresa, estado="FINALIZADA").first()
                    if not evaluacion_med:
                        evaluacion_med = Evaluacion(
                            id_empresa=empresa_mediana.id_empresa,
                            id_usuario=admin_med.id_usuario,
                            estado="FINALIZADA",
                            fecha_finalizacion=datetime.utcnow(),
                        )
                        db.session.add(evaluacion_med)
                        db.session.flush()

                    if preg.tipo_respuesta in ("OPCION_UNICA", "SI_NO") and opcion_match:
                        db.session.add(Respuesta(
                            id_evaluacion=evaluacion_med.id_evaluacion,
                            id_pregunta=preg.id_pregunta,
                            id_opcion=opcion_match.id_opcion,
                        ))
                    elif preg.tipo_respuesta == "NUMERICA":
                        db.session.add(Respuesta(
                            id_evaluacion=evaluacion_med.id_evaluacion,
                            id_pregunta=preg.id_pregunta,
                            respuesta_numerica=valor,
                        ))

            db.session.commit()

            for eval_obj in [evaluacion_micro, evaluacion_med]:
                if eval_obj:
                    from routes.analisis import calcular_resultados_evaluacion
                    calcular_resultados_evaluacion(eval_obj.id_evaluacion)

            print("Evaluaciones demo con resultados creadas.")

        print("Datos semilla listos.")

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
