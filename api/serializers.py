from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .models import Categoria, DetallePedido, Pedido, Producto, Sucursal


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ('id', 'nombre', 'descripcion', 'activa')
        read_only_fields = ('id',)


class ProductoSerializer(serializers.ModelSerializer):
    categoria_id = serializers.PrimaryKeyRelatedField(source='categoria', queryset=Categoria.objects.all())

    class Meta:
        model = Producto
        fields = (
            'id', 'categoria_id', 'nombre_producto', 'descripcion_producto',
            'precio_venta', 'stock_actual', 'imagen', 'disponible',
        )
        read_only_fields = ('id',)


class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = DetallePedido
        fields = ('id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal')


class PedidoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.username', read_only=True)
    created_at = serializers.DateTimeField(source='fecha_pedido', read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = (
            'id', 'cliente', 'cliente_nombre', 'sucursal', 'repartidor', 'estado',
            'metodo_pago', 'tipo_entrega', 'direccion_destino', 'total_orden',
            'created_at', 'detalles',
        )


class DetallePedidoEntradaSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1)


class PedidoCrearSerializer(serializers.Serializer):
    sucursal_id = serializers.PrimaryKeyRelatedField(source='sucursal', queryset=Sucursal.objects.filter(activa=True))
    metodo_pago = serializers.ChoiceField(choices=Pedido.MetodoPago.choices)
    tipo_entrega = serializers.ChoiceField(choices=Pedido.TipoEntrega.choices)
    direccion_destino = serializers.CharField(max_length=250, required=False, allow_blank=True, default='')
    detalles = DetallePedidoEntradaSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        if attrs['tipo_entrega'] == Pedido.TipoEntrega.DOMICILIO and not attrs['direccion_destino'].strip():
            raise serializers.ValidationError({'direccion_destino': 'Se requiere una dirección para entrega a domicilio.'})
        return attrs

    def create(self, validated_data):
        cantidades = defaultdict(int)
        for item in validated_data.pop('detalles'):
            cantidades[item['producto_id']] += item['cantidad']

        with transaction.atomic():
            productos = list(
                Producto.objects.select_for_update()
                .select_related('categoria')
                .filter(pk__in=cantidades)
                .order_by('pk')
            )
            productos_por_id = {producto.pk: producto for producto in productos}
            faltantes = set(cantidades) - set(productos_por_id)
            if faltantes:
                raise serializers.ValidationError({'detalles': f'Producto(s) inexistente(s): {sorted(faltantes)}.'})

            for producto_id, cantidad in cantidades.items():
                producto = productos_por_id[producto_id]
                if not producto.disponible or not producto.categoria.activa:
                    raise serializers.ValidationError({'detalles': f"'{producto.nombre_producto}' no está disponible."})
                if not producto.verificar_stock(cantidad):
                    raise serializers.ValidationError({
                        'detalles': f"Stock insuficiente para '{producto.nombre_producto}'. Disponible: {producto.stock_actual}."
                    })

            pedido = Pedido.objects.create(
                cliente=validated_data.pop('cliente'),
                total_orden=Decimal('0.00'),
                **validated_data,
            )
            total = Decimal('0.00')
            for producto_id, cantidad in cantidades.items():
                producto = productos_por_id[producto_id]
                producto.descontar_stock(cantidad)
                subtotal = producto.precio_venta * cantidad
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio_venta,
                    subtotal=subtotal,
                )
                total += subtotal

            pedido.total_orden = total
            pedido.save(update_fields=('total_orden',))
            return pedido