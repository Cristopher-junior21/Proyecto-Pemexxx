"""Controlador del panel: componentes editables en ui/main.ui."""
from datetime import date
from pathlib import Path
import mysql.connector
from PySide6.QtCore import QFile,QObject,Qt,QTimer,QEvent
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QAbstractItemView,QHeaderView,QMessageBox,QTableWidgetItem,QLineEdit
from database import conexion as db
from logica.reglas import tiene_permiso
from logica.identidad_visual import aplicar_marca
from logica.trabajadores import TrabajadoresMixin
from logica.cursos import CursosMixin
from logica.inscripciones import InscripcionesMixin
from logica.cedulas import CedulasMixin
from logica.reportes import ReportesMixin
from logica.usuarios import UsuariosMixin
from logica.tablas_ui import instalar_ajustador, reajustar_tabla

BASE_DIR=Path(__file__).resolve().parent.parent
PAGINAS=(
 ('Inicio','Panel de control','Resumen de la gestión de capacitación'),
 ('Trabajadores','Trabajadores','Registro y consulta de personal'),
 ('Cursos','Eventos','Programación de eventos de capacitación'),
 ('Inscripciones','Inscripciones','Participantes y asignación a eventos'),
 ('Cedulas','Cédulas','Registro de información del trabajador'),
 ('Reportes','Reportes','Filtros, visualizaciones y exportación'),
 ('Usuarios','Usuarios','Administración de cuentas y respaldos'),
)


class ProtegerCierrePrincipal(QObject):
    """Pide confirmación al cerrar si quedan formularios incompletos."""
    def __init__(self,controlador):
        super().__init__(controlador.ui)
        self.controlador=controlador

    def eventFilter(self,obj,event):
        if event.type()==QEvent.Close:
            for tipo in ('trabajador','evento','inscripcion','usuario'):
                if not self.controlador._confirmar_descartar(tipo):
                    event.ignore()
                    return True
        return super().eventFilter(obj,event)


class SistemaCapacitacion(TrabajadoresMixin,CursosMixin,InscripcionesMixin,
                          CedulasMixin,ReportesMixin,UsuariosMixin):
    def __init__(self,usuario):
        self.usuario=usuario
        if usuario['rol'] not in ('ADMIN','CAPTURA','CONSULTA'):
            raise PermissionError('El usuario no tiene un rol válido.')
        self.anio=date.today().year
        ruta=QFile(str(BASE_DIR/'ui'/'main.ui'))
        if not ruta.open(QFile.ReadOnly):raise FileNotFoundError('No se encontró ui/main.ui')
        self.ui=QUiLoader().load(ruta);ruta.close()
        if self.ui is None:raise RuntimeError('No se pudo cargar ui/main.ui')
        self.ui.setStyleSheet((BASE_DIR/'ui'/'style.qss').read_text(encoding='utf-8'))
        aplicar_marca(self.ui, 'principal')
        self.trabajador_id=None;self.curso_id=None
        self._firmas={}
        self._ultima_pagina=0
        self._ultimo_anio_real=self.anio
        self._preparar_tablas()
        self._preparar_anios()
        self._configurar_eventos()
        self._preparar_navegacion()
        self._safe(self.preparar_reportes)
        self._aplicar_permisos()
        if self.usuario['rol']=='ADMIN':self.cargar_roles()
        self._guardar_firma_formulario('usuario')
        self._guardar_firma_formulario('inscripcion')
        self.nuevo_trabajador(preguntar=False);self.nuevo_curso(preguntar=False)
        self._pagina_cambiada(0)
        self._temporizador=QTimer(self.ui)
        self._temporizador.setInterval(60_000)
        self._temporizador.timeout.connect(lambda:self._safe(self._actualizacion_periodica))
        self._temporizador.start()
        self._proteccion_cierre=ProtegerCierrePrincipal(self)
        self.ui.installEventFilter(self._proteccion_cierre)

    def _w(self,nombre):
        w=self.ui.findChild(QObject,nombre)
        if w is None:raise RuntimeError(f'Falta {nombre} en ui/main.ui')
        return w

    def _valores_formulario(self, tipo):
        """Firma de datos editables, sin depender de señales ni del orden de widgets."""
        nombres = (
          ('txtFicha','txtNombre','txtPuesto','txtDepartamento') if tipo=='trabajador'
          else ('txtUsuarioNombre','txtUsuarioLogin','txtUsuarioClave','cmbUsuarioRol') if tipo=='usuario'
          else ('cmbTrabajador','cmbCurso') if tipo=='inscripcion'
          else ('txtClaveEvento','txtCursoNombre','cmbCursoTipo','cmbCursoModalidad',
                'cmbClasificacionEvento','fechaCursoInicio','fechaCursoFin',
                'horaCursoInicio','horaCursoFin','txtDuracionHoras','txtCursoLugar',
                'txtCursoEnlaceVirtual','txtCursoInstructor')
        )
        resultado=[]
        for nombre in nombres:
            w=self._w(nombre)
            if hasattr(w,'text'):v=w.text()
            elif hasattr(w,'currentData'):v=w.currentData()
            elif hasattr(w,'date'):v=w.date().toString('yyyy-MM-dd')
            elif hasattr(w,'time'):v=w.time().toString('HH:mm')
            else:v=None
            resultado.append((nombre,str(v)))
        return tuple(resultado)

    def _guardar_firma_formulario(self,tipo):
        self._firmas[tipo]=self._valores_formulario(tipo)

    def _confirmar_descartar(self,tipo):
        anterior=self._firmas.get(tipo)
        if anterior is None or anterior==self._valores_formulario(tipo):
            return True
        titulo={'trabajador':'trabajador','evento':'evento','usuario':'usuario','inscripcion':'inscripción'}.get(tipo,tipo)
        return QMessageBox.question(
            self.ui,'Cambios sin guardar',
            f'Hay datos del {titulo} sin guardar. ¿Descartarlos y continuar?',
            QMessageBox.Yes | QMessageBox.No,QMessageBox.No)==QMessageBox.Yes

    def _descartar_cambios_pagina(self,indice):
        tipo={1:'trabajador',2:'evento',3:'inscripcion',6:'usuario'}.get(indice)
        if tipo and not self._confirmar_descartar(tipo):return False
        if tipo=='trabajador':self.nuevo_trabajador(preguntar=False)
        if tipo=='evento':self.nuevo_curso(preguntar=False)
        if tipo=='usuario':
            for nombre in ('txtUsuarioNombre','txtUsuarioLogin','txtUsuarioClave'):
                self._w(nombre).clear()
            self._guardar_firma_formulario('usuario')
        if tipo=='inscripcion':
            self._w('cmbTrabajador').setCurrentIndex(0)
            self._w('cmbCurso').setCurrentIndex(0)
            self._guardar_firma_formulario('inscripcion')
        return True

    def _restaurar_seleccion_tabla(self,nombre,identificador):
        tabla=self._w(nombre)
        tabla.blockSignals(True)
        try:
            if identificador is None:
                tabla.clearSelection()
                tabla.setCurrentCell(-1,-1)
            else:
                for fila in range(tabla.rowCount()):
                    it=tabla.item(fila,0)
                    if it is not None and it.text()==str(identificador):
                        tabla.selectRow(fila)
                        break
        finally:tabla.blockSignals(False)

    def _sincronizar_estados(self):
        """Actualización en BD al abrir/refrescar; requiere servidor en hora local correcta."""
        db.execute("""UPDATE cursos SET estado=CASE
            WHEN NOW() < TIMESTAMP(fecha_inicio,COALESCE(hora_inicio,'00:00:00'))
              THEN 'PROGRAMADO'
            WHEN NOW() >= TIMESTAMP(fecha_fin,COALESCE(hora_fin,'23:59:59'))
              THEN 'FINALIZADO'
            ELSE 'EN_CURSO' END
            WHERE estado<>'CANCELADO' AND estado<>CASE
            WHEN NOW() < TIMESTAMP(fecha_inicio,COALESCE(hora_inicio,'00:00:00'))
              THEN 'PROGRAMADO'
            WHEN NOW() >= TIMESTAMP(fecha_fin,COALESCE(hora_fin,'23:59:59'))
              THEN 'FINALIZADO'
            ELSE 'EN_CURSO' END""")

    def _requiere(self,operacion):
        if tiene_permiso(self.usuario['rol'],operacion):return True
        QMessageBox.warning(self.ui,'Permiso denegado','Tu perfil no tiene permiso para esta operación.')
        return False

    def _safe(self,fn):
        try:return fn()
        except ValueError as exc:
            QMessageBox.warning(self.ui,'Revisa los datos',str(exc))
        except mysql.connector.Error as exc:
            cod=exc.errno
            mensaje={1045:'Credenciales MySQL incorrectas. Revisa .env.',
                     1049:'La base de datos no existe.',
                     1062:'La clave o ficha ya existe. Usa un identificador diferente.',
                     1452:'Uno de los elementos seleccionados ya no existe.',
                     3819:'El valor no cumple una restricción de la base de datos.',
                     2003:'No se pudo conectar al servidor MySQL.',
                     2005:'Servidor MySQL desconocido.'}.get(cod,
                       f'No se pudo realizar la operación. MySQL {cod}: {exc.msg}')
            QMessageBox.warning(self.ui,'Error en la base de datos',mensaje)
        except (OSError,ImportError,RuntimeError) as exc:
            QMessageBox.critical(self.ui,'Error de ejecución',str(exc))
        except Exception as exc:
            QMessageBox.critical(self.ui,'Error inesperado',str(exc))

    def _tabla(self,nombre,encabezados,oculta_id=True):
        t=self._w(nombre)
        t.setColumnCount(len(encabezados));t.setHorizontalHeaderLabels(encabezados)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setAlternatingRowColors(True);t.setShowGrid(False)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setStretchLastSection(False)
        t.setColumnHidden(0,oculta_id)
        instalar_ajustador(t,nombre)

    def _preparar_tablas(self):
        self._tabla('tablaTrabajadores',['ID','Ficha','Nombre','Puesto','Departamento','Estado'])
        self._tabla('tablaCursos',['ID','Clave','Evento','Tipo','Clasificación','Modalidad',
                    'Inicio','Fin','Horas','Instructor','Estado'])
        self._tabla('tablaInscripciones',['ID','Ficha','Trabajador','Evento','Registro','Estado'])
        self._tabla('tablaReportes',['ID','Clave','Evento','Tipo','Modalidad','Clasificación',
                    'Inicio','Estado','Inscritos'])
        self._tabla('tablaUsuarios',['ID','Nombre','Usuario','Rol','Estado'])
        self._tabla('tablaProximosCursos',['Evento','Fecha','Tipo','Modalidad'],oculta_id=False)
        # El ajuste proporcional también se aplica a próximos eventos.

    def _cargar_tabla(self,nombre,filas,oculta_id=True):
        t=self._w(nombre);t.blockSignals(True)
        try:
            t.setRowCount(len(filas))
            for i,fila in enumerate(filas):
                for j,v in enumerate(fila):
                    q=QTableWidgetItem('' if v is None else str(v))
                    q.setFlags(q.flags() & ~Qt.ItemIsEditable)
                    t.setItem(i,j,q)
            t.setColumnHidden(0,oculta_id)
            reajustar_tabla(t)
        finally:t.blockSignals(False)

    def _seleccionado(self,nombre):
        t=self._w(nombre);row=t.currentRow()
        if row<0 or t.item(row,0) is None:return None
        return int(t.item(row,0).text())

    def _preparar_anios(self):
        rows=db.fetchall('SELECT DISTINCT YEAR(fecha_inicio) AS anio FROM cursos ORDER BY anio')
        actual=date.today().year
        anios=sorted(set(list(range(actual-10,actual+1))+
            [int(r['anio']) for r in rows if r['anio'] and int(r['anio'])<=actual]))
        for n in ('cmbAnioActivo','cmbReporteAnio'):
            cb=self._w(n)
            cb.blockSignals(True)
            try:
                actual=cb.currentData()
                cb.clear()
                for yr in anios:cb.addItem(str(yr),yr)
                vigente=actual if actual in anios else self.anio
                cb.setCurrentIndex(cb.findData(vigente))
            finally:cb.blockSignals(False)
        self._w('cmbAnioActivo').currentIndexChanged.connect(self._cambio_anio)

    def _cambio_anio(self,_=None):
        selected=self._w('cmbAnioActivo').currentData()
        if selected is None:return
        if selected > date.today().year:
            QMessageBox.warning(self.ui,'Año no disponible','No se puede consultar un año que aún no ha comenzado.')
            cb=self._w('cmbAnioActivo');cb.blockSignals(True)
            cb.setCurrentIndex(cb.findData(self.anio));cb.blockSignals(False)
            return
        if selected!=self.anio and not self._confirmar_descartar('evento'):
            cb=self._w('cmbAnioActivo');cb.blockSignals(True)
            cb.setCurrentIndex(cb.findData(self.anio));cb.blockSignals(False)
            return
        self.anio=selected
        self.ui.setWindowTitle(f'Sistema de Capacitación Cangrejera — {self.anio}')
        self._w('lblTituloAnio').setText(f'Sistema de Capacitación Cangrejera — {self.anio}')
        self._w('heroTitle').setText(f'Eventos de capacitación · {self.anio}')
        self._w('cmbReporteAnio').setCurrentIndex(max(0,self._w('cmbReporteAnio').findData(self.anio)))
        self.nuevo_curso(preguntar=False)
        self._w('lblEncabezado').setText(f'{PAGINAS[self._w("tabsPrincipal").currentIndex()][1]} · {self.anio}')
        self._safe(self.actualizar_todo)

    def _preparar_navegacion(self):
        tab=self._w('tabsPrincipal');tab.tabBar().hide()
        self.ui.statusBar().hide()
        self._w('lblContadores').hide()
        # El nombre del módulo ya aparece en el encabezado común.
        for titulo in ('titleTrabajadores','titleCursos','titleInscripciones',
                       'titleCedulas','titleReportes','titleUsuarios'):
            self._w(titulo).hide()
        self._w('lblFechaHoy').setText(date.today().strftime('%d/%m/%Y'))
        for i,(nombre,_,_) in enumerate(PAGINAS):
            boton=self._w('btnNav'+nombre)
            boton.setProperty('nav',True)
            boton.style().unpolish(boton);boton.style().polish(boton)
            boton.clicked.connect(lambda checked=False,j=i:tab.setCurrentIndex(j))
        tab.currentChanged.connect(self._pagina_cambiada)
        self._w('btnAccesoTrabajador').clicked.connect(lambda:tab.setCurrentIndex(1))
        self._w('btnAccesoCurso').clicked.connect(lambda:tab.setCurrentIndex(2))
        self._w('btnRefrescarPanel').clicked.connect(lambda:self._safe(self.actualizar_todo))
        self._w('lblTituloAnio').setText(f'Sistema de Capacitación Cangrejera — {self.anio}')
        self.ui.setWindowTitle(f'Sistema de Capacitación Cangrejera — {self.anio}')

    def _pagina_cambiada(self,indice):
        if not (0<=indice<len(PAGINAS)):return
        anterior=self._ultima_pagina
        if indice!=anterior and not self._descartar_cambios_pagina(anterior):
            tab=self._w('tabsPrincipal')
            tab.blockSignals(True);tab.setCurrentIndex(anterior);tab.blockSignals(False)
            return
        self._ultima_pagina=indice
        for i,(name,_,_) in enumerate(PAGINAS):
            self._w('btnNav'+name).setChecked(i==indice)
        self._w('lblEncabezado').setText(f'{PAGINAS[indice][1]} · {self.anio}')
        self._w('lblSubEncabezado').setText(PAGINAS[indice][2])
        self._safe(self.actualizar_todo)

    def _configurar_eventos(self):
        for name,fn in {
            'btnTrabGuardar':self.guardar_trabajador,'btnTrabNuevo':self.nuevo_trabajador,
            'btnTrabDesactivar':lambda:self.cambiar_estado_trabajador(0),
            'btnTrabReactivar':lambda:self.cambiar_estado_trabajador(1),
            'btnTrabDetalle':self.abrir_detalle,
            'btnCursoGuardar':self.guardar_curso,'btnCursoNuevo':self.nuevo_curso,
            'btnCursoCancelar':self.cancelar_curso,
            'btnInscribir':self.inscribir,'btnDarBaja':self.baja_inscripcion,
            'btnRegistrarAscenso':self.registrar_ascenso,
            'btnActualizar':self.actualizar_todo,
            'btnCedulaVista':self.vista_cedula,'btnDetalleTrabajador':lambda:self._w('tabsPrincipal').setCurrentIndex(1),
            'btnCedulaGenerar':self.generar_cedula,
            'btnReporteFiltrar':self.generar_reporte,'btnReporteLimpiar':self.limpiar_filtros_reporte,
            'btnReportePdf':self.exportar_reporte_pdf,
            'btnUsuarioGuardar':self.crear_usuario,
            'btnUsuarioActivar':lambda:self.estado_usuario(1),
            'btnUsuarioDesactivar':lambda:self.estado_usuario(0),
            'btnRespaldo':self.respaldo,
        }.items():
            self._w(name).clicked.connect(lambda checked=False,f=fn:self._safe(f))
        self._w('txtBuscarTrabajador').textChanged.connect(lambda _=None:self._safe(self.cargar_trabajadores))
        self._w('txtBuscarCurso').textChanged.connect(lambda _=None:self._safe(self.cargar_cursos))
        self._w('tablaTrabajadores').itemSelectionChanged.connect(lambda:self._safe(self.editar_trabajador_seleccionado))
        self._w('tablaCursos').itemSelectionChanged.connect(lambda:self._safe(self.editar_curso_seleccionado))
        for w in ('fechaCursoInicio','fechaCursoFin'):
            self._w(w).dateChanged.connect(lambda _=None:self._actualizar_resumen_horas())
        for w in ('horaCursoInicio','horaCursoFin'):
            self._w(w).timeChanged.connect(lambda _=None:self._actualizar_resumen_horas())
        cb=self._w('cmbCursoModalidad')
        for text,data in [('Seleccionar modalidad',None),('Presencial','PRESENCIAL'),('En línea','EN_LINEA')]:
            cb.addItem(text,data)
        cb.currentIndexChanged.connect(lambda _=None:self.actualizar_campos_modalidad())
        cb=self._w('cmbClasificacionEvento')
        for text,data in [('Seleccionar clasificación',None),('Contractual','CONTRACTUAL'),
                          ('Confianza','CONFIANZA'),('Ascenso','ASCENSO')]:cb.addItem(text,data)
        # Duración generada a partir de fechas y horas; nunca ingresada manualmente.
        self._w('txtDuracionHoras').setReadOnly(True)
        self._w('txtDuracionHoras').setFocusPolicy(Qt.NoFocus)
        self._w('txtClaveEvento').setMaxLength(8)
        self._w('txtUsuarioClave').setEchoMode(QLineEdit.Password)
        self._w('txtUsuarioClave').setMaxLength(255)

    def _aplicar_permisos(self):
        rol=self.usuario['rol'];edita=tiene_permiso(rol,'captura');admin=rol=='ADMIN'
        self._w('btnNavUsuarios').setVisible(admin)
        for name in ('btnTrabGuardar','btnTrabNuevo','btnTrabDesactivar','btnTrabReactivar',
                     'btnTrabDetalle','btnCursoGuardar','btnCursoNuevo','btnCursoCancelar',
                     'btnInscribir','btnDarBaja','btnRegistrarAscenso','btnCedulaGenerar','btnCedulaVista','btnDetalleTrabajador'):
            self._w(name).setEnabled(edita)
        for name in ('txtFicha','txtNombre','txtPuesto','txtDepartamento','txtClaveEvento',
                     'txtCursoNombre','txtCursoLugar','txtCursoEnlaceVirtual','txtCursoInstructor','txtDuracionHoras',
                     'cmbCursoTipo','cmbCursoModalidad','cmbClasificacionEvento',
                     'fechaCursoInicio','fechaCursoFin','horaCursoInicio','horaCursoFin'):
            self._w(name).setReadOnly(True) if hasattr(self._w(name),'setReadOnly') and not edita else None
            if not edita:self._w(name).setEnabled(False)
        self._w('btnAccesoTrabajador').setEnabled(edita)
        self._w('btnAccesoCurso').setEnabled(edita)
        if not admin and self._w('tabsPrincipal').currentIndex()==6:
            self._w('tabsPrincipal').setCurrentIndex(0)

    def _actualizacion_periodica(self):
        actual=date.today().year
        if actual!=self._ultimo_anio_real:
            self._ultimo_anio_real=actual
            self._preparar_anios()
        self.actualizar_todo()

    def actualizar_todo(self):
        db.test_connection()
        self._sincronizar_estados()
        self._w('lblEstado').setText('Base de datos conectada')
        self.cargar_trabajadores();self.cargar_tipos_curso();self.cargar_cursos()
        self.cargar_inscripciones();self.cargar_opciones_inscripcion()
        self.cargar_resumen();self.cargar_proximos_cursos();self.cargar_opciones_cedula()
        if hasattr(self,'datos_reporte'):self.generar_reporte()
        if self.usuario['rol']=='ADMIN':self.cargar_usuarios()

    def cargar_resumen(self):
        r=db.fetchall('''SELECT
          (SELECT COUNT(*) FROM trabajadores WHERE activo=1) AS trabajadores,
          (SELECT COUNT(*) FROM cursos WHERE estado<>'CANCELADO' AND YEAR(fecha_inicio)=%s) AS eventos,
          (SELECT COUNT(*) FROM inscripciones i JOIN cursos c ON c.id=i.curso_id
           WHERE i.estado='INSCRITO' AND YEAR(c.fecha_inicio)=%s) AS inscritos''',(self.anio,self.anio))[0]
        for n,v in [('valorTrabajadores',r['trabajadores']),('valorCursos',r['eventos']),
                    ('valorInscripciones',r['inscritos'])]:self._w(n).setText(str(v))

    def cargar_proximos_cursos(self):
        rows=db.fetchall('''SELECT c.nombre,c.fecha_inicio,tc.nombre AS tipo,c.modalidad
          FROM cursos c LEFT JOIN tipos_curso tc ON tc.id=c.tipo_curso_id
          WHERE YEAR(c.fecha_inicio)=%s AND c.estado IN ('PROGRAMADO','EN_CURSO')
            AND c.fecha_fin>=CURDATE() ORDER BY c.fecha_inicio ASC LIMIT 6''',(self.anio,))
        self._cargar_tabla('tablaProximosCursos',[(r['nombre'],r['fecha_inicio'],r['tipo'] or '—',
                     r['modalidad'] or '—') for r in rows],oculta_id=False)
        self._w('subProximos').setText('Eventos programados' if rows else 'No hay eventos próximos para este año')

    def show(self):self.ui.show()
