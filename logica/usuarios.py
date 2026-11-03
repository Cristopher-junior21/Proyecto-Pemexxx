"""Gestión de cuentas y respaldo, disponible exclusivamente para ADMIN."""
from pathlib import Path
from datetime import datetime
from tempfile import NamedTemporaryFile
import os
import shutil
import subprocess
import mysql.connector
from argon2 import PasswordHasher
from PySide6.QtWidgets import QMessageBox, QFileDialog
from database import conexion as db


class UsuariosMixin:
    def cargar_roles(self):
        cb=self._w('cmbUsuarioRol'); cb.clear()
        for r in db.fetchall('SELECT id,codigo,nombre FROM roles ORDER BY id'):
            cb.addItem(r['nombre'],r['id'])

    def cargar_usuarios(self):
        if self.usuario['rol']!='ADMIN':return
        datos=db.fetchall('''SELECT u.id,u.nombre_completo,u.nombre_usuario,
          COALESCE(r.nombre,'Sin asignar') AS rol, u.activo
          FROM usuarios u LEFT JOIN roles r ON r.id=u.rol_id ORDER BY u.id''')
        self._cargar_tabla('tablaUsuarios',[(x['id'],x['nombre_completo'],x['nombre_usuario'],x['rol'],
             'Activo' if x['activo'] else 'Desactivado') for x in datos])

    def crear_usuario(self):
        if not self._requiere('admin'):return
        nombre=self._w('txtUsuarioNombre').text().strip()
        cuenta=self._w('txtUsuarioLogin').text().strip()
        password=self._w('txtUsuarioClave').text()
        rol=self._w('cmbUsuarioRol').currentData()
        if not nombre or not cuenta or not rol:
            raise ValueError('Completa nombre, cuenta y rol.')
        if len(password)<12:raise ValueError('La contraseña debe tener al menos 12 caracteres.')
        if len(nombre)>160 or len(cuenta)>60:raise ValueError('Nombre o usuario demasiado largo.')
        db.execute('''INSERT INTO usuarios(nombre_completo,nombre_usuario,password_hash,rol_id,activo)
           VALUES(%s,%s,%s,%s,1)''',(nombre,cuenta,PasswordHasher().hash(password),rol))
        for nm in ('txtUsuarioNombre','txtUsuarioLogin','txtUsuarioClave'):
            self._w(nm).clear()
        self.cargar_usuarios()
        QMessageBox.information(self.ui,'Usuario creado','Cuenta creada con contraseña protegida.')

    def estado_usuario(self,activo):
        if not self._requiere('admin'):return
        uid=self._seleccionado('tablaUsuarios')
        if uid is None:raise ValueError('Selecciona un usuario de la tabla.')
        if uid==self.usuario['id'] and not activo:
            raise ValueError('No puedes desactivar tu propia sesión.')
        if QMessageBox.question(self.ui,'Confirmación','¿Cambiar el estado de esta cuenta?')!=QMessageBox.Yes:return
        db.execute('UPDATE usuarios SET activo=%s WHERE id=%s',(activo,uid))
        self.cargar_usuarios()

    def respaldo(self):
        if not self._requiere('admin'):return
        ruta,_=QFileDialog.getSaveFileName(self.ui,'Guardar respaldo de MySQL',
          f'respaldo_cangrejera_{datetime.now():%Y%m%d_%H%M}.sql','SQL (*.sql)')
        if not ruta:return
        destino=Path(ruta)
        if destino.exists():
            raise ValueError('El archivo ya existe. Elige otro nombre para no sobrescribir respaldos anteriores.')
        exe=shutil.which('mysqldump') or r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe'
        if not Path(exe).is_file():
            raise ValueError('No encuentro mysqldump.exe. Comprueba la instalación de MySQL Server.')
        cfg=db._config()
        # Archivo temporal de opciones: contraseña fuera de argumentos/comandos.
        with NamedTemporaryFile(mode='w',suffix='.cnf',encoding='utf-8',delete=False) as cfg_file:
            archivo_cfg=Path(cfg_file.name)
            cfg_file.write('[client]\n')
            for llave,valor in (('host',cfg['host']),('port',cfg['port']),('user',cfg['user']),('password',cfg['password'])):
                safe=str(valor).replace('\\','\\\\').replace('"','\\"').replace('\n','')
                cfg_file.write(f'{llave}="{safe}"\n')
        try:
            os.chmod(archivo_cfg,0o600)
            # --defaults-extra-file DEBE ser el primer argumento de mysqldump.
            comando=[exe,'--defaults-extra-file='+str(archivo_cfg),'--single-transaction',
               '--no-tablespaces','--routines','--triggers','--events','--result-file='+str(destino),cfg['database']]
            r=subprocess.run(comando,capture_output=True,text=True,timeout=150,check=False)
            if r.returncode!=0:
                destino.unlink(missing_ok=True)
                raise ValueError('Falló el respaldo de MySQL: '+(r.stderr[:500] or str(r.returncode)))
            if not destino.exists() or destino.stat().st_size==0:
                raise ValueError('El respaldo quedó vacío; revisa el acceso a MySQL.')
        finally:
            archivo_cfg.unlink(missing_ok=True)
        QMessageBox.information(self.ui,'Respaldo realizado',f'Respaldo guardado en:\n{destino}')
