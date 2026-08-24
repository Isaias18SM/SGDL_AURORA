"""
app/models/programa.py
"""
from app import db
from app.models.programa_competencia import programa_competencia


class Programa(db.Model):
    __tablename__ = 'programa'

    Id_Programa = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(200), nullable=False)
    Tipo = db.Column(db.String(50))
    Duracion = db.Column(db.Integer)
    Version = db.Column(db.String(30))

    fichas = db.relationship('Ficha', back_populates='programa')
    competencias = db.relationship(
        'Competencia', secondary=programa_competencia, back_populates='programas'
    )

    def __repr__(self):
        return f'<Programa {self.Nombre}>'
