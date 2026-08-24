"""
app/models/usuario_ficha_asignacion.py

Relación ternaria: qué usuario tiene qué asignación (horario) dentro de
qué ficha. Tiene columnas propias (las 3 llaves), así que es un modelo
completo y no una simple db.Table de asociación.
"""
from app import db


class UsuarioFichaAsignacion(db.Model):
    __tablename__ = 'usuario_ficha_asignacion'

    Id_Usuario = db.Column(db.Integer, db.ForeignKey('usuario.Id_Usuario'), primary_key=True)
    ID_FICHA = db.Column(db.Integer, db.ForeignKey('ficha.ID_FICHA'), primary_key=True)
    ID_ASIGNACION = db.Column(db.Integer, db.ForeignKey('asignacion.ID_ASIGNACION'), primary_key=True)

    usuario = db.relationship('Usuario')
    ficha = db.relationship('Ficha')
    asignacion = db.relationship('Asignacion')

    def __repr__(self):
        return f'<UsuarioFichaAsignacion Usuario:{self.Id_Usuario} Ficha:{self.ID_FICHA} Asignacion:{self.ID_ASIGNACION}>'
