"""Inscripciones: bloqueo transaccional de solapamientos de fechas."""
from PySide6.QtWidgets import QMessageBox, QInputDialog
from database import conexion as db


class InscripcionesMixin:
    def cargar_opciones_inscripcion(self):
        trabs=db.fetchall('SELECT id,numero_ficha,nombre_completo FROM trabajadores WHERE activo=1 ORDER BY nombre_completo')
        evs=db.fetchall("""SELECT id,nombre,clave_evento,fecha_inicio FROM cursos
           WHERE estado IN ('PROGRAMADO','EN_CURSO') AND YEAR(fecha_inicio)=%s
           ORDER BY fecha_inicio DESC""",(self.anio,))
        for n,datos,form in (
           ('cmbTrabajador',trabs,lambda r:f"{r['numero_ficha']} — {r['nombre_completo']}"),
           ('cmbCurso',evs,lambda r:f"{r['clave_evento'] or 'SIN CLAVE'} | {r['nombre']} ({r['fecha_inicio']})")):
            cb=self._w(n);cur=cb.currentData();cb.clear();cb.addItem('Seleccionar...',None)
            for r in datos:cb.addItem(form(r),r['id'])
            cb.setCurrentIndex(max(0,cb.findData(cur)))

    def cargar_inscripciones(self):
        datos=db.fetchall('''SELECT i.id,t.numero_ficha,t.nombre_completo,c.nombre,
           i.fecha_inscripcion,i.estado FROM inscripciones i
           JOIN trabajadores t ON t.id=i.trabajador_id JOIN cursos c ON c.id=i.curso_id
           WHERE YEAR(c.fecha_inicio)=%s ORDER BY i.id DESC LIMIT 500''',(self.anio,))
        self._cargar_tabla('tablaInscripciones',[tuple(r[k] for k in ('id','numero_ficha',
           'nombre_completo','nombre','fecha_inscripcion','estado')) for r in datos])

    def inscribir(self):
        if not self._requiere('captura'):return
        tid=self._w('cmbTrabajador').currentData(); cid=self._w('cmbCurso').currentData()
        if tid is None or cid is None:raise ValueError('Selecciona trabajador y evento.')
        with db.connection() as conn:
            try:
                cur=conn.cursor(dictionary=True)
                # Serializa simultáneas inscripciones del mismo trabajador.
                cur.execute('SELECT id FROM trabajadores WHERE id=%s AND activo=1 FOR UPDATE',(tid,))
                if not cur.fetchone():raise ValueError('El trabajador está inactivo o no existe.')
                cur.execute('''SELECT id,nombre,fecha_inicio,fecha_fin FROM cursos
                    WHERE id=%s AND estado IN ('PROGRAMADO','EN_CURSO')''',(cid,))
                ev=cur.fetchone()
                if not ev:raise ValueError('El evento seleccionado no está disponible.')
                cur.execute('''SELECT c.nombre,c.fecha_inicio,c.fecha_fin FROM inscripciones i
                    JOIN cursos c ON c.id=i.curso_id
                    WHERE i.trabajador_id=%s AND i.estado='INSCRITO'
                      AND c.estado<>'CANCELADO' AND c.id<>%s
                      AND c.fecha_inicio<=%s AND c.fecha_fin>=%s LIMIT 1''',
                      (tid,cid,ev['fecha_fin'],ev['fecha_inicio']))
                conflicto=cur.fetchone()
                if conflicto:
                    raise ValueError('El trabajador ya tiene un evento durante esas fechas: '+conflicto['nombre'])
                cur.execute('SELECT id,estado FROM inscripciones WHERE trabajador_id=%s AND curso_id=%s',(tid,cid))
                anterior=cur.fetchone()
                if anterior and anterior['estado']=='INSCRITO':
                    raise ValueError('El trabajador ya está inscrito en este evento.')
                if anterior:
                    cur.execute("""UPDATE inscripciones SET estado='INSCRITO',fecha_inscripcion=NOW(),
                       fecha_baja=NULL,motivo_baja=NULL,usuario_baja_id=NULL WHERE id=%s""",(anterior['id'],))
                else:
                    cur.execute('INSERT INTO inscripciones(trabajador_id,curso_id) VALUES(%s,%s)',(tid,cid))
                conn.commit()
            except Exception:
                conn.rollback();raise
            finally:
                cur.close()
        self.actualizar_todo()
        self._w('cmbTrabajador').setCurrentIndex(0)
        self._w('cmbCurso').setCurrentIndex(0)
        self._guardar_firma_formulario('inscripcion')
        QMessageBox.information(self.ui,'Inscripción guardada','El trabajador quedó inscrito en el evento.')

    def baja_inscripcion(self):
        if not self._requiere('captura'):return
        iid=self._seleccionado('tablaInscripciones')
        if iid is None:raise ValueError('Selecciona una inscripción.')
        estado=db.fetchall('SELECT estado FROM inscripciones WHERE id=%s',(iid,))
        if not estado or estado[0]['estado']!='INSCRITO':raise ValueError('La inscripción ya está de baja.')
        motivo,ok=QInputDialog.getText(self.ui,'Baja de evento','Motivo de baja (opcional):')
        if not ok:return
        db.execute("""UPDATE inscripciones SET estado='BAJA',fecha_baja=NOW(),
          motivo_baja=%s,usuario_baja_id=%s WHERE id=%s""",
          (motivo.strip() or None,self.usuario['id'],iid))
        self.actualizar_todo()
        QMessageBox.information(self.ui,'Baja registrada','Se conservó el historial de participación.')

    def registrar_ascenso(self):
        """Actualiza Nivel con confirmación tras finalizar un evento de ASCENSO."""
        if not self._requiere('captura'):return
        iid=self._seleccionado('tablaInscripciones')
        if iid is None:raise ValueError('Selecciona un trabajador inscrito.')
        with db.connection() as conn:
            cur=conn.cursor(dictionary=True)
            try:
                cur.execute('''SELECT t.id AS tid,d.nivel,c.clasificacion_evento,c.estado AS estado_evento,
                   i.estado AS estado_inscripcion,c.nombre
                   FROM inscripciones i JOIN trabajadores t ON t.id=i.trabajador_id
                   JOIN cursos c ON c.id=i.curso_id LEFT JOIN trabajador_detalle d ON d.trabajador_id=t.id
                   WHERE i.id=%s FOR UPDATE''',(iid,))
                r=cur.fetchone()
                if not r or r['clasificacion_evento']!='ASCENSO' or r['estado_evento']!='FINALIZADO' or r['estado_inscripcion']!='INSCRITO':
                    raise ValueError('El evento debe ser de ASCENSO, estar finalizado y mantener la inscripción activa.')
                nuevo,ok=QInputDialog.getText(self.ui,'Registrar ascenso',
                  f"Nivel actual: {r['nivel'] or 'Sin registrar'}. Nuevo nivel:")
                if not ok:return
                nuevo=nuevo.strip()
                if not nuevo or len(nuevo)>40:
                    raise ValueError('Escribe un nivel válido de máximo 40 caracteres.')
                if QMessageBox.question(self.ui,'Confirmar cambio de nivel',
                   'Confirma que verificaste el cumplimiento de los requisitos del ascenso. ¿Aplicar el nuevo nivel?')!=QMessageBox.Yes:
                    return
                cur.execute('''INSERT INTO trabajador_detalle(trabajador_id,nivel) VALUES(%s,%s)
                  ON DUPLICATE KEY UPDATE nivel=VALUES(nivel)''',(r['tid'],nuevo))
                cur.execute('''INSERT INTO historial_niveles(trabajador_id,inscripcion_id,
                  nivel_anterior,nivel_nuevo,usuario_id) VALUES(%s,%s,%s,%s,%s)''',
                  (r['tid'],iid,r['nivel'],nuevo,self.usuario['id']))
                conn.commit()
            except Exception:
                conn.rollback();raise
            finally:
                cur.close()
        QMessageBox.information(self.ui,'Cambio registrado','Nivel actualizado y registrado en el historial.')
