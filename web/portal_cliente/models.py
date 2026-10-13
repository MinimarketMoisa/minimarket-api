from django.db import models

# Create your models here.
class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'

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
    last_login = models.DateTimeField(blank=True, null=True)

    class meta:
        managed = False
        db_table = 'usuarios'

    def __str__(self):
        return self.nombre_completo


class Municipio(models.Model):
    id_municipio = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        managed = False
        db_table = 'municipios'

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
        db_table = 'sucursales'

    def __str__(self):
        return self.nombre

class Direccion(models.Model):
    id_direccion = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_cliente')
    id_municipio = models.ForeignKey(Municipio, models.DO_NOTHING, db_column='id_municipio')
    detalle_direccion = models.CharField(max_length=250)
    punto_referencia = models.CharField(max_length=250, blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'direcciones'

    def __str__(self):
        return f"{self.detalle_direccion}, {self.id_municipio.nombre}"

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'categorias'

    def __str__(self):
        return self.nombre

