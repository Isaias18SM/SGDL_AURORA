"""
app/models/trimestre.py
"""
from app import db


class Trimestre(db.Model):
    __tablename__ = 'trimestre'

    Id_Trimestre = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Numero_Trimestre = db.Column(db.Integer, nullable=False)
    Fecha_Inicio = db.Column(db.Date)
    Fecha_Fin = db.Column(db.Date)
    Tiempo_vigencia = db.Column(db.Integer)
    Id_Sede = db.Column(db.Integer, db.ForeignKey('sede.Id_Sede'))

    sede = db.relationship('Sede', back_populates='trimestres')
    asignaciones = db.relationship('Asignacion', back_populates='trimestre')

    def __repr__(self):
        return f'<Trimestre {self.Numero_Trimestre}>'
