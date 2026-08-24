"""
app/models/competencia.py
"""
from app import db
from app.models.programa_competencia import programa_competencia


class Competencia(db.Model):
    __tablename__ = 'competencia'

    Id_Competencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(200), nullable=False)
    Tipo = db.Column(db.String(50))

    programas = db.relationship(
        'Programa', secondary=programa_competencia, back_populates='competencias'
    )
    resultados_aprendizaje = db.relationship('ResultadoDeAprendizaje', back_populates='competencia')

    def __repr__(self):
        return f'<Competencia {self.Nombre}>'
