"""Verifica la conexión a MySQL sin abrir ninguna ventana.

Desde la raíz del proyecto: python -m database.verificar_conexion
"""
import mysql.connector
from database import conexion


def main():
    try:
        nombre = conexion.test_connection()
        resultado = conexion.fetchall("""SELECT TABLE_NAME, TABLE_TYPE
            FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_TYPE, TABLE_NAME""")
    except mysql.connector.Error as error:
        print(f"ERROR al conectar con MySQL ({error.errno}): {error.msg}")
        print("Revisa host, puerto, usuario, contraseña y nombre de la base en .env")
        return 1
    print("CONEXIÓN CORRECTA. Base de datos:", nombre)
    for item in resultado:
        print(f"  {item['TABLE_TYPE']}: {item['TABLE_NAME']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
