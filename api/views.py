from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Categoria, Pedido, Producto
from .permissions import CanCreateOrder, IsAdminOrReadOnly, user_is_admin
from .serializers import CategoriaSerializer, PedidoCrearSerializer, PedidoSerializer, ProductoSerializer


class CategoriaListCreateView(generics.ListCreateAPIView):
	serializer_class = CategoriaSerializer
	permission_classes = (IsAdminOrReadOnly,)

	def get_queryset(self):
		queryset = Categoria.objects.all()
		if not user_is_admin(self.request.user):
			queryset = queryset.filter(activa=True)
		return queryset


class CategoriaDetailView(generics.RetrieveUpdateAPIView):
	queryset = Categoria.objects.all()
	serializer_class = CategoriaSerializer
	permission_classes = (IsAdminOrReadOnly,)


class ProductoListCreateView(generics.ListCreateAPIView):
	serializer_class = ProductoSerializer
	permission_classes = (IsAdminOrReadOnly,)

	def get_queryset(self):
		queryset = Producto.objects.select_related('categoria').all()
		if not user_is_admin(self.request.user):
			queryset = queryset.filter(disponible=True, categoria__activa=True)
		return queryset


class ProductoDetailView(generics.RetrieveUpdateAPIView):
	queryset = Producto.objects.select_related('categoria').all()
	serializer_class = ProductoSerializer
	permission_classes = (IsAdminOrReadOnly,)


class PedidoListCreateView(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, CanCreateOrder)

	def get_queryset(self):
		user = self.request.user
		queryset = Pedido.objects.select_related('cliente', 'sucursal', 'repartidor').prefetch_related('detalles__producto')
		if user_is_admin(user):
			return queryset
		if user.rol and user.rol.nombre == 'REPARTIDOR':
			return queryset.filter(repartidor=user)
		return queryset.filter(Q(cliente=user))

	def get_serializer_class(self):
		if self.request.method == 'POST':
			return PedidoCrearSerializer
		return PedidoSerializer

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		pedido = serializer.save(cliente=request.user)
		response_serializer = PedidoSerializer(pedido, context=self.get_serializer_context())
		return Response(
			response_serializer.data,
			status=status.HTTP_201_CREATED,
			headers=self.get_success_headers(response_serializer.data),
		)


class PedidoDetailView(generics.RetrieveAPIView):
	serializer_class = PedidoSerializer
	permission_classes = (IsAuthenticated,)

	def get_queryset(self):
		user = self.request.user
		queryset = Pedido.objects.select_related('cliente', 'sucursal', 'repartidor').prefetch_related('detalles__producto')
		if user_is_admin(user):
			return queryset
		if user.rol and user.rol.nombre == 'REPARTIDOR':
			return queryset.filter(repartidor=user)
		return queryset.filter(cliente=user)
