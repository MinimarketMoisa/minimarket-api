from django.urls import path
from . import views
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include

from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_cliente, name='login'),
    path('logout/', views.logout_cliente, name='logout'),
    path('perfil/', views.perfil_cliente, name='perfil'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('carrito/', views.ver_carrito, name='carrito'),
    path('carrito/agregar/<int:id_producto>/', views.agregar_al_carrito, name='agregar_carrito'),
    path('carrito/actualizar/', views.actualizar_carrito, name='actualizar_carrito'),
    path('checkout/', views.checkout, name='checkout'),
    path('mis-pedidos/', views.mis_pedidos, name='pedidos'),
]