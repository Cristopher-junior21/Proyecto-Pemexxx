"""Alta interactiva de un usuario local con contraseña Argon2id.

Desde la raíz del repositorio: .\\.venv\\Scripts\\python.exe -m scripts.crear_usuario
"""
from getpass import getpass
from argon2 import PasswordHasher
import mysql.connector
from database import conexion as db


def main():
    print("=== Alta de usuario autorizado de Cangrejera ===")
    nombre = input("Nombre completo: ").strip()
    usuario = input("Nombre de usuario: ").strip()
    if not nombre or not usuario:
        print("Debes proporcionar nombre completo y usuario.")
        return
    if len(nombre) > 150 or len(usuario) > 80:
        print("Nombre de usuario o nombre completo demasiado largo.")
        return

    contrasena = getpass("Contraseña (mínimo 12 caracteres): ")
    confirmar = getpass("Repite la contraseña: ")
    if len(contrasena) < 12 or contrasena != confirmar:
        print("Las contraseñas no coinciden o tienen menos de 12 caracteres.")
        return

    hash_seguro = PasswordHasher().hash(contrasena)
    try:
        db.execute(
            """INSERT INTO usuarios (nombre_completo, nombre_usuario, password_hash, activo)
               VALUES (%s, %s, %s, 1)""",
            (nombre, usuario, hash_seguro),
        )
    except mysql.connector.IntegrityError:
        print("Ese nombre de usuario ya existe.")
        return
    except mysql.connector.Error as exc:
        print(f"No se pudo guardar el usuario. Error de MySQL: {exc.errno}")
        return
    print(f"Cuenta '{usuario}' creada correctamente. La contraseña se almacenó como hash Argon2id.")


if __name__ == "__main__":
    main()
