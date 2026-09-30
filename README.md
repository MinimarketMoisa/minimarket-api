# Minimarket Backend API

Backend para el MVP de gestión de catálogo, pedidos y despacho, desarrollado con Django, Django REST Framework y PostgreSQL. El repositorio conserva también un prototipo FastAPI bajo `app/`; el panel administrativo y los endpoints descritos aquí corresponden a Django.

## Requisitos

- Python 3.12 o superior
- PostgreSQL 16 o superior
- Git

## Configuración local en Windows

Desde PowerShell, en la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

En `.env`, configura `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` y `DB_NAME` con los valores de tu instalación. No subas `.env` al repositorio.

Crea una base vacía con el mismo nombre de `DB_NAME`. Por ejemplo, si PostgreSQL escucha en el puerto `5433`:

```powershell
createdb -h 127.0.0.1 -p 5433 -U postgres minimarket_db
```

Si `createdb` no está en el `PATH`, ejecútalo desde la carpeta `bin` de PostgreSQL o agrégala al `PATH`. Después aplica el esquema y crea el usuario del panel:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

El panel queda en `http://127.0.0.1:8000/admin/` y la API en `http://127.0.0.1:8000/api/`.

## Endpoints principales

- `GET /api/categorias/`: lista categorías activas sin autenticación.
- `GET /api/productos/`: lista productos disponibles sin autenticación.
- `POST /api/token/`: obtiene los tokens de acceso y refresco JWT.
- `POST /api/token/refresh/`: renueva el token de acceso.
- `POST /api/pedidos/`: crea un pedido con autenticación; valida stock y descuenta existencias de forma transaccional.
- `/admin/`: gestiona catálogo y pedidos; permite asignar repartidores y actualizar estados válidos.

Las escrituras del catálogo requieren un usuario administrador. Los clientes autenticados solo consultan sus propios pedidos; los repartidores, los pedidos que tienen asignados.

## Validación

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test api
```