from datetime import date, timedelta
import calendar


def calcular_estadistica(asistencias):
    """
    Calcula porcentaje de asistencia a partir
    de los registros obtenidos de la BD.
    """

    total = len(asistencias)

    if total == 0:
        return {
            "total": 0,
            "presentes": 0,
            "fallas": 0,
            "porcentaje": 0
        }

    presentes = sum(
        1 for asistencia in asistencias
        if str(asistencia.get("Estado", "")).strip().lower()
        in ("presente", "present")
    )

    fallas = sum(
        1 for asistencia in asistencias
        if str(asistencia.get("Estado", "")).strip().lower()
        in ("falla", "falta", "ausente")
    )

    porcentaje = round((presentes / total) * 100, 2)

    return {
        "total": total,
        "presentes": presentes,
        "fallas": fallas,
        "porcentaje": porcentaje
    }


def generar_progresion(asistencias):
    """
    Genera la evolución acumulada de la asistencia.

    Ejemplo:

    Día 1 -> 100%
    Día 2 -> 100%
    Día 3 -> 66.67%
    Día 4 -> 75%
    """

    registros = sorted(
        asistencias,
        key=lambda x: x["Fecha_Requerida"]
    )

    presentes = 0
    total = 0
    resultado = []

    for registro in registros:

        estado = str(
            registro.get("Estado", "")
        ).strip().lower()

        if estado not in (
            "presente",
            "present",
            "falla",
            "falta",
            "ausente"
        ):
            continue

        total += 1

        if estado in ("presente", "present"):
            presentes += 1

        porcentaje = round(
            (presentes / total) * 100,
            2
        )

        resultado.append({
            "fecha": str(registro["Fecha_Requerida"]),
            "porcentaje": porcentaje
        })

    return resultado

def generar_datos_grafica(
    asistencias,
    periodo
):

    if periodo == "mes":

        return {
            "labels": [
                str(a["Fecha_Requerida"])
                for a in asistencias
            ],

            "data": [
                a["porcentaje"]
                for a in asistencias
            ]
        }

    return {
        "labels": [],
        "data": []
    }