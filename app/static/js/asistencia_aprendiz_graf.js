const filtroPeriodo =
    document.getElementById('filtroPeriodo');

const filtroAnio =
    document.getElementById('filtroAnio');

const filtroMes =
    document.getElementById('filtroMes');

const filtroTrimestre =
    document.getElementById('filtroTrimestre');


function cargarEstadisticas() {

    const periodo =
        filtroPeriodo.value;

    const anio =
        filtroAnio.value;

    let url =
        `/api/aprendiz/estadisticas?periodo=${periodo}&anio=${anio}`;


    if (periodo === 'mes') {

        url +=
            `&mes=${filtroMes.value}`;

    }


    if (periodo === 'trimestre') {

        url +=
            `&trimestre=${filtroTrimestre.value}`;

    }


    fetch(url)

        .then(response => response.json())

        .then(data => {

            if (data.status !== 'success') {

                console.error(
                    data.message
                );

                return;
            }


            const estadistica =
                data.estadistica;


            document.getElementById(
                'porcentajeAsistencia'
            ).textContent =
                `${estadistica.porcentaje}%`;


            document.getElementById(
                'totalPresentes'
            ).textContent =
                estadistica.presentes;


            document.getElementById(
                'totalFallas'
            ).textContent =
                estadistica.fallas;


            document.getElementById(
                'totalRegistros'
            ).textContent =
                estadistica.total_registros;


            generarGrafica(
                data.progresion
            );

        })

        .catch(error => {

            console.error(
                'Error obteniendo estadísticas:',
                error
            );

        });
}


filtroPeriodo.addEventListener(
    'change',
    () => {

        if (
            filtroPeriodo.value === 'mes'
        ) {

            filtroMes.style.display =
                'block';

            filtroTrimestre.style.display =
                'none';

        }

        else if (
            filtroPeriodo.value === 'trimestre'
        ) {

            filtroMes.style.display =
                'none';

            filtroTrimestre.style.display =
                'block';

        }

        else {

            filtroMes.style.display =
                'none';

            filtroTrimestre.style.display =
                'none';

        }

        cargarEstadisticas();

    }
);


filtroAnio.addEventListener(
    'change',
    cargarEstadisticas
);


filtroMes.addEventListener(
    'change',
    cargarEstadisticas
);


filtroTrimestre.addEventListener(
    'change',
    cargarEstadisticas
);


cargarEstadisticas();


let graficaAsistencia = null;

function generarGrafica(progresion) {

    const canvas =
        document.getElementById('graficaAsistencia');

    const contexto =
        canvas.getContext('2d');


    // Si ya existe una gráfica,
    // la destruimos antes de crear otra.
    if (graficaAsistencia) {
        graficaAsistencia.destroy();
    }


    const etiquetas =
        progresion.map(item => item.fecha);

    const porcentajes =
        progresion.map(item => item.porcentaje);


    graficaAsistencia = new Chart(
        contexto,
        {
            type: 'line',

            data: {
                labels: etiquetas,

                datasets: [
                    {
                        label: 'Asistencia',

                        data: porcentajes,

                        borderWidth: 3,

                        tension: 0.35,

                        fill: true,

                        pointRadius: 4,

                        pointHoverRadius: 7
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
                            callback: function(value) {
                                return value + '%';
                            }
                        },

                        title: {
                            display: true,
                            text: 'Porcentaje'
                        }
                    },

                    x: {

                        title: {
                            display: true,
                            text: 'Fecha'
                        }

                    }

                },

                plugins: {

                    legend: {
                        display: true
                    },

                    tooltip: {

                        callbacks: {

                            label: function(context) {

                                return `Asistencia: ${context.raw}%`;

                            }

                        }

                    }

                }

            }

        }
    );
}

const circulo =
    document.getElementById("circuloAsistencia");

circulo.style.setProperty(
    "--porcentaje",
    `${92 * 3.6}deg`
);

