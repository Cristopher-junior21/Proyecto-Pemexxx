"""Autenticación del sistema de capacitación.

No guarda contraseñas en texto plano. Los hashes se comprueban con Argon2id.
Reutiliza la conexión existente en database/conexion.py.
"""
from argon2 import PasswordHasher, exceptions
from database import conexion as db

_hasher = PasswordHasher()


def autenticar(nombre_usuario: str, contrasena: str):
    """Devuelve datos públicos del usuario si son correctos; si no, None.

    Lanza la excepción de conexión si MySQL no está disponible; la interfaz
    mostrará un mensaje sin exponer datos sensibles.
    """
    nombre_usuario = nombre_usuario.strip()
    if not nombre_usuario or not contrasena:
        return None
    registros = db.fetchall(
        """SELECT id, nombre_completo, nombre_usuario, password_hash
           FROM usuarios
           WHERE nombre_usuario = %s AND activo = 1
           LIMIT 1""",
        (nombre_usuario,),
    )
    if not registros:
        return None

    usuario = registros[0]
    try:
        if not _hasher.verify(usuario["password_hash"], contrasena):
            return None
    except (exceptions.VerificationError, exceptions.InvalidHashError):
        return None

    return {
        "id": usuario["id"],
        "nombre_completo": usuario["nombre_completo"],
        "nombre_usuario": usuario["nombre_usuario"],
    }
