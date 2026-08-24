"""
app/models/observaciones.py
"""
from app import db
from datetime import datetime
from app.models.usuario_observacion import usuario_observacion
from app.models.asignacion_observacion import asignacion_observacion


class Observaciones(db.Model):
    __tablename__ = 'observaciones'

    Id_Observaciones = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Fecha = db.Column(db.DateTime, default=datetime.utcnow)
    Contenido = db.Column(db.Text)

    usuarios = db.relationship(
        'Usuario', secondary=usuario_observacion, back_populates='observaciones'
    )
    asignaciones = db.relationship(
        'Asignacion', secondary=asignacion_observacion, back_populates='observaciones'
    )

    def __repr__(self):
        return f'<Observaciones {self.Id_Observaciones}>'
