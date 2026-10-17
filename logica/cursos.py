"""Operaciones de cursos de capacitación."""
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QMessageBox
from database import conexion as db


class CursosMixin:
    def nuevo_curso(self):
        self.curso_id = None
        for campo in ("txtCursoNombre", "txtCursoLugar", "txtCursoInstructor"):
            self._w(campo).clear()
        fecha = QDate.currentDate()
        self._w("fechaCursoInicio").setDate(fecha)
        self._w("fechaCursoFin").setDate(fecha)
        self._w("cmbCursoEstado").setCurrentText("PROGRAMADO")

    def cargar_cursos(self):
        busqueda = f"%{self._w('txtBuscarCurso').text().strip()}%"
        datos = db.fetchall("""
            SELECT id, nombre, fecha_inicio, fecha_fin, lugar, instructor, estado
            FROM cursos
            WHERE nombre LIKE %s OR COALESCE(lugar, '') LIKE %s OR COALESCE(instructor, '') LIKE %s
            ORDER BY fecha_inicio DESC, id DESC LIMIT 500
        """, (busqueda,)*3)
        self._cargar_tabla("tablaCursos", [
            tuple(r[k] for k in ("id", "nombre", "fecha_inicio", "fecha_fin", "lugar", "instructor", "estado"))
            for r in datos
        ])

    def editar_curso_seleccionado(self):
        curso_id = self._seleccionado("tablaCursos")
        if curso_id is None:
            return
        rows = db.fetchall("""SELECT id, nombre, fecha_inicio, fecha_fin, lugar, instructor, estado
                             FROM cursos WHERE id=%s""", (curso_id,))
        if rows:
            r = rows[0]
            self.curso_id = r["id"]
            for campo, clave in (("txtCursoNombre", "nombre"), ("txtCursoLugar", "lugar"),
                                 ("txtCursoInstructor", "instructor")):
                self._w(campo).setText(r[clave] or "")
            for campo, clave in (("fechaCursoInicio", "fecha_inicio"), ("fechaCursoFin", "fecha_fin")):
                fecha = r[clave]
                self._w(campo).setDate(QDate(fecha.year, fecha.month, fecha.day))
            self._w("cmbCursoEstado").setCurrentText(r["estado"])

    def guardar_curso(self):
        nombre = self._w("txtCursoNombre").text().strip()
        fecha_inicio = self._w("fechaCursoInicio").date().toPython()
        fecha_fin = self._w("fechaCursoFin").date().toPython()
        if not nombre:
            QMessageBox.information(self.ui, "Datos incompletos", "Escribe el nombre del curso.")
            return
        if fecha_fin < fecha_inicio:
            QMessageBox.information(self.ui, "Fechas incorrectas", "La fecha de fin no puede ser anterior al inicio.")
            return
        args = (nombre, fecha_inicio, fecha_fin,
                self._w("txtCursoLugar").text().strip() or None,
                self._w("txtCursoInstructor").text().strip() or None,
                self._w("cmbCursoEstado").currentText())
        if self.curso_id is None:
            db.execute("""INSERT INTO cursos (nombre, fecha_inicio, fecha_fin, lugar, instructor, estado)
                          VALUES (%s,%s,%s,%s,%s,%s)""", args)
        else:
            db.execute("""UPDATE cursos SET nombre=%s,fecha_inicio=%s,fecha_fin=%s,lugar=%s,
                          instructor=%s,estado=%s WHERE id=%s""", args + (self.curso_id,))
        self.nuevo_curso()
        self.actualizar_todo()
        QMessageBox.information(self.ui, "Guardado", "Curso guardado correctamente.")

    def cancelar_curso(self):
        curso_id = self._seleccionado("tablaCursos")
        if curso_id is None:
            QMessageBox.information(self.ui, "Selecciona un curso", "Primero selecciona una fila de la tabla.")
            return
        if QMessageBox.question(self.ui, "Confirmar", "¿Deseas cancelar el curso sin eliminar su historial?") != QMessageBox.Yes:
            return
        db.execute("UPDATE cursos SET estado='CANCELADO' WHERE id=%s", (curso_id,))
        self.actualizar_todo()

