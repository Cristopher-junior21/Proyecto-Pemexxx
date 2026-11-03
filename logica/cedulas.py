"""Detalle del trabajador y cédula basada en el formato facilitado por el área."""
from pathlib import Path
from datetime import datetime
import re
from PySide6.QtCore import QFile, QEvent, QObject
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMessageBox,QDialog,QLineEdit,QPushButton,QInputDialog
from database import conexion as db

RAIZ=Path(__file__).resolve().parent.parent
CAMPOS=('curp','nombres','apellido_paterno','apellido_materno','centro_trabajo','clave_centro_trabajo',
 'subsidiaria','gerencia','clave_departamento','categoria_base','nivel','turno','tipo_plaza',
 'jefe_inmediato','extension','entidad_federativa','municipio','nivel_estudios','carrera',
 'documento_probatorio','anio_documento','institucion_tipo','discapacidad','estado_civil','hijos_dependientes')


class CedulasMixin:
    def cargar_opciones_cedula(self):
        # Cédulas se solicitan por evento, nunca por inscripción individual.
        cb=self._w('cmbCedulaEvento');anterior=cb.currentData()
        cb.blockSignals(True)
        try:
            cb.clear();cb.addItem('Selecciona un evento...',None)
            rows=db.fetchall('''SELECT c.id,c.clave_evento,c.nombre,
              SUM(CASE WHEN i.estado='INSCRITO' THEN 1 ELSE 0 END) AS inscritos
              FROM cursos c LEFT JOIN inscripciones i ON i.curso_id=c.id
              WHERE YEAR(c.fecha_inicio)=%s AND c.estado<>'CANCELADO'
              GROUP BY c.id,c.clave_evento,c.nombre
              ORDER BY c.fecha_inicio DESC,c.nombre''',(self.anio,))
            for r in rows:
                cb.addItem(f"{r['clave_evento'] or 'SIN CLAVE'} — {r['nombre']} "
                           f"({r['inscritos']} inscritos)",r['id'])
            cb.setCurrentIndex(max(0,cb.findData(anterior)))
        finally:cb.blockSignals(False)

    def _datos_cedulas(self):
        cid=self._w('cmbCedulaEvento').currentData()
        if cid is None:
            raise ValueError('Selecciona un evento antes de generar las cédulas.')
        datos=db.fetchall('''SELECT i.id AS inscripcion_id,t.id AS trabajador_id,
            t.numero_ficha,t.nombre_completo,t.puesto,t.departamento,
            c.nombre AS evento,c.clave_evento,c.duracion_horas,c.fecha_inicio,c.fecha_fin,
            c.modalidad,tc.nombre AS tipo,
            d.curp,d.nombres,d.apellido_paterno,d.apellido_materno,d.centro_trabajo,
            d.clave_centro_trabajo,d.subsidiaria,d.gerencia,d.clave_departamento,
            d.categoria_base,d.nivel,d.turno,d.tipo_plaza,d.jefe_inmediato,d.extension,
            d.entidad_federativa,d.municipio,d.nivel_estudios,d.carrera,
            d.documento_probatorio,d.anio_documento,d.institucion_tipo,d.discapacidad,
            d.estado_civil,d.hijos_dependientes
            FROM inscripciones i JOIN trabajadores t ON t.id=i.trabajador_id
            JOIN cursos c ON c.id=i.curso_id LEFT JOIN tipos_curso tc ON tc.id=c.tipo_curso_id
            LEFT JOIN trabajador_detalle d ON d.trabajador_id=t.id
            WHERE c.id=%s AND i.estado='INSCRITO' AND c.estado<>'CANCELADO'
            ORDER BY t.nombre_completo,t.numero_ficha''',(cid,))
        if not datos:
            raise ValueError('El evento seleccionado no tiene trabajadores inscritos. '
                             'Primero registra al menos una inscripción para generar las cédulas.')
        return datos

    def abrir_detalle(self):
        if not self._requiere('captura'):return
        # Puede abrirse desde trabajadores, o desde la inscripción en Cédulas.
        trab=self._seleccionado('tablaTrabajadores') if self._w('tabsPrincipal').currentIndex()==1 else None
        if trab is None:
            raise ValueError('Abre Trabajadores y selecciona a la persona cuyos datos quieras completar.')
        f=QFile(str(RAIZ/'ui'/'detalle_trabajador.ui'))
        if not f.open(QFile.ReadOnly):raise RuntimeError('Falta ui/detalle_trabajador.ui')
        dlg=QUiLoader().load(f);f.close()
        if not isinstance(dlg,QDialog):raise RuntimeError('Interfaz de detalle inválida')
        dlg.resize(900,600)
        rows=db.fetchall('SELECT * FROM trabajador_detalle WHERE trabajador_id=%s',(trab,))
        data=rows[0] if rows else {}
        for campo in CAMPOS:
            edit=dlg.findChild(QLineEdit,'det_'+campo)
            edit.setText('' if data.get(campo) is None else str(data[campo]))
        def firma_detalle():
            return tuple((campo,dlg.findChild(QLineEdit,'det_'+campo).text()) for campo in CAMPOS)
        original=firma_detalle()
        autorizado={'cerrar':False}

        class ProtegerCierre(QObject):
            def eventFilter(self,obj,event):
                if event.type()==QEvent.Close and not autorizado['cerrar'] and firma_detalle()!=original:
                    if QMessageBox.question(dlg,'Datos sin guardar',
                          'Hay información del trabajador sin guardar. ¿Deseas descartarla?',
                          QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
                        event.ignore()
                        return True
                return super().eventFilter(obj,event)

        proteger=ProtegerCierre(dlg)
        dlg.installEventFilter(proteger)
        def cerrar_detalle():
            if firma_detalle()!=original and QMessageBox.question(dlg,'Datos sin guardar',
                '¿Descartar los datos del trabajador que aún no guardaste?',
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
                return
            autorizado['cerrar']=True
            dlg.reject()
        dlg.findChild(QPushButton,'btnDetalleCerrar').clicked.connect(cerrar_detalle)

        def guardar():
            vals={n:dlg.findChild(QLineEdit,'det_'+n).text().strip() or None for n in CAMPOS}
            if vals['curp'] and not re.fullmatch(r'[A-Za-z0-9]{18}',vals['curp']):
                QMessageBox.warning(dlg,'CURP inválida','La CURP debe tener 18 caracteres.');return
            for campo in ('anio_documento','hijos_dependientes'):
                if vals[campo] is not None:
                    if not vals[campo].isdigit():
                        QMessageBox.warning(dlg,'Valor inválido',campo+' debe ser numérico.');return
                    vals[campo]=int(vals[campo])
            if vals['hijos_dependientes'] is not None and not (0<=vals['hijos_dependientes']<=255):
                QMessageBox.warning(dlg,'Valor inválido','Hijos dependientes debe estar entre 0 y 255.');return
            if vals['anio_documento'] is not None and not (1900<=vals['anio_documento']<=2100):
                QMessageBox.warning(dlg,'Valor inválido','Revisa el año del documento.');return
            # Las opciones enumeradas coinciden con las de la cédula.
            for n,validos in {'tipo_plaza':('PLANTA','TRANSITORIO','CONFIANZA','SINDICALIZADO'),
                              'institucion_tipo':('PUBLICA','PRIVADA')}.items():
                if vals[n] and vals[n].upper() not in validos:
                    QMessageBox.warning(dlg,'Valor inválido',n+': '+', '.join(validos));return
                if vals[n]:vals[n]=vals[n].upper()
            names=list(CAMPOS);params=[vals[n] for n in names]
            sql='INSERT INTO trabajador_detalle(trabajador_id,'+','.join(names)+') VALUES('+','.join(['%s']*(len(names)+1))+')'
            sql+=' ON DUPLICATE KEY UPDATE '+','.join(n+'=VALUES('+n+')' for n in names)
            try:db.execute(sql,(trab,*params))
            except Exception as e:QMessageBox.critical(dlg,'No se pudo guardar',str(e));return
            autorizado['cerrar']=True
            dlg.accept()
        dlg.findChild(QPushButton,'btnDetalleGuardar').clicked.connect(guardar)
        dlg.exec()

    def vista_cedula(self):
        datos=self._datos_cedulas()
        primero=datos[0]
        muestra='\n'.join(f"• {d['numero_ficha']} — {d['nombre_completo']}" for d in datos[:30])
        if len(datos)>30:muestra+=f"\n... y {len(datos)-30} trabajador(es) más."
        QMessageBox.information(self.ui,'Cédulas del evento',
            f"Evento: {primero['evento']}\nClave: {primero['clave_evento']}\n"
            f"Participantes activos: {len(datos)}\n\n{muestra}\n\n"
            'Se producirá un único PDF con una página por trabajador.')

    @staticmethod
    def _pagina_cedula(c,d):
        # Página individual de cédula dentro del PDF conjunto.
        from reportlab.lib.pagesizes import A4
        w,h=A4
        c.setFont('Helvetica-Bold',13)
        c.drawCentredString(w/2,h-43,'Petróleos Mexicanos y Empresas Productivas Subsidiarias')
        c.setFont('Helvetica-Bold',11)
        c.drawCentredString(w/2,h-62,'Cédula de Registro de Información del Trabajador')
        c.line(38,h-73,w-38,h-73)
        campos=[
          ('Ficha',d['numero_ficha']),('CURP',d['curp']),
          ('Nombre(s)',d['nombres'] or d['nombre_completo']),
          ('Apellido paterno',d['apellido_paterno']),('Apellido materno',d['apellido_materno']),
          ('Nombre del evento',d['evento']),('Clave del evento',d['clave_evento']),
          ('Duración en horas',d['duracion_horas']),('Fecha de inicio',d['fecha_inicio']),
          ('Fecha de término',d['fecha_fin']),('Centro de trabajo',d['centro_trabajo']),
          ('Clave del centro de trabajo',d['clave_centro_trabajo']),('Subsidiaria',d['subsidiaria']),
          ('Gerencia',d['gerencia']),('Departamento',d['departamento']),
          ('Clave del departamento',d['clave_departamento']),('Categoría base',d['categoria_base']),
          ('Nivel',d['nivel']),('Turno',d['turno']),('Tipo de plaza',d['tipo_plaza']),
          ('Jefe inmediato',d['jefe_inmediato']),('Extensión',d['extension']),
          ('Entidad federativa',d['entidad_federativa']),('Municipio',d['municipio']),
          ('Máximo de estudios',d['nivel_estudios']),('Carrera o estudio',d['carrera']),
          ('Documento probatorio',d['documento_probatorio']),('Año del documento',d['anio_documento']),
          ('Institución',d['institucion_tipo']),('Discapacidad',d['discapacidad']),
          ('Estado civil',d['estado_civil']),('Hijos dependientes',d['hijos_dependientes'])
        ]
        y=h-98
        for nombre,valor in campos:
            c.setFont('Helvetica-Bold',8.1);c.drawString(40,y,nombre+':')
            c.setFont('Helvetica',8.5)
            v='' if valor is None else str(valor)
            c.drawString(205,y,v[:58]);c.line(205,y-3,w-40,y-3)
            y-=19
        c.setFont('Helvetica',9);c.drawString(40,y-28,'Firma:')
        c.line(155,y-30,w-50,y-30)
        c.setFont('Helvetica-Oblique',7.5)
        c.drawString(40,y-58,'Documento para revisión, impresión y firma del trabajador.')
        c.showPage()

    def generar_cedula(self):
        if not self._requiere('cedula'):return
        datos=self._datos_cedulas()
        primero=datos[0]
        if not primero['clave_evento'] or not primero['duracion_horas']:
            raise ValueError('Completa la clave y duración del evento antes de generar sus cédulas.')
        if QMessageBox.question(self.ui,'Generar cédulas del evento',
            f"¿Generar las {len(datos)} cédulas de '{primero['evento']}' en un solo PDF?",
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
            return
        from uuid import uuid4
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        carpeta=RAIZ/'salidas'/'cedulas';carpeta.mkdir(parents=True,exist_ok=True)
        lote=str(uuid4())
        archivo=f"cedulas_evento_{primero['clave_evento']}_{datetime.now():%Y%m%d_%H%M%S}_{lote[:8]}.pdf"
        ruta=carpeta/archivo
        c=canvas.Canvas(str(ruta),pagesize=A4)
        try:
            for d in datos:self._pagina_cedula(c,d)
            c.save()
            with db.connection() as conn:
                cur=conn.cursor()
                try:
                    for d in datos:
                        cur.execute('''INSERT INTO cedulas_generadas(
                            inscripcion_id,usuario_id,tipo_generacion,lote_id,nombre_archivo,ruta_relativa_pdf)
                            VALUES(%s,%s,'MASIVA',%s,%s,%s)''',
                            (d['inscripcion_id'],self.usuario['id'],lote,archivo,
                             str(Path('salidas')/'cedulas'/archivo).replace('\\','/')))
                    conn.commit()
                except Exception:
                    conn.rollback();raise
                finally:cur.close()
        except Exception:
            ruta.unlink(missing_ok=True)
            raise
        self._w('lblEstadoCedula').setText(
            f'{len(datos)} cédulas generadas para el evento {primero["clave_evento"]}.')
        QMessageBox.information(self.ui,'Cédulas generadas',
            f'Se generaron {len(datos)} páginas en un único PDF:\n{ruta}')
