"""Presentación coherente y adaptable de todas las tablas del sistema.

No cambia los datos, los nombres de columnas ni las consultas SQL.
Cada sección define anchos mínimos y pesos para aprovechar el espacio disponible.
Al faltar espacio se habilita el desplazamiento horizontal sin comprimir los textos.
"""
from PySide6.QtCore import QObject, QEvent, QTimer, Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView

# columna: (peso relativo, ancho mínimo en píxeles)
# El identificador interno (columna 0) se mantiene oculto cuando corresponde.
CONFIGURACION = {
    'tablaTrabajadores': {
        1: (14, 110),  # Ficha
        2: (30, 215),  # Nombre
        3: (20, 150),  # Puesto
        4: (23, 180),  # Departamento
        5: (13, 115),  # Estado
    },
    'tablaCursos': {
        1: (12, 110),  # Clave
        2: (27, 260),  # Evento
        3: (13, 125),  # Tipo
        4: (14, 135),  # Clasificación
        5: (13, 120),  # Modalidad
        6: (12, 115),  # Inicio
        7: (12, 115),  # Fin
        8: (8, 80),    # Horas
        9: (18, 160),  # Instructor
        10: (11, 130), # Estado
    },
    'tablaInscripciones': {
        1: (13, 115),  # Ficha
        2: (26, 220),  # Trabajador
        3: (31, 260),  # Evento
        4: (17, 135),  # Registro
        5: (13, 125),  # Estado
    },
    'tablaReportes': {
        1: (11, 110),  # Clave
        2: (29, 260),  # Evento
        3: (15, 130),  # Tipo
        4: (14, 125),  # Modalidad
        5: (16, 145),  # Clasificación
        6: (13, 125),  # Inicio
        7: (14, 125),  # Estado
        8: (13, 115),  # Inscritos
    },
    'tablaUsuarios': {
        1: (40, 240),  # Nombre
        2: (25, 160),  # Usuario
        3: (20, 145),  # Rol
        4: (15, 115),  # Estado
    },
    'tablaProximosCursos': {
        0: (43, 230),  # Evento (sin ID oculto)
        1: (19, 125),  # Fecha
        2: (20, 145),  # Tipo
        3: (18, 130),  # Modalidad
    },
}


def calcular_anchos(espacio, columnas):
    """Devuelve anchos proporcionales, respetando los mínimos.

    columnas: [(peso, minimo), ...] en el orden visual mostrado.
    Si el ancho de la ventana es insuficiente, Qt habilitará el scroll horizontal.
    """
    if not columnas:
        return []
    minimos = [minimo for _, minimo in columnas]
    minimo_total = sum(minimos)
    if espacio <= minimo_total:
        return minimos
    extra = espacio - minimo_total
    total_pesos = sum(peso for peso, _ in columnas)
    salida = [minimo + (extra * peso) // total_pesos for peso, minimo in columnas]
    salida[0] += espacio - sum(salida)  # evitar unos píxeles sin utilizar
    return salida


class AjusteProporcional(QObject):
    """Observa el área visible de una tabla y ajusta solo sus columnas."""

    def __init__(self, tabla, nombre):
        super().__init__(tabla)
        self.tabla = tabla
        self.nombre = nombre
        self._pendiente = False
        encabezado = tabla.horizontalHeader()
        encabezado.setStretchLastSection(False)
        encabezado.setSectionsMovable(False)
        encabezado.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        encabezado.setHighlightSections(False)
        tabla.setAlternatingRowColors(True)
        tabla.setWordWrap(False)
        tabla.setTextElideMode(Qt.ElideRight)
        tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        tabla.verticalHeader().setDefaultSectionSize(36)
        for indice in range(tabla.columnCount()):
            encabezado.setSectionResizeMode(indice, QHeaderView.Interactive)
        tabla.viewport().installEventFilter(self)
        self.solicitar_ajuste()

    def eventFilter(self, objeto, evento):
        if objeto is self.tabla.viewport() and evento.type() == QEvent.Resize:
            self.solicitar_ajuste()
        return super().eventFilter(objeto, evento)

    def solicitar_ajuste(self):
        if not self._pendiente:
            self._pendiente = True
            QTimer.singleShot(0, self.ajustar)

    def ajustar(self):
        self._pendiente = False
        configuracion = CONFIGURACION.get(self.nombre)
        if not configuracion:
            return
        indices = [i for i in configuracion if i < self.tabla.columnCount()
                   and not self.tabla.isColumnHidden(i)]
        if not indices:
            return
        pesos_minimos = [configuracion[i] for i in indices]
        disponible = max(0, self.tabla.viewport().width() - 2)
        anchos = calcular_anchos(disponible, pesos_minimos)
        for indice, ancho in zip(indices, anchos):
            if self.tabla.columnWidth(indice) != ancho:
                self.tabla.setColumnWidth(indice, ancho)


def instalar_ajustador(tabla, nombre):
    """Instala el ajuste una sola vez; no interfiere con las conexiones de botones."""
    existente = getattr(tabla, '_ajuste_proporcional', None)
    if existente is None:
        tabla._ajuste_proporcional = AjusteProporcional(tabla, nombre)
    else:
        existente.solicitar_ajuste()


def reajustar_tabla(tabla):
    ajuste = getattr(tabla, '_ajuste_proporcional', None)
    if ajuste is not None:
        ajuste.solicitar_ajuste()
