from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, catalogo, direcciones, inventario, pedidos, repartidor

app = FastAPI(
    title="Minimarket API",
    version="1.0.0",
    description="API del MVP de minimarkets: catálogo, pedidos, repartidores e inventario por sucursal.",
)

# En desarrollo se permite cualquier origen. En producción, lista aquí solo tus dominios.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for router in (auth.router, catalogo.router, direcciones.router, pedidos.router,
               repartidor.router, inventario.router):
    app.include_router(router)


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}
