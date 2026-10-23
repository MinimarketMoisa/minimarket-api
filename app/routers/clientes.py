from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m
from .. import services
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..schemas import (
    ClienteAdminOut,
    ClienteAdminUpdate,
    DireccionOut,
)
from ..security import hash_password

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes (Admin)"],
    dependencies=[Depends(require_roles("ADMIN"))],
)


def cliente_admin_out(u: m.Usuario) -> ClienteAdminOut:
    return ClienteAdminOut(
        id_usuario=u.id_usuario,
        nombre_completo=u.nombre_completo,
        email=u.email,
        telefono=u.telefono,
        rol=u.rol.nombre if u.rol else "CLIENTE",
        activo=u.activo,
        email_verificado=u.email_verificado,
        last_login=u.last_login,
    )


@router.get("", response_model=list[ClienteAdminOut])
def listar_clientes(
    q: Optional[str] = Query(None, description="Buscar por nombre o correo"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    email_verificado: Optional[bool] = Query(None, description="Filtrar por correo verificado"),
    rol: Optional[str] = Query("CLIENTE", description="Filtrar por rol ('CLIENTE', 'EMPLEADO', 'REPARTIDOR', 'ADMIN' o 'TODOS')"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    (Solo ADMIN) Lista todos los clientes con opciones de filtrado y búsqueda.
    Por defecto muestra usuarios con rol CLIENTE. Usa rol=TODOS para ver todos.
    """
    query = select(m.Usuario).join(m.Usuario.rol)

    if rol and rol.upper() != "TODOS":
        query = query.where(func.upper(m.Rol.nombre) == rol.upper())

    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.where(
            func.lower(m.Usuario.nombre_completo).like(term)
            | func.lower(m.Usuario.email).like(term)
        )

    if activo is not None:
        query = query.where(m.Usuario.activo == activo)

    if email_verificado is not None:
        query = query.where(m.Usuario.email_verificado == email_verificado)

    query = query.order_by(m.Usuario.id_usuario.desc()).offset(offset).limit(limit)
    usuarios = db.scalars(query).all()
    return [cliente_admin_out(u) for u in usuarios]


@router.get("/{id_cliente}", response_model=dict)
def obtener_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
):
    """
    (Solo ADMIN) Obtiene el detalle completo de un cliente, incluyendo sus direcciones
    y el conteo de pedidos que ha realizado.
    """
    usuario = db.get(m.Usuario, id_cliente)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    direcciones = db.scalars(
        select(m.Direccion).where(m.Direccion.id_cliente == id_cliente)
    ).all()

    total_pedidos = db.scalar(
        select(func.count(m.Pedido.id_pedido)).where(m.Pedido.id_cliente == id_cliente)
    ) or 0

    datos = cliente_admin_out(usuario).model_dump()
    datos["total_pedidos"] = total_pedidos
    datos["direcciones"] = [
        DireccionOut.model_validate(d).model_dump() for d in direcciones
    ]

    return datos


@router.patch("/{id_cliente}", response_model=ClienteAdminOut)
def editar_cliente(
    id_cliente: int,
    data: ClienteAdminUpdate,
    admin_actual: m.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    (Solo ADMIN) Modifica los datos de un usuario: nombre, email, teléfono,
    estado activo, verificación de correo, rol o reseteo de contraseña.
    Protegido contra auto-bloqueo del administrador y revoca sesiones automáticamente.
    """
    usuario = db.get(m.Usuario, id_cliente)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    # Prevención de auto-bloqueo
    if id_cliente == admin_actual.id_usuario:
        if data.activo is False:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "No puedes desactivar tu propia cuenta de administrador"
            )
        if data.rol is not None and data.rol.upper() != "ADMIN":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "No puedes quitarte a ti mismo el rol de ADMIN"
            )

    revocar_sesiones = False

    if data.email is not None:
        nuevo_email = str(data.email).lower()
        if nuevo_email != usuario.email.lower():
            existe = db.scalar(
                select(m.Usuario.id_usuario).where(
                    func.lower(m.Usuario.email) == nuevo_email,
                    m.Usuario.id_usuario != id_cliente,
                )
            )
            if existe:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Ese correo ya está registrado por otro usuario",
                )
            usuario.email = nuevo_email
            # Si el admin no especificó explícitamente el estado de verificación, requerir nueva verificación
            if data.email_verificado is None:
                usuario.email_verificado = False
            revocar_sesiones = True

    if data.nombre_completo is not None:
        usuario.nombre_completo = data.nombre_completo

    if data.telefono is not None:
        usuario.telefono = data.telefono

    if data.activo is not None and data.activo != usuario.activo:
        usuario.activo = data.activo
        revocar_sesiones = True

    if data.email_verificado is not None:
        usuario.email_verificado = data.email_verificado

    if data.password is not None and data.password.strip():
        usuario.password = hash_password(data.password)
        revocar_sesiones = True

    if data.rol is not None:
        rol_obj = db.scalar(select(m.Rol).where(func.upper(m.Rol.nombre) == data.rol.upper()))
        if rol_obj is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El rol '{data.rol}' no existe. Roles válidos: CLIENTE, REPARTIDOR, EMPLEADO, ADMIN",
            )
        if usuario.id_rol != rol_obj.id_rol:
            usuario.id_rol = rol_obj.id_rol
            revocar_sesiones = True

    if revocar_sesiones:
        usuario.token_version += 1

    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Error al actualizar los datos del cliente")

    return cliente_admin_out(usuario)


@router.delete("/{id_cliente}")
def desactivar_cliente(
    id_cliente: int,
    admin_actual: m.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    (Solo ADMIN) Desactiva a un usuario. Reasigna automáticamente los pedidos si es un REPARTIDOR,
    revoca todas sus sesiones activas y previene auto-bloqueo del administrador.
    """
    if id_cliente == admin_actual.id_usuario:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "No puedes desactivar tu propia cuenta de administrador"
        )

    usuario = db.get(m.Usuario, id_cliente)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    # Si el usuario a desactivar es un REPARTIDOR, reasignar sus pedidos activos
    if usuario.rol.nombre == "REPARTIDOR":
        pedidos_activos = db.scalars(
            select(m.Pedido).where(
                m.Pedido.id_repartidor == id_cliente,
                m.Pedido.estado.in_(services.ESTADOS_ACTIVOS),
            )
        ).all()
        for ped in pedidos_activos:
            ped.id_repartidor = None
            ped.estado_repartidor = None
            services.asignar_repartidor(db, ped)

        perfil = db.get(m.PerfilRepartidor, id_cliente)
        if perfil:
            perfil.estado_operativo = "PENDIENTE"

    usuario.activo = False
    usuario.token_version += 1
    db.commit()

    return {
        "mensaje": "Cliente desactivado exitosamente",
        "id_usuario": id_cliente,
        "activo": False,
    }


@router.post("/{id_cliente}/reactivar")
def reactivar_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
):
    """
    (Solo ADMIN) Reactiva a un cliente previamente desactivado.
    Incrementa token_version para evitar que revivan tokens previos a la desactivación.
    """
    usuario = db.get(m.Usuario, id_cliente)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    usuario.activo = True
    usuario.token_version += 1
    db.commit()

    return {
        "mensaje": "Cliente reactivado exitosamente",
        "id_usuario": id_cliente,
        "activo": True,
    }
