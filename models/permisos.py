MATRIZ_PERMISOS = {
    "SUPERADMIN": {
        "descripcion": "Superadministrador de la plataforma",
        "permisos": [
            "ver_panel_global",
            "gestionar_empresas",
            "activar_inactivar_empresas",
            "ver_auditoria_global",
            "gestionar_sectores",
            "gestionar_tamano_empresas",
            "administrar_diagnostico",
            "administrar_dimensiones",
            "administrar_preguntas",
            "administrar_recomendaciones",
            "ver_ranking_empresas",
            "ver_resultados_todas_empresas",
            "gestionar_segmentos",
        ],
    },
    "EMPRESA": {
        "descripcion": "Administrador de empresa",
        "permisos": [
            "ver_panel_empresa",
            "responder_diagnostico",
            "ver_resultados_propios",
            "gestionar_recomendaciones_asignadas",
            "ver_historial_evaluaciones",
            "ver_indicadores_propios",
        ],
    },
}


def rol_tiene_permiso(nombre_rol, permiso):
    rol_data = MATRIZ_PERMISOS.get(nombre_rol.upper(), {})
    permisos = rol_data.get("permisos", [])
    return permiso in permisos


def obtener_permisos_rol(nombre_rol):
    rol_data = MATRIZ_PERMISOS.get(nombre_rol.upper(), {})
    return rol_data.get("permisos", [])


def usuario_tiene_permiso(usuario, permiso):
    for rol in usuario.roles_list:
        if rol_tiene_permiso(rol.nombre, permiso):
            return True
    return False
