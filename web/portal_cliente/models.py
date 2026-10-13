from django.db import models


class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        managed = False
        db_table = 'rol'

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Rol, models.DO_NOTHING, db_column='id_rol')
    nombre_completo = models.CharField(max_length=150)
    email = models.EmailField(max_length=150, unique=True)
    password = models.CharField(max_length=254)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuario'

    def __str__(self):
        return self.nombre_completo


class Municipio(models.Model):
    id_municipio = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        managed = False
        db_table = 'municipio'

    def __str__(self):
        return self.nombre


class Sucursal(models.Model):
    id_sucursal = models.AutoField(primary_key=True)
    id_municipio = models.ForeignKey(Municipio, models.DO_NOTHING, db_column='id_municipio')
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=250)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    activa = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'sucursal'

    def __str__(self):
        return self.nombre


class Direccion(models.Model):
    id_direccion = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_cliente', related_name='direcciones')
    id_municipio = models.ForeignKey(Municipio, models.DO_NOTHING, db_column='id_municipio')
    detalle_direccion = models.CharField(max_length=250)
    punto_referencia = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'direccion'

    def __str__(self):
        return f"{self.detalle_direccion}, {self.id_municipio.nombre}"


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'categoria'

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    id_categoria = models.ForeignKey(Categoria, models.DO_NOTHING, db_column='id_categoria')
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=50, blank=True, null=True)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    imagen_url = models.CharField(max_length=500, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'producto'

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    id_pedido = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_cliente', related_name='pedidos_cliente')
    id_sucursal = models.ForeignKey(Sucursal, models.DO_NOTHING, db_column='id_sucursal')
    id_repartidor = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_repartidor', blank=True, null=True, related_name='pedidos_repartidor')
    id_direccion = models.ForeignKey(Direccion, models.DO_NOTHING, db_column='id_direccion', blank=True, null=True)
    canal = models.CharField(max_length=50)
    tipo_entrega = models.CharField(max_length=50)
    metodo_pago = models.CharField(max_length=50)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default='pendiente')
    estado_pago = models.CharField(max_length=20)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'pedido'


class DetallePedido(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    id_pedido = models.ForeignKey(Pedido, models.DO_NOTHING, db_column='id_pedido', related_name='detalles')
    id_producto = models.ForeignKey(Producto, models.DO_NOTHING, db_column='id_producto')
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'detalle_pedido'