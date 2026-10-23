"""Crea las tablas y los roles iniciales.   Uso:  python -m app.init_db"""
from sqlalchemy import select, text

from . import models
from .database import Base, SessionLocal, engine

ROLES = ["CLIENTE", "REPARTIDOR", "EMPLEADO", "ADMIN"]


def init() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS email_verificado BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;"))
        conn.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS intentos_fallidos INTEGER NOT NULL DEFAULT 0;"))
        conn.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS bloqueado_hasta TIMESTAMPTZ NULL;"))
        conn.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS ultimo_correo_en TIMESTAMPTZ NULL;"))
        conn.execute(text("ALTER TABLE pedido ADD COLUMN IF NOT EXISTS estado_repartidor VARCHAR(20) DEFAULT NULL;"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_denuncia_abierta ON denuncia_repartidor (id_pedido) WHERE estado IN ('PENDIENTE', 'INVESTIGANDO');"))
    with SessionLocal() as db:
        existentes = set(db.scalars(select(models.Rol.nombre)))
        for nombre in ROLES:
            if nombre not in existentes:
                db.add(models.Rol(nombre=nombre))
        db.commit()
    print("Tablas y roles listos.")


if __name__ == "__main__":
    init()
