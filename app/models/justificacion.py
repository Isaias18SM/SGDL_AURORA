"""
app/models/justificacion.py
"""
from app import db


class Justificacion(db.Model):
    __tablename__ = 'justificacion'

    Id_Justificacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Motivo = db.Column(db.Text)
    URL_Archivo = db.Column(db.String(500))
    Valido_SN = db.Column(db.String(1), default='N')
    Verificado_SN = db.Column(db.String(1), default='N')

    asistencias = db.relationship('AsistenciaJustificacionUsuario', back_populates='justificacion')

    def __repr__(self):
        return f'<Justificacion {self.Id_Justificacion}>'
