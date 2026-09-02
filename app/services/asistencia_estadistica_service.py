def calcular_estadistica(asistencias):
    """
    Calcula estadísticas reales a partir de registros de asistencia.
    """

    total = len(asistencias)

    if total == 0:
        return {
            "total": 0,
            "presentes": 0,
            "fallas": 0,
            "retardos": 0,
            "excusas": 0,
            "porcentaje": 0
        }

    presentes = 0
    fallas = 0
    retardos = 0
    excusas = 0

    for asistencia in asistencias:

        estado = str(
            asistencia.get("Estado", "")
        ).strip().lower()

        if estado == "presente":
            presentes += 1

        elif estado == "falla":
            fallas += 1

        elif estado == "retardo":
            retardos += 1

        elif estado == "excusa":
            excusas += 1

    porcentaje = round(
        (presentes / total) * 100,
        2
    )

    return {
        "total": total,
        "presentes": presentes,
        "fallas": fallas,
        "retardos": retardos,
        "excusas": excusas,
        "porcentaje": porcentaje
    }


def generar_progresion(asistencias):

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
            "falla",
            "retardo",
            "excusa"
        ):
            continue

        total += 1

        if estado == "presente":
            presentes += 1

        porcentaje = round(
            (presentes / total) * 100,
            2
        )

        resultado.append({
            "fecha": str(
                registro["Fecha_Requerida"]
            ),
            "porcentaje": porcentaje
        })

    return resultado