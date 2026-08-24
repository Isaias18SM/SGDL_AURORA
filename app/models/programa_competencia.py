"""
app/models/programa_competencia.py

Tabla de asociación muchos-a-muchos entre Programa y Competencia.
No tiene columnas propias, solo las dos llaves foráneas.
"""
from app import db

programa_competencia = db.Table(
    'programa_competencia',
    db.Column('Id_Programa', db.Integer, db.ForeignKey('programa.Id_Programa'), primary_key=True),
    db.Column('Id_Competencia', db.Integer, db.ForeignKey('competencia.Id_Competencia'), primary_key=True)
)
