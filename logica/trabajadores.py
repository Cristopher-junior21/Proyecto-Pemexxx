"""Operaciones de trabajadores: alta, consulta, edición y baja lógica.

Los widgets referenciados aquí están definidos en ui/main.ui.
Las consultas SQL se ejecutan mediante database/conexion.py.
"""
from PySide6.QtWidgets import QMessageBox
from database import conexion as db


class TrabajadoresMixin:
    def nuevo_trabajador(self):
        self.trabajador_id = None
        for campo in ("txtFicha", "txtNombre", "txtPuesto", "txtDepartamento"):
            self._w(campo).clear()
        self._w("txtFicha").setFocus()

    def cargar_trabajadores(self):
        busqueda = f"%{self._w('txtBuscarTrabajador').text().strip()}%"
        datos = db.fetchall("""
            SELECT id, numero_ficha, nombre_completo, puesto, departamento, activo
            FROM trabajadores
            WHERE numero_ficha LIKE %s OR nombre_completo LIKE %s
              OR puesto LIKE %s OR departamento LIKE %s
            ORDER BY id DESC LIMIT 500
        """, (busqueda,)*4)
        self._cargar_tabla("tablaTrabajadores", [
            (r["id"], r["numero_ficha"], r["nombre_completo"], r["puesto"], r["departamento"],
             "Activo" if r["activo"] else "Inactivo") for r in datos
        ])

    def editar_trabajador_seleccionado(self):
        trab_id = self._seleccionado("tablaTrabajadores")
        if trab_id is None:
            return
        rows = db.fetchall("""SELECT id, numero_ficha, nombre_completo, puesto, departamento
                              FROM trabajadores WHERE id = %s""", (trab_id,))
        if rows:
            r = rows[0]
            self.trabajador_id = r["id"]
            for campo, valor in (("txtFicha", r["numero_ficha"]), ("txtNombre", r["nombre_completo"]),
                                 ("txtPuesto", r["puesto"]), ("txtDepartamento", r["departamento"])):
                self._w(campo).setText(valor)

    def guardar_trabajador(self):
        datos = tuple(self._w(c).text().strip() for c in
                      ("txtFicha", "txtNombre", "txtPuesto", "txtDepartamento"))
        if not all(datos):
            QMessageBox.information(self.ui, "Datos incompletos", "Completa la ficha, nombre, puesto y departamento.")
            return
        if self.trabajador_id is None:
            db.execute("""INSERT INTO trabajadores (numero_ficha, nombre_completo, puesto, departamento)
                          VALUES (%s, %s, %s, %s)""", datos)
        else:
            db.execute("""UPDATE trabajadores SET numero_ficha=%s, nombre_completo=%s, puesto=%s,
                          departamento=%s WHERE id=%s""", datos + (self.trabajador_id,))
        self.nuevo_trabajador()
        self.actualizar_todo()
        QMessageBox.information(self.ui, "Guardado", "Trabajador guardado correctamente.")

    def cambiar_estado_trabajador(self, activo):
        trab_id = self._seleccionado("tablaTrabajadores")
        if trab_id is None:
            QMessageBox.information(self.ui, "Selecciona un trabajador", "Primero selecciona una fila de la tabla.")
            return
        accion = "reactivar" if activo else "desactivar"
        if QMessageBox.question(self.ui, "Confirmar", f"¿Deseas {accion} este trabajador?") != QMessageBox.Yes:
            return
        db.execute("UPDATE trabajadores SET activo=%s WHERE id=%s", (activo, trab_id))
        self.actualizar_todo()

