"""
app/models/asignacion_resultado_aprendizaje.py

Tabla de asociación muchos-a-muchos entre Asignacion y ResultadoDeAprendizaje.
"""
from app import db

asignacion_resultado_aprendizaje = db.Table(
    'asignacion_resultado_aprendizaje',
    db.Column('ID_ASIGNACION', db.Integer, db.ForeignKey('asignacion.ID_ASIGNACION'), primary_key=True),
    db.Column('Id_Resultado_Aprendizaje', db.Integer, db.ForeignKey('resultado_de_aprendizaje.Id_Resultado_Aprendizaje'), primary_key=True)
)
