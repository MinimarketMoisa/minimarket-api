from django.db import migrations


def create_default_roles(apps, schema_editor):
    Rol = apps.get_model('api', 'Rol')
    database = schema_editor.connection.alias
    roles = (
        ('ADMIN', 'Administrador del minimarket'),
        ('CLIENTE', 'Cliente de la aplicación'),
        ('REPARTIDOR', 'Encargado de entregas'),
    )
    for nombre, descripcion in roles:
        Rol.objects.using(database).get_or_create(
            nombre=nombre,
            defaults={'descripcion': descripcion},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_roles, migrations.RunPython.noop),
    ]