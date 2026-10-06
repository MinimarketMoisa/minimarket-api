"""Crea las tablas y los roles iniciales.   Uso:  python -m app.init_db"""
from sqlalchemy import select

from . import models
from .database import Base, SessionLocal, engine

ROLES = ["CLIENTE", "REPARTIDOR", "EMPLEADO", "ADMIN"]


def init() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existentes = set(db.scalars(select(models.Rol.nombre)))
        for nombre in ROLES:
            if nombre not in existentes:
                db.add(models.Rol(nombre=nombre))
        db.commit()
    print("Tablas y roles listos.")


if __name__ == "__main__":
    init()
