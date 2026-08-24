"""
app/models/asistencia_justificacion_usuario.py

Relación ternaria: qué asistencia fue justificada, con qué justificación
y por cuál usuario. Tiene columnas propias (las 3 llaves), así que es un
modelo completo y no una simple db.Table de asociación.
"""
from app import db


class AsistenciaJustificacionUsuario(db.Model):
    __tablename__ = 'asistencia_justificacion_usuario'

    Id_Asistencia = db.Column(db.Integer, db.ForeignKey('asistencia.Id_Asistencia'), primary_key=True)
    Id_Justificacion = db.Column(db.Integer, db.ForeignKey('justificacion.Id_Justificacion'), primary_key=True)
    Id_Usuario = db.Column(db.Integer, db.ForeignKey('usuario.Id_Usuario'), primary_key=True)

    asistencia = db.relationship('Asistencia', back_populates='justificaciones')
    justificacion = db.relationship('Justificacion', back_populates='asistencias')
    usuario = db.relationship('Usuario')

    def __repr__(self):
        return f'<AsistenciaJustificacionUsuario Asistencia:{self.Id_Asistencia} Justificacion:{self.Id_Justificacion}>'
