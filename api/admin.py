from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Categoria, DetallePedido, Pedido, Producto, Rol, Sucursal, Usuario


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'descripcion')
	search_fields = ('nombre',)


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'telefono', 'correo_contacto', 'activa')
	list_filter = ('activa',)
	search_fields = ('nombre', 'direccion')


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
	fieldsets = UserAdmin.fieldsets + (
		('Minimarket', {'fields': ('nombre_completo', 'rol', 'sucursal', 'telefono', 'direccion_entrega')}),
	)
	add_fieldsets = UserAdmin.add_fieldsets + (
		('Minimarket', {'fields': ('email', 'nombre_completo', 'rol', 'sucursal', 'telefono', 'direccion_entrega')}),
	)
	list_display = ('username', 'nombre_completo', 'email', 'rol', 'sucursal', 'is_active', 'is_staff')
	list_filter = ('rol', 'sucursal', 'is_active', 'is_staff')
	search_fields = ('username', 'email', 'first_name', 'last_name')


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'activa')
	list_filter = ('activa',)
	search_fields = ('nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
	list_display = ('nombre_producto', 'categoria', 'precio_venta', 'stock_actual', 'disponible')
	list_filter = ('categoria', 'disponible')
	search_fields = ('nombre_producto', 'descripcion_producto')
	list_select_related = ('categoria',)


class DetallePedidoInline(admin.TabularInline):
	model = DetallePedido
	extra = 0
	can_delete = False
	readonly_fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal')


class PedidoAdminForm(forms.ModelForm):
	class Meta:
		model = Pedido
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['repartidor'].queryset = Usuario.objects.filter(
			rol__nombre=Rol.Nombre.REPARTIDOR,
			is_active=True,
		)

	def clean(self):
		cleaned_data = super().clean()
		estado = cleaned_data.get('estado')
		repartidor = cleaned_data.get('repartidor')
		if not estado:
			return cleaned_data

		if not self.instance.pk:
			if estado == Pedido.Estado.EN_RUTA and repartidor is None:
				self.add_error('repartidor', 'Asigna un repartidor antes de iniciar la ruta.')
			return cleaned_data

		pedido_actual = Pedido.objects.get(pk=self.instance.pk)
		if estado != pedido_actual.estado:
			try:
				pedido_actual.validar_cambio_estado(estado, repartidor.pk if repartidor else None)
			except ValueError as error:
				self.add_error('estado', str(error))
		return cleaned_data


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
	form = PedidoAdminForm
	list_display = ('id', 'fecha_pedido', 'cliente', 'sucursal', 'repartidor', 'estado', 'total_orden')
	list_filter = ('estado', 'metodo_pago', 'tipo_entrega', 'sucursal', 'fecha_pedido')
	search_fields = ('=id', 'cliente__username', 'cliente__email', 'repartidor__username')
	readonly_fields = ('fecha_pedido', 'total_orden')
	list_select_related = ('cliente', 'sucursal', 'repartidor')
	inlines = (DetallePedidoInline,)

	@transaction.atomic
	def save_model(self, request, obj, form, change):
		estado_solicitado = obj.estado
		if change:
			pedido_actual = Pedido.objects.select_for_update().get(pk=obj.pk)
			obj.estado = pedido_actual.estado
			super().save_model(request, obj, form, change)
			if estado_solicitado != pedido_actual.estado:
				obj.cambiar_estado(estado_solicitado)
		else:
			super().save_model(request, obj, form, change)
