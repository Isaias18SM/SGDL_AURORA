const filtroPeriodo =
    document.getElementById("filtroPeriodo");

const filtroAnio =
    document.getElementById("filtroAnio");

const filtroMes =
    document.getElementById("filtroMes");

const filtroTrimestre =
    document.getElementById("filtroTrimestre");

const filtroFicha =
    document.getElementById("filtroFicha");

const contenedorMes =
    document.getElementById("contenedorMes");

const contenedorTrimestre =
    document.getElementById("contenedorTrimestre");

let graficaAprendices = null;
let graficaProgresion = null;


/* ==========================
   CARGAR FICHAS
========================== */

async function cargarFichas() {

    try {

        const respuesta =
            await fetch("/api/fichas");

        const data =
            await respuesta.json();

        if (data.status !== "success") {
            return;
        }

        filtroFicha.innerHTML =
            '<option value="">Todas mis fichas</option>';

        data.fichas.forEach(ficha => {

            const opcion =
                document.createElement("option");

            opcion.value =
                ficha.ID_FICHA;

            opcion.textContent =
                `${ficha.codigo} - ${ficha.programa}`;

            filtroFicha.appendChild(opcion);

        });

    } catch (error) {

        console.error(
            "Error cargando fichas:",
            error
        );

    }
}


/* ==========================
   CARGAR ESTADÍSTICAS
========================== */

async function cargarEstadisticas() {

    const periodo =
        filtroPeriodo.value;

    const anio =
        filtroAnio.value;

    let url =
        `/api/instructor/estadisticas?` +
        `periodo=${periodo}` +
        `&anio=${anio}`;


    if (periodo === "mes") {

        url +=
            `&mes=${filtroMes.value}`;

    }


    if (periodo === "trimestre") {

        url +=
            `&trimestre=${filtroTrimestre.value}`;

    }


    if (filtroFicha.value) {

        url +=
            `&ficha=${filtroFicha.value}`;

    }


    try {

        const respuesta =
            await fetch(url);

        const data =
            await respuesta.json();


        if (data.status !== "success") {

            console.error(data.message);

            return;

        }


        actualizarResumen(
            data.resumen
        );


        actualizarTabla(
            data.aprendices
        );


        generarGraficaAprendices(
            data.aprendices
        );


        generarGraficaProgresion(
            data.progresion
        );

    } catch (error) {

        console.error(
            "Error obteniendo estadísticas:",
            error
        );

    }

}


/* ==========================
   RESUMEN
========================== */

function actualizarResumen(resumen) {

    document.getElementById(
        "porcentajeGeneral"
    ).textContent =
        `${resumen.porcentaje}%`;

    document.getElementById(
        "totalPresentes"
    ).textContent =
        resumen.presentes;

    document.getElementById(
        "totalFallas"
    ).textContent =
        resumen.fallas;

    document.getElementById(
        "totalRegistros"
    ).textContent =
        resumen.total;

}


/* ==========================
   TABLA
========================== */

function actualizarTabla(aprendices) {

    const tabla =
        document.getElementById(
            "tablaAprendices"
        );

    tabla.innerHTML = "";


    if (!aprendices.length) {

        tabla.innerHTML = `
            <tr>
                <td colspan="7"
                    style="text-align:center;">
                    No existen registros para el
                    período seleccionado.
                </td>
            </tr>
        `;

        return;

    }


    aprendices.forEach(aprendiz => {

        const fila =
            document.createElement("tr");

        fila.innerHTML = `

            <td>
                ${aprendiz.nombre}
            </td>

            <td>
                ${aprendiz.ficha}
            </td>

            <td>
                ${aprendiz.total}
            </td>

            <td>
                ${aprendiz.presentes}
            </td>

            <td>
                ${aprendiz.fallas}
            </td>

            <td>
                ${aprendiz.retardos}
            </td>

            <td>
                <strong>
                    ${aprendiz.porcentaje}%
                </strong>
            </td>

        `;

        tabla.appendChild(fila);

    });

}


/* ==========================
   GRAFICA POR APRENDIZ
========================== */

function generarGraficaAprendices(aprendices) {

    const canvas =
        document.getElementById(
            "graficaAprendices"
        );

    if (graficaAprendices) {

        graficaAprendices.destroy();

    }


    graficaAprendices =
        new Chart(
            canvas,
            {
                type: "bar",

                data: {

                    labels:
                        aprendices.map(
                            a => a.nombre
                        ),

                    datasets: [

                        {
                            label:
                                "Porcentaje de asistencia",

                            data:
                                aprendices.map(
                                    a => a.porcentaje
                                ),

                            borderWidth: 1

                        }

                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    scales: {

                        y: {

                            min: 0,

                            max: 100,

                            ticks: {

                                callback:
                                    value =>
                                        `${value}%`

                            }

                        }

                    }

                }

            }
        );

}


/* ==========================
   EVOLUCION
========================== */

function generarGraficaProgresion(progresion) {

    const canvas =
        document.getElementById(
            "graficaProgresion"
        );

    if (graficaProgresion) {

        graficaProgresion.destroy();

    }


    graficaProgresion =
        new Chart(
            canvas,
            {
                type: "line",

                data: {

                    labels:
                        progresion.map(
                            p => p.fecha
                        ),

                    datasets: [

                        {

                            label:
                                "Asistencia general",

                            data:
                                progresion.map(
                                    p => p.porcentaje
                                ),

                            borderWidth: 3,

                            tension: 0.3,

                            fill: false

                        }

                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    scales: {

                        y: {

                            min: 0,

                            max: 100,

                            ticks: {

                                callback:
                                    value =>
                                        `${value}%`

                            }

                        }

                    }

                }

            }
        );

}


/* ==========================
   FILTROS
========================== */

filtroPeriodo.addEventListener(
    "change",
    function () {

        if (
            this.value === "mes"
        ) {

            contenedorMes.style.display =
                "block";

            contenedorTrimestre.style.display =
                "none";

        }

        else if (
            this.value === "trimestre"
        ) {

            contenedorMes.style.display =
                "none";

            contenedorTrimestre.style.display =
                "block";

        }

        else {

            contenedorMes.style.display =
                "none";

            contenedorTrimestre.style.display =
                "none";

        }

        cargarEstadisticas();

    }
);


filtroAnio.addEventListener(
    "change",
    cargarEstadisticas
);


filtroMes.addEventListener(
    "change",
    cargarEstadisticas
);


filtroTrimestre.addEventListener(
    "change",
    cargarEstadisticas
);


filtroFicha.addEventListener(
    "change",
    cargarEstadisticas
);


/* ==========================
   INICIO
========================== */

cargarFichas();

cargarEstadisticas();