from rest_framework.test import APITestCase
from rest_framework import status

from .models import Categoria, DetallePedido, Pedido, Producto, Rol, Sucursal, Usuario


class MinimarketApiTests(APITestCase):
	def setUp(self):
		self.admin_role, _ = Rol.objects.get_or_create(nombre=Rol.Nombre.ADMIN)
		self.client_role, _ = Rol.objects.get_or_create(nombre=Rol.Nombre.CLIENTE)
		self.sucursal = Sucursal.objects.create(nombre='Central', direccion='San Miguel')
		self.categoria = Categoria.objects.create(nombre='Bebidas')
		self.producto = Producto.objects.create(
			categoria=self.categoria,
			nombre_producto='Agua 1L',
			precio_venta='1.25',
			stock_actual=5,
		)
		self.cliente = Usuario.objects.create_user(
			username='cliente',
			email='cliente@example.com',
			password='test-password-123',
			rol=self.client_role,
		)
		self.admin = Usuario.objects.create_user(
			username='admin',
			email='admin@example.com',
			password='test-password-123',
			rol=self.admin_role,
			is_staff=True,
		)

	def test_catalog_is_public_and_filters_inactive_items(self):
		Categoria.objects.create(nombre='Inactiva', activa=False)
		Producto.objects.create(
			categoria=self.categoria,
			nombre_producto='No disponible',
			precio_venta='2.00',
			disponible=False,
		)

		categorias = self.client.get('/api/categorias/')
		productos = self.client.get('/api/productos/')

		self.assertEqual(categorias.status_code, status.HTTP_200_OK)
		self.assertEqual([item['nombre'] for item in categorias.data], ['Bebidas'])
		self.assertEqual(productos.status_code, status.HTTP_200_OK)
		self.assertEqual([item['nombre_producto'] for item in productos.data], ['Agua 1L'])

	def test_only_admin_can_write_catalog(self):
		payload = {'nombre': 'Lácteos', 'descripcion': '', 'activa': True}

		self.client.force_authenticate(user=self.cliente)
		denied = self.client.post('/api/categorias/', payload, format='json')
		self.client.force_authenticate(user=self.admin)
		allowed = self.client.post('/api/categorias/', payload, format='json')

		self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
		self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)

	def test_jwt_can_create_order_and_stock_is_decremented(self):
		token_response = self.client.post('/api/token/', {
			'username': 'cliente',
			'password': 'test-password-123',
		}, format='json')
		self.assertEqual(token_response.status_code, status.HTTP_200_OK)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

		response = self.client.post('/api/pedidos/', {
			'sucursal_id': self.sucursal.pk,
			'metodo_pago': 'EFECTIVO',
			'tipo_entrega': 'DOMICILIO',
			'direccion_destino': 'Colonia Centro',
			'detalles': [
				{'producto_id': self.producto.pk, 'cantidad': 2},
				{'producto_id': self.producto.pk, 'cantidad': 1},
			],
		}, format='json')

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['total_orden'], '3.75')
		self.assertEqual(len(response.data['detalles']), 1)
		self.producto.refresh_from_db()
		self.assertEqual(self.producto.stock_actual, 2)

	def test_insufficient_stock_leaves_order_and_stock_unchanged(self):
		self.client.force_authenticate(user=self.cliente)
		response = self.client.post('/api/pedidos/', {
			'sucursal_id': self.sucursal.pk,
			'metodo_pago': 'EFECTIVO',
			'tipo_entrega': 'RETIRO',
			'detalles': [{'producto_id': self.producto.pk, 'cantidad': 6}],
		}, format='json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(Pedido.objects.count(), 0)
		self.producto.refresh_from_db()
		self.assertEqual(self.producto.stock_actual, 5)

	def test_user_can_only_list_own_orders(self):
		self.client.force_authenticate(user=self.cliente)
		response = self.client.get('/api/pedidos/')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, [])

	def test_cancelling_order_restores_stock(self):
		self.client.force_authenticate(user=self.cliente)
		response = self.client.post('/api/pedidos/', {
			'sucursal_id': self.sucursal.pk,
			'metodo_pago': 'EFECTIVO',
			'tipo_entrega': 'RETIRO',
			'detalles': [{'producto_id': self.producto.pk, 'cantidad': 2}],
		}, format='json')
		pedido = Pedido.objects.get(pk=response.data['id'])

		pedido.cambiar_estado(Pedido.Estado.CANCELADO)

		self.producto.refresh_from_db()
		pedido.refresh_from_db()
		self.assertEqual(self.producto.stock_actual, 5)
		self.assertEqual(pedido.estado, Pedido.Estado.CANCELADO)
