"""Centraliza el logotipo en el sistema sin depender de rutas absolutas."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel

BASE = Path(__file__).resolve().parent.parent
RUTA_ICO = BASE / "assets" / "pemex-logo.ico"
RUTA_PNG = BASE / "assets" / "pemex-logo.png"


def icono_aplicacion():
    return QIcon(str(RUTA_ICO))


def aplicar_marca(ventana, zona="principal"):
    """Asigna icono de Windows y pixmaps a etiquetas ya definidas en .ui."""
    if RUTA_ICO.is_file():
        ventana.setWindowIcon(icono_aplicacion())
    imagen = QPixmap(str(RUTA_PNG))
    if imagen.isNull():
        return
    tamaños = {"principal": {"brandInitial": 86, "heroBadgeSymbol": 58},
               "login": {"logoLogin": 94}}.get(zona, {})
    for nombre, lado in tamaños.items():
        etiqueta = ventana.findChild(QLabel, nombre)
        if etiqueta is None:
            continue
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setText("")
        etiqueta.setPixmap(imagen.scaled(lado, lado,
                            Qt.KeepAspectRatio, Qt.SmoothTransformation))
