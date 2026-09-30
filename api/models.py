from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal


class Rol(models.Model):
	class Nombre(models.TextChoices):
		ADMIN = 'ADMIN', 'Administrador'
		CLIENTE = 'CLIENTE', 'Cliente'
		REPARTIDOR = 'REPARTIDOR', 'Repartidor'

	nombre = models.CharField(max_length=20, choices=Nombre.choices, unique=True)
	descripcion = models.CharField(max_length=200, blank=True)

	def __str__(self):
		return self.get_nombre_display()


class Sucursal(models.Model):
	id = models.BigAutoField(primary_key=True, db_column='id_sucursal')
	nombre = models.CharField(max_length=150, unique=True)
	direccion = models.CharField(max_length=200)
	telefono = models.CharField(max_length=20, blank=True)
	correo_contacto = models.EmailField(blank=True)
	activa = models.BooleanField(default=True)

	def __str__(self):
		return self.nombre


class Usuario(AbstractUser):
	id = models.BigAutoField(primary_key=True, db_column='id_usuario')
	username = models.CharField(max_length=150, unique=True, db_column='nombre_usuario')
	password = models.CharField(max_length=128, db_column='password_hash', verbose_name='password')
	is_active = models.BooleanField(default=True, db_column='activo')
	email = models.EmailField(unique=True)
	rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios')
	sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios')
	nombre_completo = models.CharField(max_length=150, blank=True)
	telefono = models.CharField(max_length=20, blank=True)
	direccion_entrega = models.CharField(max_length=250, blank=True)

	def __str__(self):
		return self.nombre_completo or self.get_full_name() or self.username


class Categoria(models.Model):
	id = models.BigAutoField(primary_key=True, db_column='id_categoria')
	nombre = models.CharField(max_length=100, unique=True)
	descripcion = models.TextField(blank=True)
	activa = models.BooleanField(default=True)

	class Meta:
		verbose_name_plural = 'categorías'
		ordering = ['nombre']

	def __str__(self):
		return self.nombre


class Producto(models.Model):
	id = models.BigAutoField(primary_key=True, db_column='id_producto')
	categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
	nombre_producto = models.CharField(max_length=150)
	descripcion_producto = models.TextField(blank=True)
	precio_venta = models.DecimalField(
		max_digits=10,
		decimal_places=2,
		validators=[MinValueValidator(Decimal('0.01'))],
	)
	stock_actual = models.PositiveIntegerField(default=0)
	imagen = models.URLField(max_length=500, blank=True)
	disponible = models.BooleanField(default=True)

	class Meta:
		ordering = ['nombre_producto']
		constraints = [
			models.CheckConstraint(condition=Q(precio_venta__gt=0), name='producto_precio_positivo'),
			models.CheckConstraint(condition=Q(stock_actual__gte=0), name='producto_stock_no_negativo'),
		]

	def __str__(self):
		return self.nombre_producto

	def verificar_stock(self, cantidad):
		return cantidad > 0 and self.stock_actual >= cantidad

	def descontar_stock(self, cantidad):
		if not self.verificar_stock(cantidad):
			raise ValueError('Cantidad inválida o stock insuficiente.')
		self.stock_actual -= cantidad
		self.save(update_fields=('stock_actual',))

	def reabastecer_stock(self, cantidad):
		if cantidad <= 0:
			raise ValueError('La cantidad a reabastecer debe ser positiva.')
		self.stock_actual += cantidad
		self.save(update_fields=('stock_actual',))


class Pedido(models.Model):
	class Estado(models.TextChoices):
		PENDIENTE = 'PENDIENTE', 'Pendiente'
		PREPARADO = 'PREPARADO', 'Preparado'
		EN_RUTA = 'EN_RUTA', 'En ruta'
		ENTREGADO = 'ENTREGADO', 'Entregado'
		CANCELADO = 'CANCELADO', 'Cancelado'

	class MetodoPago(models.TextChoices):
		EFECTIVO = 'EFECTIVO', 'Efectivo'
		TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'

	class TipoEntrega(models.TextChoices):
		DOMICILIO = 'DOMICILIO', 'Domicilio'
		RETIRO = 'RETIRO', 'Retiro en sucursal'

	id = models.BigAutoField(primary_key=True, db_column='id_pedido')
	cliente = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='pedidos_cliente')
	sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='pedidos')
	repartidor = models.ForeignKey(
		Usuario,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name='pedidos_repartidor',
	)
	estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
	metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices)
	tipo_entrega = models.CharField(max_length=20, choices=TipoEntrega.choices)
	direccion_destino = models.CharField(max_length=250, blank=True)
	total_orden = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	fecha_pedido = models.DateTimeField(default=timezone.now, db_index=True)

	class Meta:
		ordering = ['-fecha_pedido']
		constraints = [
			models.CheckConstraint(condition=Q(total_orden__gte=0), name='pedido_total_no_negativo'),
		]

	def __str__(self):
		return f'Pedido #{self.pk} - {self.get_estado_display()}'

	def calcular_total(self):
		total = self.detalles.aggregate(total=models.Sum('subtotal'))['total']
		return total or Decimal('0.00')

	def validar_cambio_estado(self, nuevo_estado, repartidor_id=None):
		transiciones = {
			self.Estado.PENDIENTE: {self.Estado.PREPARADO, self.Estado.CANCELADO},
			self.Estado.PREPARADO: {self.Estado.EN_RUTA, self.Estado.CANCELADO},
			self.Estado.EN_RUTA: {self.Estado.ENTREGADO},
			self.Estado.ENTREGADO: set(),
			self.Estado.CANCELADO: set(),
		}
		if nuevo_estado not in transiciones:
			raise ValueError('Estado de pedido desconocido.')
		if nuevo_estado not in transiciones[self.estado]:
			raise ValueError(f'Transición inválida: {self.estado} -> {nuevo_estado}.')
		if nuevo_estado == self.Estado.EN_RUTA and repartidor_id is None:
			raise ValueError('Asigna un repartidor antes de iniciar la ruta.')

	def cambiar_estado(self, nuevo_estado):
		self.validar_cambio_estado(nuevo_estado, self.repartidor_id)
		if nuevo_estado == self.Estado.CANCELADO:
			self.cancelar_pedido()
			return
		self.estado = nuevo_estado
		self.save(update_fields=('estado',))

	def cancelar_pedido(self):
		with transaction.atomic():
			pedido = type(self).objects.select_for_update().get(pk=self.pk)
			if pedido.estado not in (self.Estado.PENDIENTE, self.Estado.PREPARADO):
				raise ValueError('Solo se pueden cancelar pedidos pendientes o preparados.')
			detalles = list(pedido.detalles.order_by('producto_id'))
			for detalle in detalles:
				producto = Producto.objects.select_for_update().get(pk=detalle.producto_id)
				producto.reabastecer_stock(detalle.cantidad)
			pedido.estado = self.Estado.CANCELADO
			pedido.save(update_fields=('estado',))
		self.estado = self.Estado.CANCELADO


class DetallePedido(models.Model):
	id = models.BigAutoField(primary_key=True, db_column='id_detalle')
	pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
	producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_pedido')
	cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
	precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
	subtotal = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		constraints = [
			models.CheckConstraint(condition=Q(cantidad__gt=0), name='detalle_cantidad_positiva'),
			models.CheckConstraint(condition=Q(precio_unitario__gt=0), name='detalle_precio_positivo'),
			models.CheckConstraint(condition=Q(subtotal__gte=0), name='detalle_subtotal_no_negativo'),
			models.UniqueConstraint(fields=['pedido', 'producto'], name='pedido_producto_unico'),
		]

	def calcular_subtotal(self):
		return self.precio_unitario * self.cantidad

	def __str__(self):
		return f'{self.producto.nombre_producto} x {self.cantidad}'
