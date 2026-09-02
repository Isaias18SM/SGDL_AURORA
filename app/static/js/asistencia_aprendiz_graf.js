document.addEventListener('DOMContentLoaded', function () {

    // =========================================================
    // ELEMENTOS DEL DOM
    // =========================================================

    const filtroPeriodo = document.getElementById('filtroPeriodo');
    const filtroAnio = document.getElementById('filtroAnio');
    const filtroMes = document.getElementById('filtroMes');
    const filtroTrimestre = document.getElementById('filtroTrimestre');

    const circulo = document.getElementById('circuloAsistencia');
    const porcentajeAsistencia = document.getElementById('porcentajeAsistencia');
    const estadoAsistencia = document.getElementById('estadoAsistencia');

    const totalPresentes = document.getElementById('totalPresentes');
    const totalFallas = document.getElementById('totalFallas');
    const totalRegistros = document.getElementById('totalRegistros');

    const periodoGrafica = document.getElementById('periodoGrafica');
    const canvas = document.getElementById('graficaAsistencia');

    let graficaAsistencia = null;


    // =========================================================
    // VALIDAR ELEMENTOS
    // =========================================================

    if (
        !filtroPeriodo ||
        !filtroAnio ||
        !filtroMes ||
        !filtroTrimestre ||
        !canvas
    ) {
        console.error(
            'No se encontraron los elementos necesarios para las estadísticas.'
        );
        return;
    }


    // =========================================================
    // MOSTRAR / OCULTAR FILTROS
    // =========================================================

    function actualizarFiltros() {

        if (filtroPeriodo.value === 'mes') {

            filtroMes.style.display = 'block';
            filtroTrimestre.style.display = 'none';

        } else if (filtroPeriodo.value === 'trimestre') {

            filtroMes.style.display = 'none';
            filtroTrimestre.style.display = 'block';

        } else {

            filtroMes.style.display = 'none';
            filtroTrimestre.style.display = 'none';
        }
    }


    // =========================================================
    // ACTUALIZAR RESUMEN
    // =========================================================

    function actualizarResumen(estadistica) {

        const porcentaje = Number(estadistica.porcentaje || 0);
        const presentes = Number(estadistica.presentes || 0);
        const fallas = Number(estadistica.fallas || 0);
        const total = Number(estadistica.total || 0);

        // Porcentaje

        if (porcentajeAsistencia) {
            porcentajeAsistencia.textContent = `${porcentaje}%`;
        }


        // Círculo

        if (circulo) {

            const grados = Math.max(
                0,
                Math.min(100, porcentaje)
            ) * 3.6;

            circulo.style.setProperty(
                '--porcentaje',
                `${grados}deg`
            );
        }


        // Totales

        if (totalPresentes) {
            totalPresentes.textContent = presentes;
        }

        if (totalFallas) {
            totalFallas.textContent = fallas;
        }

        if (totalRegistros) {
            totalRegistros.textContent = total;
        }


        // Estado

        if (estadoAsistencia) {

            if (total === 0) {

                estadoAsistencia.textContent = 'Sin datos';

            } else if (porcentaje >= 80) {

                estadoAsistencia.textContent = 'En buen estado';

            } else {

                estadoAsistencia.textContent = 'Requiere atención';
            }
        }
    }


    // =========================================================
    // GENERAR GRÁFICA
    // =========================================================

    function generarGrafica(progresion) {

        const contexto = canvas.getContext('2d');

        // Destruir gráfica anterior

        if (graficaAsistencia) {

            graficaAsistencia.destroy();
            graficaAsistencia = null;
        }


        // Validar datos

        if (!Array.isArray(progresion)) {
            progresion = [];
        }


        const etiquetas = progresion.map(
            item => item.fecha
        );

        const porcentajes = progresion.map(
            item => Number(item.porcentaje || 0)
        );


        // Crear gráfica

        graficaAsistencia = new Chart(
            contexto,
            {
                type: 'line',

                data: {

                    labels: etiquetas,

                    datasets: [
                        {
                            label: 'Asistencia acumulada',

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

                                callback: function (value) {
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

                                label: function (context) {

                                    return `Asistencia: ${context.raw}%`;
                                }
                            }
                        }
                    }
                }
            }
        );
    }


    // =========================================================
    // NOMBRE DEL PERÍODO
    // =========================================================

    function obtenerNombrePeriodo(data) {

        if (data.periodo === 'mes') {

            const opcion =
                filtroMes.options[
                    filtroMes.selectedIndex
                ];

            const nombreMes =
                opcion ? opcion.text : '';

            return `${nombreMes} ${data.anio}`;
        }


        if (data.periodo === 'trimestre') {

            return `Trimestre ${filtroTrimestre.value} - ${data.anio}`;
        }


        return `Año ${data.anio}`;
    }


    // =========================================================
    // CARGAR ESTADÍSTICAS
    // =========================================================

    async function cargarEstadisticas() {

        const periodo = filtroPeriodo.value;
        const anio = filtroAnio.value;


        // Crear parámetros

        const parametros = new URLSearchParams();

        parametros.set(
            'periodo',
            periodo
        );

        parametros.set(
            'anio',
            anio
        );


        // Mes

        if (periodo === 'mes') {

            parametros.set(
                'mes',
                filtroMes.value
            );
        }


        // Trimestre

        if (periodo === 'trimestre') {

            parametros.set(
                'trimestre',
                filtroTrimestre.value
            );
        }


        const url =
            `/api/aprendiz/estadisticas?${parametros.toString()}`;


        console.log(
            'Consultando estadísticas:',
            url
        );


        try {

            const response =
                await fetch(
                    url,
                    {
                        method: 'GET',

                        headers: {
                            'Accept': 'application/json'
                        }
                    }
                );


            const data =
                await response.json();


            // Validar HTTP

            if (!response.ok) {

                throw new Error(
                    data.message ||
                    'Error al consultar las estadísticas.'
                );
            }


            // Validar respuesta

            if (data.status !== 'success') {

                throw new Error(
                    data.message ||
                    'No se pudieron obtener las estadísticas.'
                );
            }


            console.log(
                'Estadísticas recibidas:',
                data
            );


            // =================================================
            // ESTADÍSTICA
            // =================================================

            const estadistica =
                data.estadistica || {

                    total: 0,

                    presentes: 0,

                    fallas: 0,

                    excusas: 0,

                    retardos: 0,

                    porcentaje: 0
                };


            // Actualizar tarjetas

            actualizarResumen(
                estadistica
            );


            // =================================================
            // GRÁFICA
            // =================================================

            generarGrafica(
                data.progresion || []
            );


            // =================================================
            // PERÍODO
            // =================================================

            if (periodoGrafica) {

                periodoGrafica.textContent =
                    obtenerNombrePeriodo(data);
            }


        } catch (error) {

            console.error(
                'Error obteniendo estadísticas:',
                error
            );


            actualizarResumen({

                total: 0,

                presentes: 0,

                fallas: 0,

                excusas: 0,

                retardos: 0,

                porcentaje: 0
            });


            generarGrafica([]);


            if (periodoGrafica) {

                periodoGrafica.textContent =
                    'No fue posible cargar el período';
            }
        }
    }


    // =========================================================
    // EVENTOS
    // =========================================================

    filtroPeriodo.addEventListener(
        'change',
        function () {

            actualizarFiltros();

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


    // =========================================================
    // INICIALIZAR
    // =========================================================

    actualizarFiltros();

    cargarEstadisticas();

});
