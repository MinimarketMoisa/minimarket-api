from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import settings
from .limiter import limiter
from .routers import (
    auth,
    catalogo,
    clientes,
    direcciones,
    inventario,
    pedidos,
    repartidor,
)

is_prod = settings.entorno == "produccion"

app = FastAPI(
    title="Minimarket API",
    version="1.0.0",
    description="API del MVP de minimarkets: catálogo, pedidos, repartidores e inventario por sucursal.",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

origins = settings.cors_origins if settings.cors_origins else (["*"] if not is_prod else [])
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https: https://fastapi.tiangolo.com; font-src 'self' https: data:;"
    )
    if is_prod:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


for router in (
    auth.router,
    catalogo.router,
    clientes.router,
    direcciones.router,
    pedidos.router,
    repartidor.router,
    inventario.router,
):
    app.include_router(router)


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok", "entorno": settings.entorno}
