"""Creación inicial de las 2 cuentas autorizadas: ADMIN y CAPTURA.
También permite asignar rol a una cuenta anterior. Usar exclusivamente desde
la PC de administración con acceso a MySQL (sin contraseñas en los argumentos).
"""
from getpass import getpass
import mysql.connector
from argon2 import PasswordHasher
from database import conexion as db


def crear_o_asignar(rol):
    nombre_usuario=input(f'Usuario {rol}: ').strip()
    if not nombre_usuario or len(nombre_usuario)>60:
        print('Usuario inválido');return
    rows=db.fetchall('SELECT id FROM usuarios WHERE nombre_usuario=%s',(nombre_usuario,))
    id_rol=db.fetchall('SELECT id FROM roles WHERE codigo=%s',(rol,))[0]['id']
    if rows:
        if input('Cuenta existente. ¿Asignar rol? [si/NO] ').lower().strip()!='si':
            return
        db.execute('UPDATE usuarios SET rol_id=%s WHERE id=%s',(id_rol,rows[0]['id']))
        print('Rol asignado.');return
    nombre=input('Nombre completo: ').strip()
    p1=getpass('Contraseña nueva (mínimo 12): ')
    p2=getpass('Confirmación: ')
    if not nombre or len(p1)<12 or p1!=p2:
        print('No se creó: datos o contraseña incorrectos.');return
    db.execute('''INSERT INTO usuarios(nombre_completo,nombre_usuario,password_hash,rol_id,activo)
               VALUES(%s,%s,%s,%s,1)''',(nombre,nombre_usuario,PasswordHasher().hash(p1),id_rol))
    print(f'{rol} creado correctamente.')


def main():
    print('Alta administrativa inicial en MySQL (requiere credenciales de la BD).')
    try:
        for rol in ('ADMIN','CAPTURA'):
            crear_o_asignar(rol)
    except (mysql.connector.Error,KeyError) as e:
        print('Error. Ejecuta primero migrations/02_eventos_roles_cedulas.sql:',e)

if __name__=='__main__':main()
