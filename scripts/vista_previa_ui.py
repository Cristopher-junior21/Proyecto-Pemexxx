"""Abre la interfaz para revisar su diseño sin conectar a MySQL.

Uso desde la raíz del repositorio:
    .\\.venv\\Scripts\\python.exe -m scripts.vista_previa_ui
"""
import sys
from pathlib import Path
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QTabWidget, QPushButton, QLabel
from logica.identidad_visual import aplicar_marca, icono_aplicacion

BASE = Path(__file__).resolve().parent.parent
PAGINAS = ("Inicio", "Trabajadores", "Cursos", "Inscripciones", "Cedulas", "Reportes", "Usuarios")


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(icono_aplicacion())
    f = QFile(str(BASE / "ui" / "main.ui"))
    if not f.open(QFile.ReadOnly):
        raise FileNotFoundError("No se pudo abrir ui/main.ui")
    ventana = QUiLoader().load(f)
    f.close()
    if ventana is None:
        raise RuntimeError("Qt Designer no pudo cargar ui/main.ui")
    ventana.setStyleSheet((BASE / "ui" / "style.qss").read_text(encoding="utf-8"))
    aplicar_marca(ventana, "principal")
    tabs = ventana.findChild(QTabWidget, "tabsPrincipal")
    tabs.tabBar().hide()
    ventana.findChild(QLabel, "lblTituloAnio").setText("Sistema de Capacitación Cangrejera — Vista previa")
    ventana.statusBar().hide()
    ventana.findChild(QLabel, "lblContadores").hide()
    ventana.findChild(QLabel, "lblEstado").setText("Vista de diseño")
    encabezados = ("Panel de control", "Trabajadores", "Eventos", "Inscripciones", "Cédulas de registro", "Reportes", "Usuarios")
    for i, nombre in enumerate(PAGINAS):
        b = ventana.findChild(QPushButton, "btnNav"+nombre)
        b.clicked.connect(lambda _checked=False, n=i: tabs.setCurrentIndex(n))
    def actualizar_pagina(i):
        ventana.findChild(QLabel, "lblEncabezado").setText(encabezados[i])
        for j, nombre in enumerate(PAGINAS):
            ventana.findChild(QPushButton, "btnNav"+nombre).setChecked(i==j)
    tabs.currentChanged.connect(actualizar_pagina)
    ventana.findChild(QPushButton, "btnAccesoTrabajador").clicked.connect(lambda: tabs.setCurrentIndex(1))
    ventana.findChild(QPushButton, "btnAccesoCurso").clicked.connect(lambda: tabs.setCurrentIndex(2))
    # Vista previa: los botones de datos no ejecutan operaciones.
    for nombre in ("btnUsuarioGuardar", "btnUsuarioActivar", "btnUsuarioDesactivar",
                   "btnRespaldo", "btnCedulaGenerar", "btnDetalleTrabajador",
                   "btnCedulaVista", "btnTrabDetalle", "btnRegistrarAscenso",
                   "btnReportePdf", "btnTrabGuardar", "btnTrabNuevo", "btnTrabDesactivar", "btnTrabReactivar",
                   "btnCursoGuardar", "btnCursoNuevo", "btnCursoCancelar", "btnInscribir",
                   "btnDarBaja", "btnActualizar", "btnRefrescarPanel"):
        ventana.findChild(QPushButton, nombre).setEnabled(False)
    actualizar_pagina(tabs.currentIndex())
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
