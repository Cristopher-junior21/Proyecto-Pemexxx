"""Operaciones de inscripción y baja de participantes de cursos."""
from PySide6.QtWidgets import QMessageBox, QInputDialog
from database import conexion as db


class InscripcionesMixin:
    def cargar_opciones_inscripcion(self):
        trabajadores = db.fetchall("""SELECT id, numero_ficha, nombre_completo FROM trabajadores
                                    WHERE activo=1 ORDER BY nombre_completo""")
        cursos = db.fetchall("""SELECT id, nombre, fecha_inicio FROM cursos
                              WHERE estado IN ('PROGRAMADO','EN_CURSO') ORDER BY fecha_inicio DESC""")
        for combo_name, datos, formateador in (
            ("cmbTrabajador", trabajadores, lambda r: f"{r['numero_ficha']} — {r['nombre_completo']}"),
            ("cmbCurso", cursos, lambda r: f"{r['nombre']} ({r['fecha_inicio']})"),
        ):
            combo = self._w(combo_name)
            actual = combo.currentData()
            combo.clear()
            for r in datos:
                combo.addItem(formateador(r), r["id"])
            if actual is not None:
                for i in range(combo.count()):
                    if combo.itemData(i) == actual:
                        combo.setCurrentIndex(i)
                        break

    def cargar_inscripciones(self):
        datos = db.fetchall("""
            SELECT i.id, t.numero_ficha, t.nombre_completo, c.nombre,
                   i.fecha_inscripcion, i.estado
            FROM inscripciones i
            JOIN trabajadores t ON t.id=i.trabajador_id
            JOIN cursos c ON c.id=i.curso_id
            ORDER BY i.id DESC LIMIT 500
        """)
        self._cargar_tabla("tablaInscripciones", [
            tuple(r[k] for k in ("id", "numero_ficha", "nombre_completo", "nombre", "fecha_inscripcion", "estado"))
            for r in datos
        ])

    def inscribir(self):
        trabajador_id = self._w("cmbTrabajador").currentData()
        curso_id = self._w("cmbCurso").currentData()
        if trabajador_id is None or curso_id is None:
            QMessageBox.information(self.ui, "Datos faltantes", "Necesitas un trabajador activo y un curso disponible.")
            return
        existe = db.fetchall("""SELECT id, estado FROM inscripciones
                              WHERE trabajador_id=%s AND curso_id=%s""", (trabajador_id, curso_id))
        if not existe:
            db.execute("INSERT INTO inscripciones (trabajador_id,curso_id) VALUES (%s,%s)",
                       (trabajador_id, curso_id))
        elif existe[0]["estado"] == "BAJA":
            db.execute("""UPDATE inscripciones SET estado='INSCRITO', fecha_inscripcion=NOW(),
                          fecha_baja=NULL, motivo_baja=NULL, usuario_baja_id=NULL
                          WHERE id=%s""", (existe[0]["id"],))
        else:
            QMessageBox.information(self.ui, "Ya inscrito", "Este trabajador ya está inscrito en ese curso.")
            return
        self.actualizar_todo()
        QMessageBox.information(self.ui, "Inscripción", "Inscripción guardada correctamente.")

    def baja_inscripcion(self):
        inscripcion_id = self._seleccionado("tablaInscripciones")
        if inscripcion_id is None:
            QMessageBox.information(self.ui, "Selecciona inscripción", "Selecciona una fila de Inscripciones.")
            return
        rows = db.fetchall("SELECT estado FROM inscripciones WHERE id=%s", (inscripcion_id,))
        if not rows or rows[0]["estado"] != "INSCRITO":
            QMessageBox.information(self.ui, "Sin cambios", "La inscripción ya está de baja o no existe.")
            return
        motivo, ok = QInputDialog.getText(self.ui, "Motivo de baja", "Motivo de baja del curso (opcional):")
        if not ok:
            return
        # El trigger de MySQL crea automáticamente el registro en bajas_inscripciones.
        db.execute("""UPDATE inscripciones SET estado='BAJA', fecha_baja=NOW(),
                      motivo_baja=%s, usuario_baja_id=NULL
                      WHERE id=%s AND estado='INSCRITO'""",
                   (motivo.strip() or None, inscripcion_id))
        self.actualizar_todo()
        QMessageBox.information(self.ui, "Baja registrada", "Se conservó el historial de la inscripción.")

