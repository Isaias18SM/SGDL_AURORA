"""
app/models/usuario_observacion.py

Tabla de asociación muchos-a-muchos entre Usuario y Observaciones.
"""
from app import db

usuario_observacion = db.Table(
    'usuario_observacion',
    db.Column('Id_Usuario', db.Integer, db.ForeignKey('usuario.Id_Usuario'), primary_key=True),
    db.Column('Id_Observaciones', db.Integer, db.ForeignKey('observaciones.Id_Observaciones'), primary_key=True)
)
