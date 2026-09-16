from functools import wraps

from flask import abort
from flask_login import current_user

from models.permisos import rol_tiene_permiso


def _sin_acceso():
    abort(403)


def superadmin_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.tiene_rol("SUPERADMIN"):
            _sin_acceso()
        return func(*args, **kwargs)
    return envoltura


def admin_empresa_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if not current_user.tiene_rol("EMPRESA"):
            _sin_acceso()
        if not current_user.tiene_empresa or not current_user.acceso_empresa_activa:
            _sin_acceso()
        return func(*args, **kwargs)
    return envoltura


def miembro_empresa_requerido(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            _sin_acceso()
        if not current_user.tiene_empresa:
            _sin_acceso()
        if not current_user.acceso_empresa_activa:
            _sin_acceso()
        return func(*args, **kwargs)
    return envoltura


def requiere_permiso(permiso):
    def decorador(func):
        @wraps(func)
        def envoltura(*args, **kwargs):
            if not current_user.is_authenticated:
                _sin_acceso()
            tiene = False
            for r in current_user.roles_list:
                if rol_tiene_permiso(r.nombre, permiso):
                    tiene = True
                    break
            if not tiene:
                _sin_acceso()
            return func(*args, **kwargs)
        return envoltura
    return decorador
