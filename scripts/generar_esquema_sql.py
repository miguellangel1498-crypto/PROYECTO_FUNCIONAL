"""Genera el CREATE TABLE de todas las tablas a partir de los modelos
SQLAlchemy, sin necesitar conexion a un servidor MySQL vivo.

Uso:
    python scripts/generar_esquema_sql.py > export/schema_growthhorizon.sql
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql

from extensions import db
import models  # noqa: F401  (registra todos los modelos en db.metadata)


def main():
    dialect = mysql.dialect()
    print("-- Esquema de la base de datos growthhorizon")
    print("-- Generado automaticamente desde los modelos SQLAlchemy")
    print("SET NAMES utf8mb4;")
    print("SET FOREIGN_KEY_CHECKS=0;\n")

    for table in db.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect)).strip()
        print(ddl + ";\n")

    print("SET FOREIGN_KEY_CHECKS=1;")


if __name__ == "__main__":
    main()
