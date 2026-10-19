"""Crea las tablas y los roles iniciales.   Uso:  python -m app.init_db"""
from sqlalchemy import select, text

from . import models
from .database import Base, SessionLocal, engine

ROLES = ["CLIENTE", "REPARTIDOR", "EMPLEADO", "ADMIN"]


def init() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS email_verificado BOOLEAN NOT NULL DEFAULT FALSE;"))
    with SessionLocal() as db:
        existentes = set(db.scalars(select(models.Rol.nombre)))
        for nombre in ROLES:
            if nombre not in existentes:
                db.add(models.Rol(nombre=nombre))
        db.commit()
    print("Tablas y roles listos.")


if __name__ == "__main__":
    init()
