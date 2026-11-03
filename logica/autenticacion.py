"""Autenticación segura Argon2id y autorización por roles de BD."""
from argon2 import PasswordHasher, exceptions
from database import conexion as db

_hasher = PasswordHasher()


def autenticar(nombre_usuario: str, contrasena: str):
    if not nombre_usuario.strip() or not contrasena:
        return None
    rows = db.fetchall('''SELECT u.id, u.nombre_completo, u.nombre_usuario,
                         u.password_hash, r.codigo AS rol
                         FROM usuarios u LEFT JOIN roles r ON r.id=u.rol_id
                         WHERE u.nombre_usuario=%s AND u.activo=1 LIMIT 1''',
                       (nombre_usuario.strip(),))
    if not rows or not rows[0]['rol']:
        return None  # No usar cuentas sin rol asignado
    u=rows[0]
    try:
        if not _hasher.verify(u['password_hash'],contrasena):
            return None
    except (exceptions.VerificationError, exceptions.InvalidHashError):
        return None
    if _hasher.check_needs_rehash(u['password_hash']):
        db.execute('UPDATE usuarios SET password_hash=%s WHERE id=%s',
                   (_hasher.hash(contrasena),u['id']))
    return {'id':u['id'],'nombre_completo':u['nombre_completo'],
            'nombre_usuario':u['nombre_usuario'],'rol':u['rol']}
