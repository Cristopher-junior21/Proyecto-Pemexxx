"""Reportes con filtros encadenados, visualización y PDF."""
from collections import Counter
from datetime import datetime
from pathlib import Path
from PySide6.QtGui import QPixmap,QPainter,QColor,QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog,QMessageBox
from database import conexion as db


class ReportesMixin:
    def preparar_reportes(self):
        for n,opciones in (
          ('cmbReporteTipo',[('Todos',None)]),
          ('cmbReporteModalidad',[('Todas',None),('Presencial','PRESENCIAL'),('En línea','EN_LINEA')]),
          ('cmbReporteClasificacion',[('Todas',None),('Contractual','CONTRACTUAL'),('Confianza','CONFIANZA'),('Ascenso','ASCENSO')]),
          ('cmbReporteEstado',[('Todos',None),('PROGRAMADO','PROGRAMADO'),('En curso','EN_CURSO'),('Finalizado','FINALIZADO'),('Cancelado','CANCELADO')]),
        ):
            cb=self._w(n);cb.clear()
            for nombre,valor in opciones:cb.addItem(nombre,valor)
        for r in db.fetchall('SELECT id,nombre FROM tipos_curso ORDER BY nombre'):
            self._w('cmbReporteTipo').addItem(r['nombre'],r['id'])
        for n in ('cmbReporteAnio','cmbReporteTipo','cmbReporteModalidad','cmbReporteClasificacion','cmbReporteEstado'):
            self._w(n).currentIndexChanged.connect(lambda _=None:self._safe(self.generar_reporte))
        cb=self._w('cmbReporteAgrupar')
        for text,field in [('Por tipo','tipo'),('Por modalidad','modalidad'),
                           ('Por clasificación','clasificacion_evento'),('Por estado','estado')]:
            cb.addItem(text,field)
        cb.currentIndexChanged.connect(lambda _=None:self._dibujar_grafico())
        self.datos_reporte=[]
        self._w('lblGraficoReportes').setScaledContents(True)

    def limpiar_filtros_reporte(self):
        for n in ('cmbReporteTipo','cmbReporteModalidad','cmbReporteClasificacion','cmbReporteEstado'):
            self._w(n).setCurrentIndex(0)
        self._w('cmbReporteAnio').setCurrentIndex(max(0,self._w('cmbReporteAnio').findData(self.anio)))
        self.generar_reporte()

    def generar_reporte(self):
        anio=self._w('cmbReporteAnio').currentData() or self.anio
        tipo=self._w('cmbReporteTipo').currentData()
        modalidad=self._w('cmbReporteModalidad').currentData()
        clasificacion=self._w('cmbReporteClasificacion').currentData()
        estado=self._w('cmbReporteEstado').currentData()
        sql='''SELECT c.id,c.clave_evento,c.nombre,tc.nombre AS tipo,c.modalidad,
          c.clasificacion_evento,c.fecha_inicio,c.fecha_fin,c.duracion_horas,c.estado,
          SUM(CASE WHEN i.estado='INSCRITO' THEN 1 ELSE 0 END) AS participantes
          FROM cursos c LEFT JOIN tipos_curso tc ON tc.id=c.tipo_curso_id
          LEFT JOIN inscripciones i ON i.curso_id=c.id
          WHERE YEAR(c.fecha_inicio)=%s'''
        args=[anio]
        for columna,valor in (('c.tipo_curso_id',tipo),('c.modalidad',modalidad),
                              ('c.clasificacion_evento',clasificacion),('c.estado',estado)):
            if valor is not None:sql+=' AND '+columna+'=%s';args.append(valor)
        sql+=' GROUP BY c.id,c.clave_evento,c.nombre,tc.nombre,c.modalidad,c.clasificacion_evento,c.fecha_inicio,c.fecha_fin,c.duracion_horas,c.estado ORDER BY c.fecha_inicio,c.nombre'
        self.datos_reporte=db.fetchall(sql,tuple(args))
        cols=('id','clave_evento','nombre','tipo','modalidad','clasificacion_evento','fecha_inicio','estado','participantes')
        self._cargar_tabla('tablaReportes',[tuple(r.get(c) or (0 if c=='participantes' else '—') for c in cols) for r in self.datos_reporte])
        t=len(self.datos_reporte)
        participantes=sum(int(x['participantes'] or 0) for x in self.datos_reporte)
        horas_contractuales=sum(float(x['duracion_horas'] or 0) for x in self.datos_reporte
                                if x['clasificacion_evento']=='CONTRACTUAL')
        self._w('lblReporteResumen').setText(
            f'Año {anio} · Eventos: {t} · Inscripciones: {participantes} · Horas contractuales: {horas_contractuales:g}')
        self._dibujar_grafico()

    def _dibujar_grafico(self):
        """Gráfico simple QPainter, sin dependencias de librerías externas."""
        pix=QPixmap(830,220);pix.fill(QColor('#FFFFFF'))
        p=QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont('Segoe UI',11))
        agrupar=self._w('cmbReporteAgrupar').currentData() or 'tipo'
        conteos=Counter((r.get(agrupar) or 'Sin clasificar') for r in self.datos_reporte)
        elementos=sorted(conteos.items(),key=lambda x:x[0])
        p.setPen(QColor('#1F4050'));p.drawText(18,26,'Distribución por '+self._w('cmbReporteAgrupar').currentText()+' · filtros activos')
        if not elementos:p.drawText(22,115,'Sin resultados para los filtros seleccionados.');p.end();self._w('lblGraficoReportes').setPixmap(pix);return
        maximo=max(conteos.values())
        for idx,(tipo,cantidad) in enumerate(elementos[:5]):
            y=60+idx*31
            p.setPen(QColor('#3F5965'));p.drawText(20,y,tipo[:21])
            p.fillRect(210,y-18,round(480*cantidad/maximo),20,QColor('#32A77D'))
            p.setPen(QColor('#153E3B'));p.drawText(730,y,str(cantidad))
        p.end();self._w('lblGraficoReportes').setPixmap(pix)

    def exportar_reporte_pdf(self):
        if not self._requiere('reporte'):return
        if not self.datos_reporte:raise ValueError('No hay eventos para exportar con los filtros elegidos.')
        from reportlab.lib.pagesizes import landscape,A4
        from reportlab.pdfgen import canvas
        ruta,_=QFileDialog.getSaveFileName(self.ui,'Guardar reporte','reporte_eventos.pdf','PDF (*.pdf)')
        if not ruta:return
        c=canvas.Canvas(ruta,pagesize=landscape(A4)); w,h=landscape(A4)
        y=h-48
        def cabecera():
            nonlocal y
            c.setFont('Helvetica-Bold',15);c.drawString(42,h-40,'Sistema de Capacitación Cangrejera · Reporte de eventos')
            c.setFont('Helvetica',9);c.drawString(42,h-60,self._w('lblReporteResumen').text())
            y=h-89
        cabecera()
        for r in self.datos_reporte:
            if y<60:c.showPage();cabecera()
            c.setFont('Helvetica',9)
            descripcion=f"{r['clave_evento'] or 'Sin clave'} | {str(r['nombre'])[:45]} | {r['tipo'] or '-'} | {r['estado']} | {r['participantes']} inscritos"
            c.drawString(42,y,descripcion);y-=20
        c.save()
        QMessageBox.information(self.ui,'Reporte exportado','PDF guardado correctamente.')
