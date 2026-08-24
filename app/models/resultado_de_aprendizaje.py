"""
app/models/resultado_de_aprendizaje.py
"""
from app import db
from app.models.asignacion_resultado_aprendizaje import asignacion_resultado_aprendizaje


class ResultadoDeAprendizaje(db.Model):
    __tablename__ = 'resultado_de_aprendizaje'

    Id_Resultado_Aprendizaje = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Estado = db.Column(db.String(20))
    Calificacion = db.Column(db.Numeric(5, 2))
    Aprobado_Desaprobado = db.Column(db.String(20))
    Id_Competencia = db.Column(db.Integer, db.ForeignKey('competencia.Id_Competencia'))

    competencia = db.relationship('Competencia', back_populates='resultados_aprendizaje')
    asignaciones = db.relationship(
        'Asignacion', secondary=asignacion_resultado_aprendizaje, back_populates='resultados_aprendizaje'
    )

    def __repr__(self):
        return f'<ResultadoDeAprendizaje {self.Id_Resultado_Aprendizaje}>'
