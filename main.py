"""Punto de entrada: ejecutar con `python main.py` desde la raíz."""
import sys
from PySide6.QtWidgets import QApplication
from logica.sistema import SistemaCapacitacion


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Sistema de capacitación Cangrejera")
    ventana = SistemaCapacitacion()
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
