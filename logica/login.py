"""Ventana de inicio de sesión diseñada con Qt Designer."""
from pathlib import Path

import mysql.connector
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QLineEdit, QMessageBox

from logica.autenticacion import autenticar

ROOT = Path(__file__).resolve().parent.parent


class DialogoLogin:
    def __init__(self):
        archivo = QFile(str(ROOT / "ui" / "login.ui"))
        if not archivo.open(QFile.ReadOnly):
            raise FileNotFoundError("No se encontró ui/login.ui")
        try:
            self.dialogo = QUiLoader().load(archivo)
        finally:
            archivo.close()
        if not isinstance(self.dialogo, QDialog):
            raise RuntimeError("login.ui debe tener una ventana de tipo QDialog")
        hoja_estilos = ROOT / "ui" / "login.qss"
        self.dialogo.setStyleSheet(hoja_estilos.read_text(encoding="utf-8"))

        self.usuario = None
        self._nombre = self.dialogo.findChild(QLineEdit, "txtUsuario")
        self._clave = self.dialogo.findChild(QLineEdit, "txtContrasena")
        self._clave.setEchoMode(QLineEdit.Password)
        self.dialogo.findChild(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton, "btnEntrar").clicked.connect(self.iniciar_sesion)
        self._nombre.returnPressed.connect(self._clave.setFocus)
        self._clave.returnPressed.connect(self.iniciar_sesion)
        self._nombre.setFocus()

    def iniciar_sesion(self):
        nombre = self._nombre.text().strip()
        clave = self._clave.text()
        if not nombre or not clave:
            QMessageBox.warning(self.dialogo, "Datos incompletos", "Escribe tu usuario y contraseña.")
            return
        try:
            persona = autenticar(nombre, clave)
        except mysql.connector.Error as exc:
            QMessageBox.critical(
                self.dialogo, "Error de conexión",
                f"No se pudo consultar MySQL (código {exc.errno}). Revisa el archivo .env y el servicio MySQL."
            )
            self._clave.clear()
            return

        if persona is None:
            self._clave.clear()
            self._clave.setFocus()
            QMessageBox.warning(self.dialogo, "Acceso denegado", "Usuario o contraseña incorrectos, o cuenta desactivada.")
            return

        self.usuario = persona
        self.dialogo.accept()

    def ejecutar(self):
        return self.dialogo.exec() == QDialog.Accepted
