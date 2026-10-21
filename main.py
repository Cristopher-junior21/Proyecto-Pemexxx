"""Entrada principal: primero solicita inicio de sesión, luego abre el sistema."""
import sys
from PySide6.QtWidgets import QApplication
from logica.login import DialogoLogin
from logica.sistema import SistemaCapacitacion


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Sistema de capacitación Cangrejera")
    login = DialogoLogin()
    if not login.ejecutar():
        return 0

    ventana = SistemaCapacitacion()
    ventana.ui.setWindowTitle(
        f"Sistema de Capacitación | Cangrejera — {login.usuario['nombre_completo']}"
    )
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
