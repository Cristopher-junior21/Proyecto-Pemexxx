"""Gestión de eventos (tabla MySQL cursos)."""
from datetime import timedelta
from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (QMessageBox, QDialog, QVBoxLayout, QFormLayout,
    QLabel, QScrollArea, QWidget, QDialogButtonBox, QFrame)
from database import conexion as db
from logica.reglas import (validar_clave_evento, validar_duracion,
    calcular_horas_programadas, estado_evento, CLASIFICACIONES)


class CursosMixin:
    def cargar_tipos_curso(self):
        combo=self._w('cmbCursoTipo'); actual=combo.currentData()
        combo.clear(); combo.addItem('Selecciona tipo',None)
        for r in db.fetchall('SELECT id,nombre FROM tipos_curso WHERE activo=1 ORDER BY id'):
            combo.addItem(r['nombre'],r['id'])
        combo.setCurrentIndex(max(0,combo.findData(actual)))

    def actualizar_campos_modalidad(self):
        mod=self._w('cmbCursoModalidad').currentData()
        self._w('txtCursoLugar').setEnabled(mod=='PRESENCIAL')
        self._w('txtCursoEnlaceVirtual').setEnabled(mod=='EN_LINEA')

    def nuevo_curso(self, preguntar=True):
        if preguntar and not self._confirmar_descartar('evento'):
            return
        self.curso_id=None
        for n in ('txtCursoNombre','txtCursoLugar','txtCursoEnlaceVirtual','txtCursoInstructor','txtClaveEvento','txtDuracionHoras'):
            self._w(n).clear()
        hoy=QDate.currentDate()
        f=hoy if self.anio==hoy.year() else QDate(self.anio,1,1)
        self._w('fechaCursoInicio').setDate(f)
        self._w('fechaCursoFin').setDate(f)
        self._w('horaCursoInicio').setTime(QTime(9,0))
        self._w('horaCursoFin').setTime(QTime(17,0))
        self._w('lblCursoEstadoAuto').setText('Se determinará automáticamente al guardar')
        for n in ('cmbCursoTipo','cmbCursoModalidad','cmbClasificacionEvento'):
            self._w(n).setCurrentIndex(0)
        self.actualizar_campos_modalidad()
        self._actualizar_resumen_horas()
        self._guardar_firma_formulario('evento')

    def _actualizar_resumen_horas(self):
        """Actualiza el total automático cada vez que cambian fechas u horas."""
        try:
            inicio = self._w('fechaCursoInicio').date().toPython()
            fin = self._w('fechaCursoFin').date().toPython()
            hora_inicio = self._w('horaCursoInicio').time().toPython()
            hora_fin = self._w('horaCursoFin').time().toPython()
            calculadas = validar_duracion(
                calcular_horas_programadas(inicio, fin, hora_inicio, hora_fin))
            dias = sum(1 for i in range((fin-inicio).days+1)
                       if (inicio + timedelta(days=i)).weekday() < 5)
            self._w('txtDuracionHoras').setText(f'{calculadas:g}')
            self._w('lblHorasCalculadas').setText(
                f'{dias} días hábiles · {calculadas/dias:g} h/día · total {calculadas:g} h')
        except ValueError as exc:
            self._w('txtDuracionHoras').clear()
            self._w('lblHorasCalculadas').setText(f'Revisa el horario: {exc}')

    def _mostrar_vista_previa_evento(self, datos):
        """Confirma el registro o la edición antes de realizar cualquier INSERT/UPDATE."""
        dialogo = QDialog(self.ui)
        dialogo.setWindowTitle('Vista previa del evento')
        dialogo.setMinimumSize(600, 540)
        dialogo.resize(740, 680)
        dialogo.setModal(True)
        dialogo.setStyleSheet('''
            QDialog { background:#f8fbf9; color:#152b27; }
            QLabel { color:#152b27; font-size:13px; }
            QLabel#tituloVistaEvento { color:#00564a; font-size:21px; font-weight:700; }
            QLabel#subtituloVistaEvento { color:#57776d; font-size:12px; }
            QWidget#contenedorVistaEvento { background:white; border:1px solid #d4e6dc;
                                              border-radius:10px; }
            QPushButton { padding:10px 18px; border-radius:7px;
                          background:#e7f0eb; color:#00564a; font-weight:600; }
            QPushButton#btnConfirmarEvento { background:#00786c; color:white; }
        ''')
        layout = QVBoxLayout(dialogo)
        layout.setSpacing(12)
        titulo=QLabel('Revisa los datos del evento antes de guardar')
        titulo.setObjectName('tituloVistaEvento')
        titulo.setWordWrap(True)
        layout.addWidget(titulo)
        subtitulo=QLabel('Los datos todavía no se han registrado en MySQL.')
        subtitulo.setObjectName('subtituloVistaEvento')
        layout.addWidget(subtitulo)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        contenido=QWidget()
        contenido.setObjectName('contenedorVistaEvento')
        formulario=QFormLayout(contenido)
        formulario.setLabelAlignment(Qt.AlignTop | Qt.AlignLeft)
        formulario.setFormAlignment(Qt.AlignTop)
        formulario.setVerticalSpacing(12)
        formulario.setHorizontalSpacing(24)
        formulario.setContentsMargins(20,20,20,20)
        for etiqueta,valor in datos:
            nombre=QLabel(etiqueta)
            nombre.setStyleSheet('font-weight:600; color:#00564a;')
            valor_widget=QLabel(str(valor) if valor is not None else '—')
            valor_widget.setWordWrap(True)
            valor_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
            formulario.addRow(nombre,valor_widget)
        scroll.setWidget(contenido)
        layout.addWidget(scroll,1)
        botones=QDialogButtonBox()
        btn_volver=botones.addButton('Volver a editar',QDialogButtonBox.RejectRole)
        btn_confirmar=botones.addButton('Confirmar y guardar',QDialogButtonBox.AcceptRole)
        btn_confirmar.setObjectName('btnConfirmarEvento')
        btn_volver.clicked.connect(dialogo.reject)
        btn_confirmar.clicked.connect(dialogo.accept)
        layout.addWidget(botones)
        return dialogo.exec() == QDialog.Accepted

    def cargar_cursos(self):
        filtro='%'+self._w('txtBuscarCurso').text().strip()+'%'
        rows=db.fetchall('''SELECT c.id,c.clave_evento,c.nombre,tc.nombre AS tipo,
            c.clasificacion_evento,c.modalidad,c.fecha_inicio,c.fecha_fin,
            c.duracion_horas,c.lugar,c.enlace_virtual,c.instructor,c.estado
            FROM cursos c LEFT JOIN tipos_curso tc ON tc.id=c.tipo_curso_id
            WHERE YEAR(c.fecha_inicio)=%s AND (c.nombre LIKE %s
              OR COALESCE(c.clave_evento,'') LIKE %s OR COALESCE(tc.nombre,'') LIKE %s)
            ORDER BY c.fecha_inicio DESC,c.id DESC LIMIT 500''',
            (self.anio,filtro,filtro,filtro))
        self._cargar_tabla('tablaCursos',[(r['id'],r['clave_evento'] or '—',r['nombre'],r['tipo'] or '—',
                r['clasificacion_evento'] or '—',r['modalidad'] or '—',r['fecha_inicio'],r['fecha_fin'],
                r['duracion_horas'] or '—',r['instructor'] or '—',r['estado']) for r in rows])

    def editar_curso_seleccionado(self):
        cid=self._seleccionado('tablaCursos')
        if cid is None:return
        rows=db.fetchall('SELECT * FROM cursos WHERE id=%s',(cid,))
        if not rows:return
        c=rows[0]
        if cid != self.curso_id and not self._confirmar_descartar('evento'):
            self._restaurar_seleccion_tabla('tablaCursos',self.curso_id)
            return
        self.curso_id=cid
        for nombre,campo in (('txtClaveEvento','clave_evento'),('txtCursoNombre','nombre'),
                             ('txtCursoLugar','lugar'),('txtCursoEnlaceVirtual','enlace_virtual'),
                             ('txtCursoInstructor','instructor')):
            self._w(nombre).setText(c[campo] or '')
        for n,field in (('fechaCursoInicio','fecha_inicio'),('fechaCursoFin','fecha_fin')):
            f=c[field];self._w(n).setDate(QDate(f.year,f.month,f.day))
        for n,field in (('cmbCursoTipo','tipo_curso_id'),('cmbCursoModalidad','modalidad'),
                        ('cmbClasificacionEvento','clasificacion_evento')):
            self._w(n).setCurrentIndex(max(0,self._w(n).findData(c[field])))
        for n,campo in (('horaCursoInicio','hora_inicio'),('horaCursoFin','hora_fin')):
            h=c[campo]
            if h is not None:
                # MySQL devuelve TIME como timedelta.
                from datetime import timedelta
                if isinstance(h,timedelta):
                    seg=int(h.total_seconds())
                    h=QTime((seg//3600)%24,(seg//60)%60)
                else:
                    h=QTime(h.hour,h.minute)
                self._w(n).setTime(h)
            else:
                self._w(n).setTime(QTime(9,0) if n=='horaCursoInicio' else QTime(17,0))
        self._w('lblCursoEstadoAuto').setText('Estado: '+c['estado'])
        self.actualizar_campos_modalidad()
        self._actualizar_resumen_horas()
        self._guardar_firma_formulario('evento')

    def guardar_curso(self):
        if not self._requiere('captura'):return
        clave=validar_clave_evento(self._w('txtClaveEvento').text().strip())
        nombre=self._w('txtCursoNombre').text().strip()
        tipo=self._w('cmbCursoTipo').currentData()
        mod=self._w('cmbCursoModalidad').currentData()
        clas=self._w('cmbClasificacionEvento').currentData()
        hora_ini=self._w('horaCursoInicio').time().toPython()
        hora_fin=self._w('horaCursoFin').time().toPython()
        # La duración nunca depende de un valor capturado por el usuario.
        dur=validar_duracion(calcular_horas_programadas(
            self._w('fechaCursoInicio').date().toPython(),
            self._w('fechaCursoFin').date().toPython(),hora_ini,hora_fin))
        ini=self._w('fechaCursoInicio').date().toPython()
        fin=self._w('fechaCursoFin').date().toPython()
        if not nombre or tipo is None or mod not in ('PRESENCIAL','EN_LINEA') or clas not in CLASIFICACIONES:
            raise ValueError('Completa nombre, tipo, modalidad y clasificación del evento.')
        if ini.year!=self.anio:
            raise ValueError(f'El evento debe iniciar en el año de gestión seleccionado ({self.anio}).')
        if fin<ini:raise ValueError('La fecha de término no puede ser anterior al inicio.')
        lugar=self._w('txtCursoLugar').text().strip() or None
        link=self._w('txtCursoEnlaceVirtual').text().strip() or None
        if mod=='PRESENCIAL':
            if not lugar:raise ValueError('Indica el lugar del evento presencial.')
            link=None
        else:
            if not link or not link.startswith(('https://','http://')):
                raise ValueError('Indica un enlace http(s) válido para el evento en línea.')
            lugar=None
        # El estado no se recibe del formulario: depende del calendario.
        anterior_estado=None
        if self.curso_id is not None:
            res=db.fetchall('SELECT estado FROM cursos WHERE id=%s',(self.curso_id,))
            if not res:raise ValueError('El evento ya no existe.')
            anterior_estado=res[0]['estado']
        estado=estado_evento(ini,fin,hora_ini,hora_fin,
                             cancelado=anterior_estado=='CANCELADO')
        # Si se cambia la fecha de un evento con participantes, verificar que
        # no se superponga con OTRO evento activo del mismo trabajador.
        if self.curso_id is not None and estado!='CANCELADO':
            conflictos=db.fetchall('''SELECT DISTINCT t.numero_ficha,otro.nombre AS nombre_evento
                FROM inscripciones i JOIN trabajadores t ON t.id=i.trabajador_id
                JOIN inscripciones io ON io.trabajador_id=i.trabajador_id AND io.id<>i.id AND io.estado='INSCRITO'
                JOIN cursos otro ON otro.id=io.curso_id AND otro.estado<>'CANCELADO'
                WHERE i.curso_id=%s AND i.estado='INSCRITO'
                  AND otro.fecha_inicio<=%s AND otro.fecha_fin >=%s LIMIT 1''',(self.curso_id,fin,ini))
            if conflictos:
                raise ValueError('El nuevo calendario coincide con otro evento del trabajador '+conflictos[0]['numero_ficha'])
        instructor=self._w('txtCursoInstructor').text().strip() or None
        dias=sum(1 for i in range((fin-ini).days+1) if (ini+timedelta(days=i)).weekday()<5)
        datos_vista=(
            ('Operación', 'Modificar evento' if self.curso_id is not None else 'Nuevo evento'),
            ('Año de gestión', str(self.anio)),
            ('Clave del evento', clave),
            ('Nombre del evento', nombre),
            ('Tipo de evento', self._w('cmbCursoTipo').currentText()),
            ('Clasificación', self._w('cmbClasificacionEvento').currentText()),
            ('Modalidad', self._w('cmbCursoModalidad').currentText()),
            ('Inicio', ini.strftime('%d/%m/%Y')),
            ('Término', fin.strftime('%d/%m/%Y')),
            ('Horario diario', f'{hora_ini.strftime("%H:%M")} a {hora_fin.strftime("%H:%M")}'),
            ('Días hábiles', dias),
            ('Horas por día', f'{dur/dias:g} h'),
            ('Duración total calculada', f'{dur:g} horas'),
            ('Lugar', lugar if mod=='PRESENCIAL' else 'No aplica'),
            ('Enlace virtual', link if mod=='EN_LINEA' else 'No aplica'),
            ('Instructor', instructor or 'Sin especificar'),
            ('Estado automático', estado.replace('_',' ').title()),
        )
        if not self._mostrar_vista_previa_evento(datos_vista):
            return  # No se escribió nada en MySQL.
        args=(clave,nombre,tipo,mod,clas,ini,fin,hora_ini,hora_fin,dur,lugar,link,
              instructor,estado)
        if self.curso_id is None:
            db.execute('''INSERT INTO cursos(clave_evento,nombre,tipo_curso_id,modalidad,clasificacion_evento,
              fecha_inicio,fecha_fin,hora_inicio,hora_fin,duracion_horas,lugar,enlace_virtual,instructor,estado)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',args)
        else:
            db.execute('''UPDATE cursos SET clave_evento=%s,nombre=%s,tipo_curso_id=%s,modalidad=%s,
               clasificacion_evento=%s,fecha_inicio=%s,fecha_fin=%s,hora_inicio=%s,hora_fin=%s,
               duracion_horas=%s,lugar=%s,enlace_virtual=%s,instructor=%s,estado=%s WHERE id=%s''', args+(self.curso_id,))
        self.nuevo_curso(preguntar=False);self.actualizar_todo()
        QMessageBox.information(self.ui,'Evento guardado','Los datos del evento se guardaron correctamente.')

    def cancelar_curso(self):
        if not self._requiere('captura'):return
        cid=self._seleccionado('tablaCursos')
        if cid is None:raise ValueError('Selecciona un evento para cancelarlo.')
        if not self._confirmar_descartar('evento'):return
        if QMessageBox.question(self.ui,'Cancelar evento','¿Cancelar este evento y conservar su historial?')!=QMessageBox.Yes:
            return
        db.execute("UPDATE cursos SET estado='CANCELADO' WHERE id=%s",(cid,))
        self.actualizar_todo()
