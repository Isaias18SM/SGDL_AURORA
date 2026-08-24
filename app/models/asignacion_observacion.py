"""
app/models/asignacion_observacion.py

Tabla de asociación muchos-a-muchos entre Asignacion y Observaciones.
"""
from app import db

asignacion_observacion = db.Table(
    'asignacion_observacion',
    db.Column('ID_ASIGNACION', db.Integer, db.ForeignKey('asignacion.ID_ASIGNACION'), primary_key=True),
    db.Column('Id_Observaciones', db.Integer, db.ForeignKey('observaciones.Id_Observaciones'), primary_key=True)
)
