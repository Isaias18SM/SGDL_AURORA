"""
app/models/asistencia.py
"""
from app import db
from datetime import datetime


class Asistencia(db.Model):
    __tablename__ = 'asistencia'

    Id_Asistencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Id_Usuario = db.Column(db.Integer, db.ForeignKey('usuario.Id_Usuario'))
    HoraRegistro = db.Column(db.DateTime, default=datetime.utcnow)
    Fecha_Requerida = db.Column(db.Date)
    Estado = db.Column(db.String(20))  # Presente / Falla / Retardo / Excusa / Sin registrar

    usuario = db.relationship('Usuario', back_populates='asistencias')
    justificaciones = db.relationship('AsistenciaJustificacionUsuario', back_populates='asistencia')

    def __repr__(self):
        return f'<Asistencia {self.Id_Asistencia} - {self.Estado}>'
