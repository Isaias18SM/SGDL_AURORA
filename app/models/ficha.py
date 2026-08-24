"""
app/models/ficha.py
"""
from app import db


class Ficha(db.Model):
    __tablename__ = 'ficha'

    ID_FICHA = db.Column(db.Integer, primary_key=True, autoincrement=True)
    No_FICHA = db.Column(db.String(30), nullable=False)
    Jornada = db.Column(db.String(50))
    TipoDeFicha = db.Column(db.String(50))
    Vigencia = db.Column(db.String(50))
    FechaInicio = db.Column(db.Date)
    FechaFinal = db.Column(db.Date)
    Id_Programa = db.Column(db.Integer, db.ForeignKey('programa.Id_Programa'))

    programa = db.relationship('Programa', back_populates='fichas')

    def __repr__(self):
        return f'<Ficha {self.No_FICHA}>'
