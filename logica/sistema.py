"""Controlador de la ventana principal.

Carga la interfaz hecha en Qt Designer, conecta señales y métodos de los
módulos y actualiza los datos en pantalla.
"""
from pathlib import Path
import mysql.connector
from PySide6.QtCore import QFile, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem, QAbstractItemView
from database import conexion as db
from logica.trabajadores import TrabajadoresMixin
from logica.cursos import CursosMixin
from logica.inscripciones import InscripcionesMixin

BASE_DIR = Path(__file__).resolve().parent.parent


class SistemaCapacitacion(TrabajadoresMixin, CursosMixin, InscripcionesMixin):
    def __init__(self):
        loader = QUiLoader()
        ui_file = QFile(str(BASE_DIR / "ui" / "main.ui"))
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError("No se encontró ui/main.ui")
        self.ui = loader.load(ui_file)
        ui_file.close()
        if self.ui is None:
            raise RuntimeError("No se pudo abrir el archivo de Qt Designer")

        self.ui.setStyleSheet((BASE_DIR / "ui" / "style.qss").read_text(encoding="utf-8"))
        self.trabajador_id = None
        self.curso_id = None
        self._preparar_tablas()
        self._configurar_eventos()
        self.nuevo_trabajador()
        self.nuevo_curso()
        self._safe(self.actualizar_todo)

    def _w(self, nombre):
        widget = self.ui.findChild(__import__("PySide6.QtCore", fromlist=["QObject"]).QObject, nombre)
        if widget is None:
            raise RuntimeError(f"Falta el componente '{nombre}' en ui/main.ui")
        return widget

    def _safe(self, funcion):
        try:
            return funcion()
        except mysql.connector.Error as exc:
            if exc.errno == 1045:
                detalle = "El servidor rechazó el usuario o contraseña. Revisa DB_USER y DB_PASSWORD en tu archivo .env."
            elif exc.errno == 1049:
                detalle = "No se encontró la base de datos. Revisa DB_NAME en .env."
            elif exc.errno == 1062:
                detalle = "Ese registro ya existe (valor duplicado, posiblemente número de ficha o inscripción)."
            elif exc.errno in (2003, 2005):
                detalle = "No se pudo conectar a MySQL. Revisa el servicio, dirección y puerto."
            else:
                detalle = f"MySQL devolvió un error ({exc.errno}): {exc.msg}"
            self._w("lblEstado").setText("Sin conexión a MySQL o error de consulta.")
            QMessageBox.warning(self.ui, "Error de MySQL", detalle)
        except Exception as exc:
            QMessageBox.critical(self.ui, "Error", str(exc))

    def _preparar_tablas(self):
        self._tabla("tablaTrabajadores", ["ID", "Ficha", "Nombre", "Puesto", "Departamento", "Estado"])
        self._tabla("tablaCursos", ["ID", "Curso", "Inicio", "Fin", "Lugar", "Instructor", "Estado"])
        self._tabla("tablaInscripciones", ["ID", "Ficha", "Trabajador", "Curso", "Fecha de inscripción", "Estado"])

    def _tabla(self, nombre, encabezados):
        tabla = self._w(nombre)
        tabla.setColumnCount(len(encabezados))
        tabla.setHorizontalHeaderLabels(encabezados)
        tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.setColumnHidden(0, True)
        tabla.horizontalHeader().setStretchLastSection(True)

    def _cargar_tabla(self, nombre, filas):
        tabla = self._w(nombre)
        tabla.setRowCount(len(filas))
        for fila_indice, fila in enumerate(filas):
            for columna, valor in enumerate(fila):
                celda = QTableWidgetItem("" if valor is None else str(valor))
                celda.setFlags(celda.flags() & ~Qt.ItemIsEditable)
                tabla.setItem(fila_indice, columna, celda)
        tabla.resizeColumnsToContents()
        tabla.setColumnHidden(0, True)

    def _seleccionado(self, tabla_nombre):
        tabla = self._w(tabla_nombre)
        fila = tabla.currentRow()
        if fila < 0 or tabla.item(fila, 0) is None:
            return None
        return int(tabla.item(fila, 0).text())

    def _configurar_eventos(self):
        conexiones = {
            "btnTrabGuardar": self.guardar_trabajador,
            "btnTrabNuevo": self.nuevo_trabajador,
            "btnTrabDesactivar": lambda: self.cambiar_estado_trabajador(0),
            "btnTrabReactivar": lambda: self.cambiar_estado_trabajador(1),
            "btnCursoGuardar": self.guardar_curso,
            "btnCursoNuevo": self.nuevo_curso,
            "btnCursoCancelar": self.cancelar_curso,
            "btnInscribir": self.inscribir,
            "btnDarBaja": self.baja_inscripcion,
            "btnActualizar": self.actualizar_todo,
        }
        for boton, funcion in conexiones.items():
            self._w(boton).clicked.connect(lambda _checked=False, f=funcion: self._safe(f))
        self._w("txtBuscarTrabajador").textChanged.connect(lambda _=None: self._safe(self.cargar_trabajadores))
        self._w("txtBuscarCurso").textChanged.connect(lambda _=None: self._safe(self.cargar_cursos))
        self._w("tablaTrabajadores").itemSelectionChanged.connect(lambda: self._safe(self.editar_trabajador_seleccionado))
        self._w("tablaCursos").itemSelectionChanged.connect(lambda: self._safe(self.editar_curso_seleccionado))
        self._w("tabsPrincipal").currentChanged.connect(lambda _=None: self._safe(self.actualizar_todo))
        self._w("cmbCursoEstado").addItems(["PROGRAMADO", "EN_CURSO", "FINALIZADO", "CANCELADO"])

    def actualizar_todo(self):
        db_name = db.test_connection()
        self._w("lblEstado").setText(f"Conexión MySQL activa · Esquema: {db_name}")
        self.cargar_trabajadores()
        self.cargar_cursos()
        self.cargar_inscripciones()
        self.cargar_opciones_inscripcion()
        self.cargar_resumen()
        self.ui.statusBar().showMessage("Conectado a MySQL | Prototipo v0.1")

    def cargar_resumen(self):
        conteo = db.fetchall("""
            SELECT
            (SELECT COUNT(*) FROM trabajadores WHERE activo = 1) AS trabajadores,
            (SELECT COUNT(*) FROM cursos WHERE estado <> 'CANCELADO') AS cursos,
            (SELECT COUNT(*) FROM inscripciones WHERE estado = 'INSCRITO') AS inscritos
        """)[0]
        self._w("lblContadores").setText(
            f"Trabajadores activos: {conteo['trabajadores']}     |     "
            f"Cursos no cancelados: {conteo['cursos']}     |     "
            f"Inscripciones activas: {conteo['inscritos']}"
        )

    def show(self):
        self.ui.show()

