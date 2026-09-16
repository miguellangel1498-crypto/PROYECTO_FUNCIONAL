# PLAN_DE_CAMBIOS - Growth Horizon v2.0

## Resumen
Migracion completa de plataforma de ventas/inventario a herramienta de **diagnostico de madurez empresarial**.  
Base de datos: SQLite -> **MySQL via PyMySQL**.  
Modelos SQLAlchemy mapeados **1:1 con esquema SQL definitivo**.

---

## 1. Modelos (18 tablas)

| Modelo | Tabla | PK | Descripcion |
|---|---|---|---|
| `Rol` | `roles` | `id_rol` | Roles del sistema (SUPERADMIN, EMPRESA) |
| `usuario_rol` | `usuario_rol` | `id_usuario` + `id_rol` | Relacion N:M usuarios-roles |
| `Sector` | `sectores` | `id_sector` | Catalogo de sectores economicos |
| `TamanoEmpresa` | `tamano_empresa` | `id_tamano` | Categorias de tamano (MICRO a GRANDE) |
| `Empresa` | `empresas` | `id_empresa` | Datos de la empresa (FK sector, tamano) |
| `Usuario` | `usuarios` | `id_usuario` | Usuarios con FK empresa nullable, roles N:M |
| `Dimension` | `dimensiones` | `id_dimension` | Dimensiones del cuestionario |
| `Pregunta` | `preguntas` | `id_pregunta` | Preguntas por dimension (AUTOREPORTADO/CALCULADO) |
| `OpcionRespuesta` | `opciones_respuesta` | `id_opcion` | Opciones para preguntas de seleccion |
| `Evaluacion` | `evaluaciones` | `id_evaluacion` | Instancia de evaluacion (EN_PROCESO/FINALIZADA) |
| `Respuesta` | `respuestas` | `id_respuesta` | Respuestas individuales por pregunta |
| `ResultadoEvaluacion` | `resultados_evaluacion` | `id_resultado` | Indice general y nivel de madurez |
| `ResultadoDimension` | `resultados_dimension` | `id_resultado_dimension` | Puntaje por dimension |
| `Recomendacion` | `recomendaciones` | `id_recomendacion` | Recomendaciones por dimension y rango |
| `EmpresaRecomendacion` | `empresa_recomendacion` | `id_empresa_recomendacion` | Recomendaciones asignadas a empresa |
| `Producto` | `productos` | `id_producto` | Fuente de datos para indicadores calculados |
| `MovimientoInventario` | `movimientos_inventario` | `id_movimiento` | Movimientos de inventario |
| `Auditoria` | `auditoria` | `id_auditoria` | Registro de acciones del sistema |

### Propiedades clave de Usuario
- `tiene_rol(nombre)` - Verifica rol via tabla N:M
- `es_superadmin` - Property que llama `tiene_rol("SUPERADMIN")`
- `tiene_empresa` - Property: `empresa is not None`
- `acceso_empresa_activa` - Property: empresa None o esta_activa

---

## 2. Permisos (models/permisos.py)

### SUPERADMIN (13 permisos)
`ver_panel_global`, `gestionar_empresas`, `activar_inactivar_empresas`, `ver_auditoria_global`, `gestionar_sectores`, `gestionar_tamano_empresas`, `administrar_diagnostico`, `administrar_dimensiones`, `administrar_preguntas`, `administrar_recomendaciones`, `ver_ranking_empresas`, `ver_resultados_todas_empresas`, `gestionar_segmentos`

### EMPRESA (6 permisos)
`ver_panel_empresa`, `responder_diagnostico`, `ver_resultados_propios`, `gestionar_recomendaciones_asignadas`, `ver_historial_evaluaciones`, `ver_indicadores_propios`

---

## 3. Decoradores (routes/decoradores.py)

| Decorador | Uso |
|---|---|
| `@superadmin_requerido` | Solo SUPERADMIN |
| `@admin_empresa_requerido` | EMPRESA con empresa activa |
| `@miembro_empresa_requerido` | Cualquier usuario con empresa activa |
| `@requiere_permiso("permiso")` | Verifica en MATRIZ_PERMISOS |

---

## 4. Rutas por Blueprint

### auth (`/auth`)
- `GET/POST /login` - Login con validacion dual (usuario + empresa activos)
- `GET/POST /registro` - Registro crea Empresa ACTIVA + rol EMPRESA automatico
- `GET /salir` - Logout

### main (`/`)
- `GET /` - Landing page
- `GET /dashboard` - Redirige segun rol

### diagnostico (`/diagnostico`)
- `GET /iniciar` - Crea Evaluacion EN_PROCESO
- `GET/POST /responder/<id>` - Cuestionario agrupado por dimensiones
- `POST /finalizar/<id>` - Valida obligatorias, calcula resultados
- `GET /resultados/<id>` - Indice, nivel, dimensiones, recomendaciones
- `GET /historial` - Lista evaluaciones finalizadas

### analisis (`/analisis`)
- `GET /` - Vista admin (ranking) o empresa (indice + comparativo sectorial)

### recomendaciones (`/recomendaciones`)
- `GET /` - Lista con filtro por estado
- `POST /<id>/cambiar_estado` - PENDIENTE/EN_PROCESO/COMPLETADA/DESCARTADA

### diagnostico_admin (`/superadmin/diagnostico`)
- CRUD dimensiones, preguntas (con opciones), recomendaciones

### superadmin (`/superadmin`)
- Panel, empresas (activate/inactivate), sectores, tamanos, ranking

### empresas (`/empresas`)
- CRUD completo de empresas (solo SUPERADMIN)

### seguridad (`/seguridad`)
- `/auditoria` - Registro de auditoria (solo SUPERADMIN)

---

## 5. Niveles de Madurez

| Nivel | Rango | Color |
|---|---|---|
| INICIAL | 0-20 | Rojo |
| BASICO | 21-40 | Amber |
| INTERMEDIO | 41-60 | Azul |
| AVANZADO | 61-80 | Cyan |
| OPTIMIZADO | 81-100 | Verde |

---

## 6. Seed (flask seed)

Datos iniciales: roles, tamanos (MICRO/PEQUENA/MEDIANA/GRANDE), 5 sectores, superadmin, 2 empresas demo con usuarios, 8 dimensiones, 22 preguntas, 40 recomendaciones, evaluaciones demo con resultados calculados, productos e inventario.

---

## 7. Archivos eliminados (residuos del sistema viejo)

- `models/base.py`, `models/roles.py`, `models/configuracion.py`
- `models/segmento.py`, `models/indicador.py`, `models/indice_madurez.py`
- `models/respuesta_diagnostico.py`, `models/venta.py`, `models/horario.py`
- `routes/empleado.py`, `routes/sectores.py`
- `templates/diagnostico/responder.html`
- `templates/cliente/seguridad.html`
- `templates/superadmin/empresas_pendientes.html`
- `templates/superadmin/permisos.html`
- `templates/superadmin/diagnostico/indicador_form.html`
