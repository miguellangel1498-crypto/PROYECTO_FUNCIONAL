from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.tiene_rol("SUPERADMIN"):
        return redirect(url_for("superadmin.panel"))
    if current_user.tiene_rol("EMPRESA"):
        return redirect(url_for("cliente.panel"))
    from flask import abort
    abort(403)
