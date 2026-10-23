"""Script utilitario para cambiar la contraseña de cualquier usuario en la base de datos.

Uso:
    python cambiar_clave.py <email> <nueva_contraseña>
    o simplemente:
    python cambiar_clave.py
"""
import sys
from sqlalchemy import select
from app.database import SessionLocal
from app import models as m
from app.security import hash_password


def cambiar(email: str, nueva_clave: str) -> bool:
    email_normalizado = email.strip().lower()
    with SessionLocal() as db:
        usuario = db.scalar(select(m.Usuario).where(m.Usuario.email == email_normalizado))
        if not usuario:
            print(f"[ERROR] Usuario con correo '{email_normalizado}' no encontrado.")
            return False

        usuario.password = hash_password(nueva_clave)
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.activo = True
        usuario.email_verificado = True
        usuario.token_version = (usuario.token_version or 0) + 1  # Revoca sesiones anteriores
        db.commit()
        print(f"[EXITO] Contrasena actualizada para: {usuario.nombre_completo} ({usuario.email})")
        print(f"        Rol: {usuario.rol.nombre} | Sesiones anteriores revocadas.")
        return True


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        cambiar(sys.argv[1], sys.argv[2])
    else:
        print("=== Cambiar Contrasena de Usuario ===")
        correo = input("Correo electronico: ").strip()
        nueva = input("Nueva contrasena: ").strip()
        if not correo or not nueva:
            print("[ERROR] Correo y contrasena son obligatorios.")
        else:
            cambiar(correo, nueva)
