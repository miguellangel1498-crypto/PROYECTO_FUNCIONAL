from datetime import datetime

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models import (
    Dimension, Empresa, EmpresaRecomendacion, Evaluacion, MovimientoInventario,
    Pregunta, Recomendacion, ResultadoDimension, ResultadoEvaluacion, Respuesta,
)

NIVELES = [
    ("INICIAL", 0, 20),
    ("BASICO", 21, 40),
    ("INTERMEDIO", 41, 60),
    ("AVANZADO", 61, 80),
    ("OPTIMIZADO", 81, 100),
]


def _determinar_nivel(puntaje):
    for nombre, minimo, maximo in NIVELES:
        if minimo <= puntaje <= maximo:
            return nombre
    return "INICIAL"


def _calcular_indicadores_calculados(empresa_id):
    from models import Producto
    productos = Producto.query.filter_by(id_empresa=empresa_id).all()
    if not productos:
        return {}

    resultados = {}
    for prod in productos:
        movimientos = MovimientoInventario.query.filter_by(id_producto=prod.id_producto).order_by(MovimientoInventario.fecha_movimiento.asc()).all()
        if not movimientos:
            continue
        total_movimientos = len(movimientos)
        ajustes = sum(1 for m in movimientos if m.tipo_movimiento == "AJUSTE")
        pct_ajustes = (ajustes / total_movimientos * 100) if total_movimientos > 0 else 0
        if prod.stock_minimo > 0:
            control_stock = min(100, (prod.stock_actual / prod.stock_minimo) * 100)
        else:
            control_stock = 100

        resultados["frecuencia_actualizacion"] = min(100, total_movimientos * 5)
        resultados["pct_ajustes"] = max(0, 100 - pct_ajustes)
        resultados["control_stock"] = min(100, control_stock)

    return resultados


def calcular_resultados_evaluacion(id_evaluacion):
    evaluacion = db.session.get(Evaluacion, id_evaluacion)
    if not evaluacion:
        return

    respuestas = Respuesta.query.filter_by(id_evaluacion=id_evaluacion).all()
    respuestas_map = {}
    for r in respuestas:
        respuestas_map[r.id_pregunta] = r

    indicadores_calculados = _calcular_indicadores_calculados(evaluacion.id_empresa)

    dimensiones = Dimension.query.filter_by(estado="ACTIVA").all()
    dim_scores = {}

    for dim in dimensiones:
        preguntas = Pregunta.query.filter_by(id_dimension=dim.id_dimension, estado="ACTIVA").all()
        suma_ponderada = 0
        peso_total = 0

        for preg in preguntas:
            peso_preg = float(preg.peso or 1)
            valor = 0
            tiene_respuesta = False

            if preg.tipo_medicion == "CALCULADO":
                clave_calc = None
                if "frecuencia" in preg.pregunta.lower():
                    clave_calc = "frecuencia_actualizacion"
                elif "ajuste" in preg.pregunta.lower():
                    clave_calc = "pct_ajustes"
                elif "stock" in preg.pregunta.lower() or "inventario" in preg.pregunta.lower():
                    clave_calc = "control_stock"

                if clave_calc and clave_calc in indicadores_calculados:
                    valor = indicadores_calculados[clave_calc]
                    tiene_respuesta = True
                    db.session.add(Respuesta(
                        id_evaluacion=id_evaluacion,
                        id_pregunta=preg.id_pregunta,
                        respuesta_numerica=valor,
                    ))
            elif preg.id_pregunta in respuestas_map:
                resp = respuestas_map[preg.id_pregunta]
                if resp.id_opcion:
                    from models import OpcionRespuesta
                    opcion = db.session.get(OpcionRespuesta, resp.id_opcion)
                    if opcion:
                        valor = float(opcion.valor)
                        tiene_respuesta = True
                elif resp.respuesta_numerica is not None:
                    valor = float(resp.respuesta_numerica)
                    tiene_respuesta = True

            if tiene_respuesta:
                suma_ponderada += valor * peso_preg
                peso_total += peso_preg

        puntaje = round(suma_ponderada / peso_total, 2) if peso_total > 0 else 0
        dim_scores[dim] = puntaje

    db.session.commit()

    suma_global = 0
    peso_global = 0
    for dim, puntaje in dim_scores.items():
        peso_dim = float(dim.peso or 1)
        suma_global += puntaje * peso_dim
        peso_global += peso_dim

    indice_general = round(suma_global / peso_global, 2) if peso_global > 0 else 0
    nivel_general = _determinar_nivel(indice_general)

    resultado = ResultadoEvaluacion(
        id_evaluacion=id_evaluacion,
        indice_madurez=indice_general,
        nivel=nivel_general,
    )
    db.session.add(resultado)
    db.session.flush()

    for dim, puntaje in dim_scores.items():
        nivel_dim = _determinar_nivel(puntaje)
        db.session.add(ResultadoDimension(
            id_resultado=resultado.id_resultado,
            id_dimension=dim.id_dimension,
            puntaje=puntaje,
            nivel=nivel_dim,
        ))

    for dim, puntaje in dim_scores.items():
        recs = Recomendacion.query.filter(
            Recomendacion.id_dimension == dim.id_dimension,
            Recomendacion.estado == "ACTIVA",
            Recomendacion.nivel_minimo <= puntaje,
            Recomendacion.nivel_maximo >= puntaje,
        ).all()
        for rec in recs:
            existente = EmpresaRecomendacion.query.filter_by(
                id_empresa=evaluacion.id_empresa,
                id_recomendacion=rec.id_recomendacion,
                id_evaluacion=id_evaluacion,
            ).first()
            if not existente:
                db.session.add(EmpresaRecomendacion(
                    id_empresa=evaluacion.id_empresa,
                    id_recomendacion=rec.id_recomendacion,
                    id_evaluacion=id_evaluacion,
                    estado="PENDIENTE",
                ))

    db.session.commit()


def _obtener_segmento(puntaje):
    for nombre, minimo, maximo in NIVELES:
        if minimo <= puntaje <= maximo:
            return nombre
    return "INICIAL"


def _calcular_promedio_sector(sector_id, tamano_id):
    empresas_sector = Empresa.query.filter(
        Empresa.id_sector == sector_id,
        Empresa.id_tamano == tamano_id,
        Empresa.estado == "ACTIVA",
    ).all()

    if not empresas_sector:
        return None

    empresa_ids = [e.id_empresa for e in empresas_sector]
    from models import Evaluacion as EvalModel

    ultimas_evals = (
        db.session.query(
            EvalModel.id_empresa,
            func.max(EvalModel.id_evaluacion).label("ultima_eval"),
        )
        .filter(EvalModel.id_empresa.in_(empresa_ids), EvalModel.estado == "FINALIZADA")
        .group_by(EvalModel.id_empresa)
        .subquery()
    )

    promedio = (
        db.session.query(func.avg(ResultadoEvaluacion.indice_madurez))
        .join(ultimas_evals, ResultadoEvaluacion.id_evaluacion == ultimas_evals.c.ultima_eval)
        .scalar()
    )
    return round(float(promedio), 2) if promedio else None


def _ranking_empresas():
    from models import Evaluacion as EvalModel

    ultimas_evals = (
        db.session.query(
            EvalModel.id_empresa,
            func.max(EvalModel.id_evaluacion).label("ultima_eval"),
        )
        .filter(EvalModel.estado == "FINALIZADA")
        .group_by(EvalModel.id_empresa)
        .subquery()
    )

    ranking = (
        db.session.query(
            Empresa.id_empresa,
            Empresa.nombre,
            ResultadoEvaluacion.indice_madurez,
            ResultadoEvaluacion.nivel,
        )
        .join(ultimas_evals, Empresa.id_empresa == ultimas_evals.c.id_empresa)
        .join(ResultadoEvaluacion, ResultadoEvaluacion.id_evaluacion == ultimas_evals.c.ultima_eval)
        .filter(Empresa.estado == "ACTIVA")
        .order_by(ResultadoEvaluacion.indice_madurez.desc())
        .all()
    )
    return ranking


analisis_bp = Blueprint("analisis", __name__, url_prefix="/analisis")


@analisis_bp.route("/")
@login_required
def principal():
    from models.permisos import rol_tiene_permiso

    es_superadmin = current_user.tiene_rol("SUPERADMIN")
    es_empresa = current_user.tiene_rol("EMPRESA")

    if not es_superadmin and not es_empresa:
        abort(403)

    if es_empresa:
        if not current_user.tiene_empresa or not current_user.acceso_empresa_activa:
            abort(403)

    empresa = current_user.empresa

    if es_superadmin:
        ranking = _ranking_empresas()
        empresas_con_indice = []
        for emp_id, nombre, indice, nivel in ranking:
            empresas_con_indice.append({
                "id": emp_id,
                "nombre": nombre,
                "indice": round(float(indice), 2),
                "nivel": nivel,
            })

        todas_empresas = Empresa.query.filter_by(estado="ACTIVA").all()
        return render_template(
            "analisis.html",
            es_admin=True,
            empresa=None,
            empresas_con_indice=empresas_con_indice,
            todas_empresas=todas_empresas,
        )
    else:
        if empresa is None:
            abort(403)

        ultima_eval = (
            Evaluacion.query
            .filter_by(id_empresa=empresa.id_empresa, estado="FINALIZADA")
            .order_by(Evaluacion.fecha_finalizacion.desc())
            .first()
        )

        resultado = None
        dimensiones_resultado = []
        if ultima_eval:
            resultado = ResultadoEvaluacion.query.filter_by(id_evaluacion=ultima_eval.id_evaluacion).first()
            if resultado:
                dimensiones_resultado = ResultadoDimension.query.filter_by(id_resultado=resultado.id_resultado).all()

        promedio_sector = _calcular_promedio_sector(empresa.id_sector, empresa.id_tamano)

        recomendaciones = []
        if ultima_eval:
            recomendaciones = EmpresaRecomendacion.query.filter_by(id_evaluacion=ultima_eval.id_evaluacion).all()

        return render_template(
            "analisis.html",
            es_admin=False,
            empresa=empresa,
            resultado=resultado,
            dimensiones_resultado=dimensiones_resultado,
            promedio_sector=promedio_sector,
            recomendaciones=recomendaciones,
        )
