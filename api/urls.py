from django.urls import path

from .views import (
    CategoriaDetailView,
    CategoriaListCreateView,
    PedidoDetailView,
    PedidoListCreateView,
    ProductoDetailView,
    ProductoListCreateView,
)

urlpatterns = [
    path('categorias/', CategoriaListCreateView.as_view(), name='categoria-list'),
    path('categorias/<int:pk>/', CategoriaDetailView.as_view(), name='categoria-detail'),
    path('productos/', ProductoListCreateView.as_view(), name='producto-list'),
    path('productos/<int:pk>/', ProductoDetailView.as_view(), name='producto-detail'),
    path('pedidos/', PedidoListCreateView.as_view(), name='pedido-list'),
    path('pedidos/<int:pk>/', PedidoDetailView.as_view(), name='pedido-detail'),
]