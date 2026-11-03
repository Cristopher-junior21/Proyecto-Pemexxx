"""Entrada principal: primero solicita inicio de sesión, luego abre el sistema."""
import sys
from PySide6.QtWidgets import QApplication
from logica.login import DialogoLogin
from logica.sistema import SistemaCapacitacion
from logica.identidad_visual import icono_aplicacion


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Sistema de capacitación Cangrejera")
    app.setWindowIcon(icono_aplicacion())
    login = DialogoLogin()
    if not login.ejecutar():
        return 0

    ventana = SistemaCapacitacion(login.usuario)
    ventana.ui.setWindowTitle(
        f"Sistema de Capacitación Cangrejera — {ventana.anio}"
    )
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
