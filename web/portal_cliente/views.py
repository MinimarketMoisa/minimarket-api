from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Usuario, Producto, Categoria, Direccion, Municipio, Sucursal, Pedido
from app.security import verify_password
from app.database import SessionLocal
from app.schemas import PedidoIn, PedidoItemIn
from app import services
import app.models as sa_models

def _get_cart(session):
    return session.setdefault('carrito', {})

def login_cliente(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        try:
            u = Usuario.objects.get(email__iexact=email, activo=True)
            if verify_password(password, u.password):
                if u.id_rol.nombre != 'CLIENTE':
                    messages.error(request, 'Acceso restringido: Portal exclusivo para Clientes.')
                    return render(request, 'portal_cliente/login.html')
                request.session['usuario_id'] = u.id_usuario
                request.session['usuario_nombre'] = u.nombre_completo
                return redirect('catalogo')
            messages.error(request, 'Credenciales incorrectas.')
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado o inactivo.')
    return render(request, 'portal_cliente/login.html')

def logout_cliente(request):
    request.session.flush()
    return redirect('login')

def catalogo(request):
    usuario_id = request.session.get('usuario_id')
    busqueda = request.POST.get('q', request.GET.get('q', '')).strip()
    id_cat = request.GET.get('cat')

    productos = Producto.objects.filter(activo=True)
    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) | 
            Q(descripcion__icontains=busqueda) | 
            Q(id_categoria__nombre__icontains=busqueda)
        )
    if id_cat:
        productos = productos.filter(id_categoria_id=id_cat)

    categorias = Categoria.objects.all().order_by('nombre')
    carrito = _get_cart(request.session)
    cart_count = sum(carrito.values())

    return render(request, 'portal_cliente/catalogo.html', {
        'productos': productos,
        'categorias': categorias,
        'busqueda': busqueda,
        'cat_actual': int(id_cat) if id_cat else None,
        'cart_count': cart_count,
        'usuario_nombre': request.session.get('usuario_nombre'),
    })

def agregar_al_carrito(request, id_producto):
    cart = _get_cart(request.session)
    pid = str(id_producto)
    cart[pid] = cart.get(pid, 0) + 1
    request.session.modified = True
    messages.success(request, 'Producto añadido al carrito.')
    return redirect(request.META.get('HTTP_REFERER', 'catalogo'))

def ver_carrito(request):
    cart = _get_cart(request.session)
    items = []
    subtotal = Decimal('0.00')

    if cart:
        p_ids = [int(k) for k in cart.keys()]
        productos = {p.id_producto: p for p in Producto.objects.filter(id_producto__in=p_ids)}
        for pid_str, cant in cart.items():
            pid = int(pid_str)
            if pid in productos:
                p = productos[pid]
                st = p.precio_base * cant
                subtotal += st
                items.append({'producto': p, 'cantidad': cant, 'subtotal': st})

    costo_envio = Decimal('1.50')
    return render(request, 'portal_cliente/carrito.html', {
        'items': items,
        'subtotal': subtotal,
        'costo_envio': costo_envio,
        'total': subtotal + costo_envio,
    })

def actualizar_carrito(request):
    if request.method == 'POST':
        cart = _get_cart(request.session)
        pid = request.POST.get('id_producto')
        accion = request.POST.get('accion')
        if pid in cart:
            if accion == 'mas':
                cart[pid] += 1
            elif accion == 'menos':
                cart[pid] -= 1
                if cart[pid] <= 0:
                    del cart[pid]
            elif accion == 'borrar':
                del cart[pid]
            request.session.modified = True
    return redirect('ver_carrito')

def checkout(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    cart = _get_cart(request.session)
    if not cart:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('catalogo')

    usuario = Usuario.objects.get(id_usuario=usuario_id)
    direcciones = usuario.direcciones.all()
    sucursales = Sucursal.objects.filter(activa=True)

    if request.method == 'POST':
        tipo_entrega = request.POST.get('tipo_entrega') # 'DOMICILIO' o 'RETIRO'
        metodo_pago = request.POST.get('metodo_pago')   # 'CONTRA_ENTREGA' o 'TRANSFERENCIA'
        id_dir = request.POST.get('id_direccion')
        id_suc = request.POST.get('id_sucursal')

        # Armar el payload que exige la API
        items_in = [PedidoItemIn(id_producto=int(pid), cantidad=cant) for pid, cant in cart.items()]
        pedido_in = PedidoIn(
            items=items_in,
            tipo_entrega=tipo_entrega,
            metodo_pago=metodo_pago,
            canal='WEB',
            id_direccion=int(id_dir) if tipo_entrega == 'DOMICILIO' and id_dir else None,
            id_sucursal=int(id_suc) if tipo_entrega == 'RETIRO' and id_suc else None
        )

        # Invocar core transaccional con SQLAlchemy para bloqueo pesimista y reparto
        with SessionLocal() as db:
            sa_cliente = db.get(sa_models.Usuario, usuario_id)
            try:
                pedido_creado = services.crear_pedido(db, sa_cliente, pedido_in)
                request.session['carrito'] = {}
                request.session.modified = True
                messages.success(request, f'¡Pedido #{pedido_creado.id_pedido} confirmado exitosamente!')
                return redirect('mis_pedidos')
            except Exception as e:
                messages.error(request, f'Error al procesar la orden: {getattr(e, "detail", str(e))}')

    return render(request, 'portal_cliente/checkout.html', {
        'direcciones': direcciones,
        'sucursales': sucursales,
    })

def mis_pedidos(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    pedidos = Pedido.objects.filter(id_cliente_id=usuario_id).order_by('-id_pedido').prefetch_related('detalles__id_producto')
    return render(request, 'portal_cliente/pedidos.html', {'pedidos': pedidos})

def perfil_cliente(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = Usuario.objects.get(id_usuario=usuario_id)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'actualizar_datos':
            usuario.nombre_completo = request.POST.get('nombre_completo', usuario.nombre_completo)
            usuario.telefono = request.POST.get('telefono', usuario.telefono)
            usuario.save()
            request.session['usuario_nombre'] = usuario.nombre_completo
            messages.success(request, 'Perfil actualizado correctamente.')
        elif accion == 'nueva_direccion':
            id_mun = request.POST.get('id_municipio')
            detalle = request.POST.get('detalle_direccion', '').strip()
            ref = request.POST.get('punto_referencia', '').strip()
            if detalle and id_mun:
                Direccion.objects.create(
                    id_cliente=usuario,
                    id_municipio_id=id_mun,
                    detalle_direccion=detalle,
                    punto_referencia=ref
                )
                messages.success(request, 'Dirección registrada.')
        return redirect('perfil')

    return render(request, 'portal_cliente/perfil.html', {
        'usuario': usuario,
        'direcciones': usuario.direcciones.select_related('id_municipio').all(),
        'municipios': Municipio.objects.all().order_by('nombre'),
    })