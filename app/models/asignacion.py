"""
app/models/asignacion.py
"""
from app import db
from app.models.asignacion_resultado_aprendizaje import asignacion_resultado_aprendizaje
from app.models.asignacion_observacion import asignacion_observacion


class Asignacion(db.Model):
    __tablename__ = 'asignacion'

    ID_ASIGNACION = db.Column(db.Integer, primary_key=True, autoincrement=True)
    HORA_INICIO = db.Column(db.Time, nullable=False)
    HORA_FINALIZACION = db.Column(db.Time, nullable=False)
    Minutos_De_Tolerancia = db.Column(db.Integer, default=0)
    Id_Usuario = db.Column(db.Integer, db.ForeignKey('usuario.Id_Usuario'))
    Id_Trimestre = db.Column(db.Integer, db.ForeignKey('trimestre.Id_Trimestre'))

    usuario = db.relationship('Usuario', back_populates='asignaciones')
    trimestre = db.relationship('Trimestre', back_populates='asignaciones')

    resultados_aprendizaje = db.relationship(
        'ResultadoDeAprendizaje', secondary=asignacion_resultado_aprendizaje, back_populates='asignaciones'
    )
    observaciones = db.relationship(
        'Observaciones', secondary=asignacion_observacion, back_populates='asignaciones'
    )

    def __repr__(self):
        return f'<Asignacion {self.ID_ASIGNACION}>'
