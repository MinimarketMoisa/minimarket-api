# MiniMarket Backend API

API REST y WebSockets construida con **FastAPI**, **SQLAlchemy 2**, **PostgreSQL**, **PyJWT** y **SlowAPI** para la operación completa de **MiniMarket**: catálogo multisucursal, inventario con control de concurrencia, gestión de pedidos, asignación geográfica y tracking GPS de repartidores en tiempo real, pasarela de pagos simulada (Wompi Sandbox), correos transaccionales HTML y reportes empresariales.

Está diseñada para alimentar de forma unificada la **tienda web**, las **aplicaciones móviles en Flutter/Dart** (clientes y repartidores) y el **panel administrativo en Django** compartiendo la misma base de datos y hashes de contraseña compatibles (`pbkdf2_sha256` con 870,000 iteraciones).

---

## Arquitectura y Stack Tecnológico

| Componente | Tecnología | Función en el sistema |
| :--- | :--- | :--- |
| **Framework HTTP / WS** | FastAPI + Uvicorn (ASGI) | Endpoints REST tipados, validación automática, BackgroundTasks y WebSockets en vivo |
| **Base de datos y ORM** | PostgreSQL 16 + SQLAlchemy 2 (`psycopg`) | Persistencia relacional, restricciones de integridad y bloqueos pesimistas (`FOR UPDATE`) |
| **Autenticación y Seguridad** | PyJWT + PBKDF2-SHA256 + SlowAPI | JWT revocables, compatibilidad con Django Auth, anti-fuerza bruta y rate limiting por IP real |
| **Notificaciones** | SMTP (SSL/TLS) | Verificación de correo, cambio de email, recuperación de contraseña, alertas y facturas HTML |
| **Documentación interactiva** | OpenAPI / Swagger UI / ReDoc | Disponible en `/docs` y `/redoc` (controlable en producción con `ENABLE_DOCS`) |

---

## Estructura del Proyecto

```text
minimarket-api/
├── app/
│   ├── main.py                # Inicialización FastAPI, CORS, SlowAPI y cabeceras de seguridad
│   ├── config.py              # Configuración Pydantic Settings y validaciones estrictas de producción
│   ├── database.py            # Motor SQLAlchemy y sesiones PostgreSQL
│   ├── models.py              # Esquema relacional ORM (14 tablas + constraints e índices)
│   ├── schemas.py             # Esquemas de entrada/salida y validadores anti-bot/negocio
│   ├── security.py            # Hashing PBKDF2 compatible con Django y tokens JWT tipados
│   ├── deps.py                # Dependencias de autenticación, revocación y control RBAC por rol
│   ├── limiter.py             # Rate limiter SlowAPI con extracción de IP real tras proxy
│   ├── init_db.py             # Creación de tablas, columnas evolutivas y roles base
│   ├── seed.py                # Datos iniciales de ejemplo (sucursales, catálogo y usuarios)
│   ├── routers/
│   │   ├── auth.py            # Registro, login, verificación, cambio de correo y vistas HTML de reset
│   │   ├── catalogo.py        # Municipios, sucursales, categorías, productos y disponibilidad
│   │   ├── direcciones.py     # Direcciones de entrega del usuario con coordenadas GPS
│   │   ├── inventario.py      # Consulta y ajuste de stock por sucursal
│   │   ├── pedidos.py         # Creación, tracking REST/WebSocket, estados y denuncias
│   │   ├── pagos.py           # Simulador Wompi Sandbox y catálogo de tarjetas de prueba
│   │   ├── repartidor.py      # Flujo móvil del repartidor (aceptar, rechazar, GPS en vivo)
│   │   ├── clientes.py        # Administración de usuarios/roles/bloqueos (Solo ADMIN)
│   │   └── reportes.py        # Auditoría por pedido, reporte diario y reporte mensual (UTC-6)
│   └── services/
│       ├── pedidos.py         # Motor de asignación de sucursal, Haversine, estados y stock
│       ├── tracking.py        # Gestor de salas WebSocket por pedido
│       └── email.py           # Plantillas HTML MiniMarket y envío SMTP en segundo plano
├── tests/
│   └── test_e2e_security.py   # Suite automatizada E2E y de seguridad (27 pruebas)
├── core/ & api/ & manage.py   # Integración y panel administrativo Django sobre la misma BD
├── cambiar_clave.py           # Utilidad CLI para restablecer contraseña y revocar sesiones
├── poblar_500_productos.py    # Script de carga masiva de catálogo e inventario
├── test_gps_repartidor.py     # Simulador CLI de movimiento GPS y escucha WebSocket
├── requirements.txt           # Dependencias congeladas del proyecto
└── .env.example               # Plantilla de variables de entorno
```

---

## Roles del Sistema y Modelo de Datos

### Roles (RBAC)
- **`CLIENTE`**: Gestiona sus direcciones, consulta el catálogo, realiza pedidos (`DOMICILIO` o `RETIRO`), paga con tarjeta simulada, sigue su envío por WebSocket y puede denunciar incidencias del repartidor.
- **`REPARTIDOR`**: Recibe asignaciones automáticas de entregas, acepta o rechaza pedidos, transmite su ubicación GPS en tiempo real y también puede realizar compras personales como cliente (la API evita auto-asignarle su propio pedido).
- **`EMPLEADO`**: Opera exclusivamente sobre la sucursal a la que está asignado (visualiza inventario/pedidos de su tienda, actualiza stock, confirma transferencias y consulta reportes de su sucursal).
- **`ADMIN`**: Acceso global multisucursal, gestión de catálogo y precios, administración de usuarios/roles con revocación instantánea de sesiones, resolución de denuncias y reportes consolidados.

### Entidades principales en PostgreSQL
- **Identidad y acceso**: `rol`, `usuario`, `empleado`, `perfil_repartidor`.
- **Geografía y tiendas**: `municipio`, `sucursal`, `direccion`.
- **Catálogo e inventario**: `categoria`, `producto`, `inventario` (único por sucursal y producto).
- **Operación de pedidos**: `pedido`, `detalle_pedido` (precio congelado y subtotal calculado persistido), `rechazo_pedido`, `denuncia_repartidor`.

---

## Funcionamiento Interno de la API

### 1. Autenticación, Verificación y Seguridad
- **Registro con filtros anti-troll** (`POST /auth/registro`):
  - Exige teléfono válido de El Salvador (`2`, `6` o `7` + 7 dígitos, aceptando `+503` o `503`, normalizado a `XXXX-XXXX`).
  - Bloquea patrones ficticios o de bots (`7777-7777`, `7000-0000`, secuencias `7123-4567`, pares repetidos `7070-7070`) y prohíbe teléfonos duplicados entre cuentas (`409 Conflict`).
  - Rechaza dominios de correo desechables (`yopmail.com`, `10minutemail.com`, `tempmail.com`, etc.).
- **Verificación de correo obligatoria**: Tras el registro se envía un enlace firmado (`type="email_verification"`). Ni `POST /auth/login` ni los endpoints protegidos permiten operar hasta confirmar el correo.
- **Tokens JWT tipados y revocación inmediata**:
  - Cada JWT incluye `type` (`access`, `email_verification`, `email_change`, `password_reset`), `ver` (`token_version`) y `pwd` (`password_fingerprint`).
  - Si cambia la contraseña (desde la API, web o Django Admin) o si se desactiva/modifica un usuario, todos sus tokens anteriores quedan invalidados al instante.
- **Protección contra fuerza bruta y enumeración**:
  - Usa `DUMMY_HASH` de PBKDF2 en tiempo constante para que usuarios inexistentes respondan igual que contraseñas incorrectas.
  - Bloquea temporalmente la cuenta durante 15 minutos tras 5 intentos fallidos consecutivos.
  - Los endpoints de recuperación/reenvío responden de forma neutra sin revelar si un correo existe y aplican cooldown de 60 segundos entre envíos.
- **Rate limiting tras proxy**: [`get_real_ip`](app/limiter.py) toma `x-forwarded-for` o `cf-connecting-ip` cuando el tráfico llega desde proxy local (`127.0.0.1` / `::1`) para aislar la tasa de peticiones por cliente real.
- **Cabeceras de seguridad HTTP**: Todas las respuestas incluyen `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy` y `Strict-Transport-Security` (en producción).

### 2. Creación de Pedidos y Control de Inventario
Al invocar `POST /pedidos`:
1. **Reglas anti-acaparamiento**: Verifica que la cuenta tenga un teléfono salvadoreño válido registrado y limita a **máximo 1 pedido activo** (`PENDIENTE`, `PREPARADO`, `EN_RUTA`) por cuenta y por número de teléfono hasta que el pedido finalice (`ENTREGADO` o `CANCELADO`).
2. **Selección de sucursal con bloqueo transaccional**:
   - Si es `DOMICILIO`, filtra sucursales activas del mismo municipio que la dirección del cliente y agrega `COSTO_ENVIO`.
   - Si es `RETIRO`, evalúa la sucursal seleccionada (`costo_envio = 0`).
   - Bloquea las filas de `inventario` con `SELECT ... FOR UPDATE` para descontar stock de manera atómica y evitar condiciones de carrera.
3. **Asignación automática de repartidor**: Si es `DOMICILIO`, calcula la distancia geográfica (**fórmula Haversine**) entre la sucursal y los repartidores con `estado_operativo = "LIBRE"`, asignando el más cercano que no sea el mismo cliente y no haya rechazado previamente ese pedido.
4. **Código de negocio y facturación**: Genera un código único `PED-XXXXXX` y envía la factura HTML en segundo plano.

### 3. Estados del Pedido y Concurrencia
- Transiciones permitidas:
  - `PENDIENTE` -> `PREPARADO` (personal de sucursal/admin) o `CANCELADO` (cliente dueño o personal).
  - `PREPARADO` -> `EN_RUTA` (repartidor asignado que haya aceptado) | `ENTREGADO` (retiros) | `CANCELADO` (personal).
  - `EN_RUTA` -> `ENTREGADO` (repartidor asignado; marca automáticamente `estado_pago = "PAGADO"` si era `CONTRA_ENTREGA`).
- `ENTREGADO` y `CANCELADO` son estados finales inmutables (bloqueo con `FOR UPDATE` para impedir doble cancelación y doble restauración de stock).
- Al pasar a `CANCELADO`, restaura el stock descontado, libera al repartidor y reintenta asignar pedidos en espera.

### 4. Tracking GPS en Tiempo Real (REST + WebSockets)
- **Cliente (Web / App)**:
  - Consulta inicial por `GET /pedidos/{id_pedido}/seguimiento` (sucursal origen, destino y posición actual del repartidor, ocultando `id_repartidor` por privacidad).
  - Conexión en vivo a `wss://<host>/pedidos/{id_pedido}/ws/seguimiento?token=<JWT>` con soporte de keepalive `ping` -> `pong`.
- **Repartidor (App móvil)**:
  - Envía su posición a `PATCH /repartidor/ubicacion`; la API guarda coordenadas y retransmite en vivo eventos `posicion_actualizada`, `estado_pedido_actualizado` y `pago_confirmado` a los clientes conectados.

### 5. Pasarela de Pagos Simulada (Wompi Sandbox)
- `GET /pagos/wompi/tarjetas-prueba` entrega el catálogo oficial de **10 tarjetas de prueba** (8 Visa y 2 Mastercard, crédito/débito, distintos saldos, 1 bloqueada por fraude y 1 con saldo `$2.50` para simular fondos insuficientes).
- `POST /pagos/wompi/simular` valida lista blanca estricta, expiración, bloqueo bancario y saldo contra `pedido.total`. Si aprueba, registra `referencia_pago`, cambia `metodo_pago = "TARJETA"` y `estado_pago = "PAGADO"`, envía recibo por correo y emite evento por WebSocket.

---

## Catálogo de Endpoints

### Sistema
| Método | Ruta | Acceso | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Público | Estado del servicio y entorno activo |

### Autenticación (`/auth`)
| Método | Ruta | Acceso | Descripción |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/registro` | Público (`5/hour`) | Crea usuario `CLIENTE`, valida teléfono SV único y envía verificación por correo |
| `POST` | `/auth/login` | Público (`10/minute`) | Autenticación OAuth2 password; retorna JWT `access_token` |
| `GET` | `/auth/me` | Autenticado | Perfil del usuario autenticado |
| `GET` | `/auth/estado-verificacion` | Público (`30/minute`) | Consulta si un correo ya completó verificación |
| `GET` / `POST` | `/auth/verificar-correo` | Público | Activa `email_verificado` (HTML para navegador o JSON para móvil) |
| `POST` | `/auth/reenviar-verificacion` | Público (`5/hour`) | Reenvía enlace de verificación con cooldown |
| `POST` | `/auth/solicitar-cambio-email` | Autenticado (`5/hour`) | Exige contraseña actual y envía token al nuevo correo |
| `POST` | `/auth/confirmar-cambio-email` | Público | Confirma cambio de correo y revoca sesiones anteriores |
| `POST` | `/auth/olvide-contrasena` | Público (`5/hour`) | Envía enlace único de restablecimiento |
| `GET` | `/auth/restablecer-contrasena` | Público | Renderiza formulario HTML seguro con token oculto |
| `POST` | `/auth/restablecer-contrasena` | Público (`5/hour`) | Aplica nueva contraseña de un solo uso y revoca sesiones |

### Catálogo (`/municipios`, `/sucursales`, `/categorias`, `/productos`)
| Método | Ruta | Acceso | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/municipios` | Público | Lista municipios ordenados |
| `GET` | `/sucursales` | Público | Lista sucursales activas (filtrable por `id_municipio`) |
| `GET` | `/categorias` | Público | Lista categorías del catálogo |
| `POST` / `PATCH` | `/categorias` / `/categorias/{id}` | `ADMIN` | Crea o edita categorías |
| `GET` | `/productos` | Público | Busca productos activos (`id_categoria`, `q`, `skip`, `limit`) |
| `GET` | `/productos/{id}` | Público | Detalle de producto activo |
| `GET` | `/productos/{id}/disponibilidad` | Público | Sucursales con stock positivo para ese producto |
| `POST` / `PATCH` | `/productos` / `/productos/{id}` | `ADMIN` | Crea, edita precio/datos o desactiva productos |

### Inventario y Direcciones
| Método | Ruta | Acceso | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/inventario/sucursal/{id_sucursal}` | `EMPLEADO`, `ADMIN` | Consulta stock y vencimientos de la sucursal permitida |
| `PUT` | `/inventario` | `EMPLEADO`, `ADMIN` | Crea o actualiza stock y fecha de vencimiento por sucursal |
| `GET` / `POST` | `/direcciones` | `CLIENTE`, `REPARTIDOR` | Lista o crea direcciones con municipio y GPS |
| `DELETE` | `/direcciones/{id_direccion}` | `CLIENTE`, `REPARTIDOR` | Elimina dirección si no ha sido usada en pedidos |

### Pedidos, Seguimiento y Denuncias (`/pedidos`)
| Método | Ruta | Acceso | Descripción |
| :--- | :--- | :--- | :--- |
| `POST` | `/pedidos` | `CLIENTE`, `REPARTIDOR` | Crea pedido (máx. 1 activo), asigna sucursal/repartidor y envía factura |
| `GET` | `/pedidos/mis-pedidos` | `CLIENTE`, `REPARTIDOR` | Historial paginado de pedidos propios |
| `GET` | `/pedidos` | `EMPLEADO`, `ADMIN` | Lista pedidos (filtrado automático por sucursal si es `EMPLEADO`) |
| `GET` | `/pedidos/codigo/{codigo_pedido}` | Autorizado | Busca pedido por código `PED-XXXXXX` |
| `GET` | `/pedidos/{id_pedido}` | Autorizado | Detalle completo del pedido |
| `GET` | `/pedidos/{id_pedido}/seguimiento` | Autorizado | Coordenadas de sucursal, destino y repartidor asignado |
| `WS` | `/pedidos/{id_pedido}/ws/seguimiento` | JWT por query (`?token=`) | Canal WebSocket en vivo (alias también en `/pedidos/{id_pedido}/ws`) |
| `PATCH` | `/pedidos/{id_pedido}/estado` | Según rol | Avanza o cancela estado del pedido con notificación WS |
| `PATCH` | `/pedidos/{id_pedido}/pago` | `EMPLEADO`, `ADMIN` | Confirma pago (`PENDIENTE` / `PAGADO`) |
| `POST` | `/pedidos/{id_pedido}/asignar-repartidor` | `EMPLEADO`, `ADMIN` | Fuerza reintento de asignación automática de repartidor |
| `POST` | `/pedidos/{id_pedido}/enviar-factura` | Dueño o `ADMIN` (`5/hour`) | Reenvía factura HTML por correo |
| `POST` | `/pedidos/{id_pedido}/denunciar` | `CLIENTE`, `REPARTIDOR` (`5/hour`) | Registra denuncia abierta contra el repartidor del pedido |
| `GET` / `PATCH` | `/pedidos/denuncias/todas` / `/pedidos/denuncias/{id}` | `ADMIN` | Lista y resuelve denuncias contra repartidores |

### Pagos Wompi Sandbox (`/pagos`)
| Método | Ruta | Acceso | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/pagos/wompi/tarjetas-prueba` | Público | Lista las 10 tarjetas oficiales del simulador |
| `POST` | `/pagos/wompi/simular` | Autorizado del pedido | Procesa cobro simulado con tarjeta, factura y broadcast WS |

### Repartidor (`/repartidor`)
| Método | Ruta | Acceso | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/repartidor/pedido-entrante` | `REPARTIDOR` | Devuelve el pedido recién asignado pendiente de respuesta |
| `GET` | `/repartidor/mis-entregas` | `REPARTIDOR` | Lista entregas asignadas o en curso (filtrable por `ASIGNADO` / `ACEPTADO`) |
| `GET` | `/repartidor/pedidos/{id_pedido}` | `REPARTIDOR` | Ficha completa de entrega con contacto y coordenadas |
| `POST` | `/repartidor/pedidos/{id_pedido}/aceptar` | `REPARTIDOR` | Acepta la entrega y marca repartidor en curso |
| `POST` | `/repartidor/pedidos/{id_pedido}/rechazar` | `REPARTIDOR` | Rechaza la entrega, libera perfil y reasigna automáticamente a otro repartidor |
| `PATCH` | `/repartidor/ubicacion` | `REPARTIDOR` | Actualiza latitud/longitud GPS y emite evento en vivo por WebSocket |
| `PATCH` | `/repartidor/estado` | `REPARTIDOR` | Cambia estado operativo (`LIBRE` o `PENDIENTE`) |

### Clientes y Reportes (`/clientes`, `/reportes`)
| Método | Ruta | Acceso | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/clientes` | `ADMIN` | Lista usuarios con búsqueda y filtros (`rol`, `activo`, `email_verificado`) |
| `GET` | `/clientes/{id_cliente}` | `ADMIN` | Detalle completo de usuario, direcciones y conteo de pedidos |
| `PATCH` | `/clientes/{id_cliente}` | `ADMIN` | Edita datos, rol, estado o teléfono único con revocación de sesión |
| `DELETE` | `/clientes/{id_cliente}` | `ADMIN` | Desactiva usuario, reasigna pedidos si es repartidor y revoca sesiones |
| `POST` | `/clientes/{id_cliente}/reactivar` | `ADMIN` | Reactiva usuario sin revivir JWT emitidos antes de desactivarlo |
| `GET` | `/reportes/pedidos/{id_pedido}` | `EMPLEADO`, `ADMIN` | Auditoría financiera y operativa de un pedido |
| `GET` | `/reportes/diario` | `EMPLEADO`, `ADMIN` | Consolidado del día (UTC-6), métodos de pago, sucursales y top productos |
| `GET` | `/reportes/mensual` | `EMPLEADO`, `ADMIN` | Ventas por día del mes, tasa de efectividad y rendimiento de repartidores |

---

## Instalación y Puesta en Marcha

### Requisitos previos
- Python 3.10 o superior
- PostgreSQL 16 o superior en ejecución

### 1. Clonar e instalar dependencias
```bash
git clone https://github.com/MinimarketMoisa/minimarket-api.git
cd minimarket-api

python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
# source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno (`.env`)
Copia `.env.example` a `.env` y completa tus credenciales:

```bash
cp .env.example .env
```

Variables principales en [`app/config.py`](app/config.py):

| Variable | Descripción | Nota en producción (`ENTORNO=produccion`) |
| :--- | :--- | :--- |
| `ENTORNO` | `desarrollo` o `produccion` | Por defecto `produccion` |
| `DATABASE_URL` | URI PostgreSQL (`postgresql://user:pass@host:5432/db`) | No permite `postgres:postgres@` en producción |
| `JWT_SECRET` | Clave secreta para firmar tokens JWT | Obligatoria de **32+ caracteres** en producción |
| `JWT_ALGORITHM` | `HS256`, `HS384` o `HS512` | Por defecto `HS256` |
| `JWT_EXPIRE_MINUTES` | Minutos de vigencia del token de acceso | Configurable (ej. `60` o `43200`) |
| `API_BASE_URL` | URL pública de la API (para enlaces en correos) | Debe iniciar con `https://` en producción |
| `FRONTEND_RESET_URL` | URL base del frontend web cliente | Usada en enlaces de retorno de vistas HTML |
| `CORS_ORIGINS` | Orígenes permitidos (lista o `*`) | En producción restringir a los dominios web reales |
| `COSTO_ENVIO` | Tarifa fija de envío a domicilio | Por defecto `1.50` |
| `ENABLE_DOCS` | Habilita `/docs`, `/redoc` y `/openapi.json` | Booleano (`true` / `false`) |
| `SMTP_*` | `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` | Requeridos para envío real de correos y facturas |

### 3. Inicializar base de datos y datos de ejemplo
```bash
python -m app.init_db
python -m app.seed
```
`app.seed` crea sucursales iniciales en San Miguel, catálogo de arranque y cuentas base de prueba (contraseña por defecto `Prueba12345` para entorno local):
- `admin@minimarket.test` (`ADMIN`)
- `empleado@minimarket.test` (`EMPLEADO`)
- `repartidor1@minimarket.test`, `repartidor2@minimarket.test` (`REPARTIDOR`)
- `cliente@minimarket.test` (`CLIENTE`)

### 4. Ejecutar el servidor API
- **Desarrollo local**:
  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
- **Producción detrás de proxy inverso (Caddy / Nginx)**:
  ```bash
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips="127.0.0.1"
  ```

---

## Pruebas Automatizadas y Scripts Útiles

La suite completa en [`tests/test_e2e_security.py`](tests/test_e2e_security.py) valida de extremo a extremo contra PostgreSQL todas las reglas críticas de negocio, seguridad JWT, concurrencia de inventario, rate limiting, tracking WebSocket, simulador Wompi Sandbox, unicidad de teléfono SV y límite de 1 pedido activo:

```bash
# Ejecutar con pytest (recomendado)
pytest -v tests/

# O ejecutar directamente el runner secuencial
python tests/test_e2e_security.py
```

Scripts auxiliares disponibles en la raíz:
- `python cambiar_clave.py <email> <nueva_contraseña>`: Cambia la contraseña de cualquier usuario y revoca todas sus sesiones activas.
- `python poblar_500_productos.py`: Carga catálogo extendido e inventario inicial en PostgreSQL.
- `python test_gps_repartidor.py`: Simula en consola el avance GPS de un repartidor y su recepción en vivo por WebSocket.
