"""
Script para poblar la base de datos con 100 productos reales típicos de El Salvador
(estilo Súper Selectos y Walmart SV), organizados por categorías, con descripciones,
precios en USD, códigos de barras únicos EAN-13, URLs de imagen HTTPS e inventario inicial.

Uso:
    python poblar_100_productos.py
"""

from decimal import Decimal
from sqlalchemy import select
from app import models as m
from app.database import SessionLocal


def D(valor) -> Decimal:
    return Decimal(str(valor))


CATEGORIAS_DATA = [
    {"nombre": "Abarrotes y Despensa", "descripcion": "Granos básicos, aceites, pastas, salsas y enlatados"},
    {"nombre": "Bebidas y Refrescos", "descripcion": "Gaseosas, jugos, agua purificada, hidratantes y cervezas"},
    {"nombre": "Lácteos y Huevos", "descripcion": "Leches, quesos, cremas, mantequillas y huevos frescos"},
    {"nombre": "Snacks y Golosinas", "descripcion": "Boquitas locales, galletas, papitas y dulces"},
    {"nombre": "Embutidos y Carnes", "descripcion": "Salchichas, jamones, pollo y cortes frescos"},
    {"nombre": "Panadería y Desayuno", "descripcion": "Pan de caja, pan dulce, tostadas y cereales"},
    {"nombre": "Frutas y Verduras", "descripcion": "Vegetales y frutas frescas de consumo diario"},
    {"nombre": "Cuidado Personal", "descripcion": "Higiene oral, jabones corporales, champú y desodorantes"},
    {"nombre": "Limpieza del Hogar", "descripcion": "Detergentes, cloro, desinfectantes y papel higiénico"},
]

PRODUCTOS_DATA = [
    # --- 1. ABARROTES Y DESPENSA (15) ---
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Blanco San Francisco 908g",
        "descripcion": "Arroz blanco de grano seleccionado, cocción perfecta. Presentación 2 libras (908g).",
        "codigo_barras": "7411001000018",
        "precio_base": D("1.15"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/uncooked-white-rice.png",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Precocido San Francisco 908g",
        "descripcion": "Arroz precocido grano entero suelto y esponjoso, rendimiento superior.",
        "codigo_barras": "7411001000025",
        "precio_base": D("1.25"),
        "imagen_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Rojo de Seda San Francisco 800g",
        "descripcion": "Frijol rojo salvadoreño de seda, grano suave de cocción rápida.",
        "codigo_barras": "7411001000032",
        "precio_base": D("1.45"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/kidney-beans.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijoles Rojos Molidos Natura's 400g",
        "descripcion": "Frijoles rojos molidos estilo casero listos para servir.",
        "codigo_barras": "7411001000049",
        "precio_base": D("0.95"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/refried-beans.png",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Aceite Vegetal Mazola 1 Litro",
        "descripcion": "Aceite vegetal 100% puro libre de colesterol, ideal para freír y cocinar.",
        "codigo_barras": "7411001000056",
        "precio_base": D("2.50"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/vegetable-oil.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Aceite de Oliva Extra Virgen Carbonell 500ml",
        "descripcion": "Aceite de oliva virgen extra de primera presión en frío, botella de vidrio.",
        "codigo_barras": "7411001000063",
        "precio_base": D("5.90"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/olive-oil.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Azúcar Blanca Cañal 1 kg",
        "descripcion": "Azúcar blanca refinada de alta pureza 100% salvadoreña.",
        "codigo_barras": "7411001000070",
        "precio_base": D("1.10"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/sugar-in-bowl.png",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Harina de Maíz Maseca 1 kg",
        "descripcion": "Harina de maíz nixtamalizado para tortillas, pupusas y tamales.",
        "codigo_barras": "7411001000087",
        "precio_base": D("1.20"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/cornmeal.png",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Pasta Espagueti Ina 200g",
        "descripcion": "Pasta alimenticia clásica enriquecida con vitaminas y minerales.",
        "codigo_barras": "7411001000094",
        "precio_base": D("0.45"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/spaghetti.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Pasta Coditos Ina 200g",
        "descripcion": "Pasta de sémola de trigo durum en forma de coditos para sopas y ensaladas.",
        "codigo_barras": "7411001000100",
        "precio_base": D("0.45"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/macaroni.png",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Salsa de Tomate Ranchera Natura's 210g",
        "descripcion": "Salsa de tomates naturales con cebolla, chile verde y especias.",
        "codigo_barras": "7411001000117",
        "precio_base": D("0.55"),
        "imagen_url": "https://images.unsplash.com/photo-1597362925123-77861d3fbac7?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Pasta de Tomate Del Fuerte 210g",
        "descripcion": "Pasta concentrada de tomate maduro para guisados y carnes.",
        "codigo_barras": "7411001000124",
        "precio_base": D("0.65"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/tomato-paste.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Atún en Trozos en Agua Sardimar 140g",
        "descripcion": "Lomo de atún aleta amarilla en agua, bajo en grasa y rico en proteína.",
        "codigo_barras": "7411001000131",
        "precio_base": D("1.35"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/canned-tuna.png",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Atún en Trozos en Aceite Calvo 140g",
        "descripcion": "Atún claro en aceite vegetal calidad gourmet en lata abre fácil.",
        "codigo_barras": "7411001000148",
        "precio_base": D("1.40"),
        "imagen_url": "https://images.unsplash.com/photo-1534482421-64566f976cfa?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Café Molido El Sol Tradicional 400g",
        "descripcion": "Café 100% arábica tostado y molido de estricta altura salvadoreño.",
        "codigo_barras": "7411001000155",
        "precio_base": D("3.25"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/coffee.jpg",
    },

    # --- 2. BEBIDAS Y REFRESCOS (12) ---
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Coca-Cola Original 2.5 Litros",
        "descripcion": "Refresco carbonatado sabor original familiar botella PET no retornable.",
        "codigo_barras": "7411001000162",
        "precio_base": D("2.50"),
        "imagen_url": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Coca-Cola Sin Azúcar 1.5 Litros",
        "descripcion": "Gaseosa Coca-Cola sabor original con cero calorías y sin azúcar.",
        "codigo_barras": "7411001000179",
        "precio_base": D("1.60"),
        "imagen_url": "https://images.unsplash.com/photo-1554866585-cd94860890b7?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Kolashanpan 1.5 Litros",
        "descripcion": "El sabor salvadoreño único de caña de azúcar en botella de 1.5L.",
        "codigo_barras": "7411001000186",
        "precio_base": D("1.35"),
        "imagen_url": "https://images.unsplash.com/photo-1624517452488-04869289c4ca?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Pepsi Regular 2 Litros",
        "descripcion": "Refresco de cola refrescante tamaño familiar botella 2L.",
        "codigo_barras": "7411001000193",
        "precio_base": D("1.75"),
        "imagen_url": "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa 7Up Lima Limón 1.5 Litros",
        "descripcion": "Refresco carbonatado transparente con sabor natural a lima-limón sin cafeína.",
        "codigo_barras": "7411001000209",
        "precio_base": D("1.30"),
        "imagen_url": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Petit Néctar de Manzana 1 Litro",
        "descripcion": "Néctar de manzana pasteurizado fortificado con vitamina C en envase Tetra Pak.",
        "codigo_barras": "7411001000216",
        "precio_base": D("1.25"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/apple-juice.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Kern's Néctar de Melocotón 1 Litro",
        "descripcion": "Delicioso néctar con pulpa de melocotón de textura suave.",
        "codigo_barras": "7411001000223",
        "precio_base": D("1.35"),
        "imagen_url": "https://images.unsplash.com/photo-1534353473418-4cfa6c56fd38?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Agua Purificada Las Perlitas Galón 3.78L",
        "descripcion": "Agua de mesa 100% purificada con ozono y luz ultravioleta.",
        "codigo_barras": "7411001000230",
        "precio_base": D("1.50"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/water.png",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Agua Purificada Alpina 600ml",
        "descripcion": "Botella individual de agua purificada ligera con tapa deportiva.",
        "codigo_barras": "7411001000247",
        "precio_base": D("0.50"),
        "imagen_url": "https://images.unsplash.com/photo-1523362628745-0c100150b504?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gatorade Cool Blue 600ml",
        "descripcion": "Bebida isotónica con electrolitos sabor mora azul para hidratación activa.",
        "codigo_barras": "7411001000254",
        "precio_base": D("1.20"),
        "imagen_url": "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Cerveza Pilsener Nacional Lata 355ml",
        "descripcion": "La cerveza tradicional de El Salvador estilo lager rubia refrescante.",
        "codigo_barras": "7411001000261",
        "precio_base": D("1.15"),
        "imagen_url": "https://images.unsplash.com/photo-1535958636474-b021ee887b13?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Cerveza Golden Extra Lata 355ml",
        "descripcion": "Cerveza tipo golden lager suave, ligera y fácil de tomar.",
        "codigo_barras": "7411001000278",
        "precio_base": D("1.10"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/beer.jpg",
    },

    # --- 3. LÁCTEOS Y HUEVOS (12) ---
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Entera Salud 1 Litro UHT",
        "descripcion": "Leche 100% de vaca entera ultrapasteurizada, fortificada con vitamina A y D.",
        "codigo_barras": "7411001000285",
        "precio_base": D("1.55"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/milk.png",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Semidescremada Dos Pinos 1 Litro",
        "descripcion": "Leche semidescremada 2% grasa en envase larga vida Tetra Brik.",
        "codigo_barras": "7411001000292",
        "precio_base": D("1.60"),
        "imagen_url": "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Deslactosada Salud 1 Litro",
        "descripcion": "Leche entera deslactosada de fácil digestión para personas intolerantes a la lactosa.",
        "codigo_barras": "7411001000308",
        "precio_base": D("1.75"),
        "imagen_url": "https://images.unsplash.com/photo-1528750997573-59b89d56f4f7?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Crema Pura Especial Salud 400ml",
        "descripcion": "Crema de leche salvadoreña espesa y con sabor tradicional para pupusas o frijoles.",
        "codigo_barras": "7411001000315",
        "precio_base": D("1.65"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/sour-cream.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Quesillo Especial San Julián 1 lb",
        "descripcion": "Quesillo tradicional salvadoreño con el punto exacto de hebra para derretir.",
        "codigo_barras": "7411001000322",
        "precio_base": D("3.25"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/mozzarella.png",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Fresco Petacones 1 lb",
        "descripcion": "Queso duro blando salvadoreño con el sello de calidad inconfundible Petacones.",
        "codigo_barras": "7411001000339",
        "precio_base": D("3.95"),
        "imagen_url": "https://images.unsplash.com/photo-1452195100486-9cc805987862?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Crema Philadelphia Clásico 210g",
        "descripcion": "Queso crema para untar, suave y cremoso ideal para postres y tostadas.",
        "codigo_barras": "7411001000346",
        "precio_base": D("2.85"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/cream-cheese.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Mantequilla con Sal Dos Pinos 115g",
        "descripcion": "Mantequilla de pura crema de leche pasteurizada con sal añadida.",
        "codigo_barras": "7411001000353",
        "precio_base": D("1.15"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/butter-sliced.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Margarina Mirasol Barra 100g",
        "descripcion": "Margarina clásica con sal enriquecida con vitaminas para repostería y cocina.",
        "codigo_barras": "7411001000360",
        "precio_base": D("0.55"),
        "imagen_url": "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Yogur Líquido Yes Fresa 750g",
        "descripcion": "Yogur bebible con probióticos activos sabor fresa natural.",
        "codigo_barras": "7411001000377",
        "precio_base": D("1.85"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/strawberry-yogurt.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Cartón de Huevos Santa Anita 30 Unidades",
        "descripcion": "Huevos frescos medianos de granja controlada en empaque protector de cartón.",
        "codigo_barras": "7411001000384",
        "precio_base": D("4.95"),
        "imagen_url": "https://images.unsplash.com/photo-1516467508483-a7212febe31a?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Media Cartón de Huevos Santa Anita 15 Unidades",
        "descripcion": "15 huevos frescos seleccionados de cascarón limpio y yema brillante.",
        "codigo_barras": "7411001000391",
        "precio_base": D("2.60"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/egg.png",
    },

    # --- 4. SNACKS Y GOLOSINAS (12) ---
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Churritos Diana 150g",
        "descripcion": "Snack de maíz horneado con el inconfundible sabor saladito y crujiente Diana.",
        "codigo_barras": "7411001000407",
        "precio_base": D("0.90"),
        "imagen_url": "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Elotitos Diana con Queso y Chile 150g",
        "descripcion": "Palitos de maíz inflado con cobertura de queso y un toque picante salvadoreño.",
        "codigo_barras": "7411001000414",
        "precio_base": D("0.90"),
        "imagen_url": "https://images.unsplash.com/photo-1621447504864-d8686e12698c?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Jalapeños Diana 150g",
        "descripcion": "Crujientes hojuelas de maíz con el auténtico y fuerte sabor a chile jalapeño.",
        "codigo_barras": "7411001000421",
        "precio_base": D("0.90"),
        "imagen_url": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Quesitos Diana 150g",
        "descripcion": "Aros de maíz crujiente con abundante sabor a queso cheddar.",
        "codigo_barras": "7411001000438",
        "precio_base": D("0.90"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/tortilla-chips.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Palitos Diana 150g",
        "descripcion": "Palitos de harina de trigo tostados y ligeramente salados, ideales para dip.",
        "codigo_barras": "7411001000445",
        "precio_base": D("0.90"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/pretzels.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Tortillitas Diana Saladas 150g",
        "descripcion": "Tortillas de maíz tostadas con sal marina, textura extra crujiente.",
        "codigo_barras": "7411001000452",
        "precio_base": D("0.85"),
        "imagen_url": "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Oreo Original Paquete x6",
        "descripcion": "Galletas de sándwich de cacao con crema sabor a vainilla.",
        "codigo_barras": "7411001000469",
        "precio_base": D("1.35"),
        "imagen_url": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Chiky Chocolate Paquete x6",
        "descripcion": "Galleta crujiente bañada en una rica capa de chocolate con leche Pozuelo.",
        "codigo_barras": "7411001000476",
        "precio_base": D("1.20"),
        "imagen_url": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Club Social Original 6 Pack",
        "descripcion": "Galletas saladas horneadas individuales para llevar a cualquier parte.",
        "codigo_barras": "7411001000483",
        "precio_base": D("1.25"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/crackers.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Papas Fritas Lay's Clásicas 110g",
        "descripcion": "Hojuelas de papa natural fritas y sazonadas con el toque exacto de sal.",
        "codigo_barras": "7411001000490",
        "precio_base": D("1.65"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/potato-chips.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Papas Pringles Original Tubo 149g",
        "descripcion": "Papas tostadas en tubo apilables con forma hiperbólica perfecta.",
        "codigo_barras": "7411001000506",
        "precio_base": D("2.45"),
        "imagen_url": "https://images.unsplash.com/photo-1527842891421-42eec6e703ea?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Snickers Barra 52.7g",
        "descripcion": "Barra de chocolate con leche rellena de turrón, caramelo y cacahuates.",
        "codigo_barras": "7411001000513",
        "precio_base": D("0.95"),
        "imagen_url": "https://images.unsplash.com/photo-1549007994-cb92caebd54b?auto=format&fit=crop&w=600&q=80",
    },

    # --- 5. EMBUTIDOS Y CARNES (8) ---
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha de Pavo Toledo Paquete 454g",
        "descripcion": "Salchichas bajas en grasa de pura carne de pavo empacadas al vacío.",
        "codigo_barras": "7411001000520",
        "precio_base": D("2.10"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/sausages.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Viena Toledo 200g",
        "descripcion": "Salchicha estilo viena condimentada ideal para panchos o guisados.",
        "codigo_barras": "7411001000537",
        "precio_base": D("0.95"),
        "imagen_url": "https://images.unsplash.com/photo-1629814249584-bd4d53cf0e7d?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón de Pierna Cocido Toledo 250g",
        "descripcion": "Rebanadas delgadas de jamón de pierna curado y cocido.",
        "codigo_barras": "7411001000544",
        "precio_base": D("2.30"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/ham.png",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Tocineta Ahumada Rebanada Toledo 200g",
        "descripcion": "Tiras de tocino de cerdo ahumadas con maderas finas listas para dorar.",
        "codigo_barras": "7411001000551",
        "precio_base": D("2.65"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/raw-bacon.png",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Pechuga de Pollo Deshuesada Pollo Indio 1 lb",
        "descripcion": "Pechuga de pollo fresca sin piel ni hueso, corte limpio certificado.",
        "codigo_barras": "7411001000568",
        "precio_base": D("3.45"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/chicken-breasts.png",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Carne Molida Especial de Res 1 lb",
        "descripcion": "Carne molida 90% magra de res fresca salvadoreña sin aditivos.",
        "codigo_barras": "7411001000575",
        "precio_base": D("3.85"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/fresh-ground-beef.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Chorizos Criollos San Miguel 400g",
        "descripcion": "Chorizos estilo tradicional oriental con hierbas aromáticas y achiote.",
        "codigo_barras": "7411001000582",
        "precio_base": D("2.80"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/chorizo.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón de Pavo Virginia Zwan 250g",
        "descripcion": "Jamón virginia de pechuga de pavo ahumado bajo en sodio.",
        "codigo_barras": "7411001000599",
        "precio_base": D("2.75"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/turkey-breast.jpg",
    },

    # --- 6. PANADERÍA Y DESAYUNO (8) ---
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Blanco Mediano Bimbo 560g",
        "descripcion": "Pan de caja clásico con leche y calcio para sándwiches suaves.",
        "codigo_barras": "7411001000605",
        "precio_base": D("1.95"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/white-bread.jpg",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Integral 100% Bimbo 680g",
        "descripcion": "Pan elaborado con grano entero y fibra dietética para cuidar tu salud.",
        "codigo_barras": "7411001000612",
        "precio_base": D("2.40"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/whole-wheat-bread.jpg",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan para Hamburguesa Bimbo Bimbollos 8u",
        "descripcion": "Bollos suaves con ajonjolí tostado listos para hamburguesas caseras.",
        "codigo_barras": "7411001000629",
        "precio_base": D("2.15"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/hamburger-bun.jpg",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan para Hot Dog Bimbo Medias Noches 8u",
        "descripcion": "Pan alargado esponjoso para preparar perros calientes con facilidad.",
        "codigo_barras": "7411001000636",
        "precio_base": D("1.95"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/hot-dog-buns.jpg",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Tostadas Clásicas Bimbo 210g",
        "descripcion": "Rebanadas de pan tostado crujientes enriquecidas con vitaminas.",
        "codigo_barras": "7411001000643",
        "precio_base": D("1.45"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/toast.jpg",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Corn Flakes Kellogg's 380g",
        "descripcion": "Hojuelas de maíz tostadas sin gluten añadidas con hierro y vitaminas B.",
        "codigo_barras": "7411001000650",
        "precio_base": D("2.70"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/cornflakes.jpg",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Zucaritas Kellogg's 400g",
        "descripcion": "Ricas hojuelas de maíz azucaradas para despertar la energía del tigre.",
        "codigo_barras": "7411001000667",
        "precio_base": D("3.15"),
        "imagen_url": "https://images.unsplash.com/photo-1521483451569-e33803c0330c?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Avena en Hojuelas Quaker 360g",
        "descripcion": "Avena de grano entero rica en fibra soluble para el colesterol y digestión.",
        "codigo_barras": "7411001000674",
        "precio_base": D("1.25"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/rolled-oats.jpg",
    },

    # --- 7. FRUTAS Y VERDURAS (10) ---
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Tomate de Cocina Maya 1 lb",
        "descripcion": "Tomates frescos seleccionados de madurez media para salsas y guisos.",
        "codigo_barras": "7411001000681",
        "precio_base": D("0.65"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/tomato.png",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Cebolla Blanca Importada 1 lb",
        "descripcion": "Cebollas blancas firmes y frescas de bulbo limpio.",
        "codigo_barras": "7411001000698",
        "precio_base": D("0.75"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/white-onion.png",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Cebolla Morada Fresca 1 lb",
        "descripcion": "Cebolla morada crujiente ideal para curtidos, ensaladas y mariscos.",
        "codigo_barras": "7411001000704",
        "precio_base": D("0.85"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/red-onion.png",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Papa Blanca Lavada 1 lb",
        "descripcion": "Papa blanca lisa de pulpa suave perfecta para puré, fritas o sopas.",
        "codigo_barras": "7411001000711",
        "precio_base": D("0.70"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/potatoes-yukon-gold.png",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Chile Verde Dulce Unidad",
        "descripcion": "Chile pimiento verde fresco con piel gruesa y aromática.",
        "codigo_barras": "7411001000728",
        "precio_base": D("0.35"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/green-bell-pepper.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Limón Pérsico Jugoso Bolsa 1 lb",
        "descripcion": "Limones verdes sin semilla con abundante jugo natural.",
        "codigo_barras": "7411001000735",
        "precio_base": D("0.90"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/lime.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Plátano Maduro de Primera Unidad",
        "descripcion": "Plátano maduro con dulzura perfecta para canoas, fritos o sancochados.",
        "codigo_barras": "7411001000742",
        "precio_base": D("0.40"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/plantains.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Roja Gala Unidad",
        "descripcion": "Manzana dulce importada de pulpa firme y cáscara brillante.",
        "codigo_barras": "7411001000759",
        "precio_base": D("0.60"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/apple.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Banano Criollo Racimo 5 Unidades",
        "descripcion": "Bananos dulces madurados al punto ricos en potasio y energía.",
        "codigo_barras": "7411001000766",
        "precio_base": D("0.75"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/bananas.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Zanahoria Fresca Lavada 1 lb",
        "descripcion": "Zanahorias dulces crocantes listas para picar, cocinar o rallar.",
        "codigo_barras": "7411001000773",
        "precio_base": D("0.55"),
        "imagen_url": "https://img.spoonacular.com/ingredients_500x500/carrots.jpg",
    },

    # --- 8. CUIDADO PERSONAL (12) ---
    {
        "categoria": "Cuidado Personal",
        "nombre": "Pasta Dental Colgate Triple Acción 100ml",
        "descripcion": "Protección anticaries, dientes blancos y aliento fresco con menta original.",
        "codigo_barras": "7411001000780",
        "precio_base": D("1.40"),
        "imagen_url": "https://images.unsplash.com/photo-1550985543-f1ea83691cd8?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Cepillo Dental Colgate Zig Zag Pack x2",
        "descripcion": "Cerdas en ángulo multi-nivel para una limpieza profunda entre los dientes.",
        "codigo_barras": "7411001000797",
        "precio_base": D("1.75"),
        "imagen_url": "https://images.unsplash.com/photo-1625834319124-345137437603?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón de Tocador Protex Avena Antibacterial 110g",
        "descripcion": "Elimina el 99.9% de bacterias mientras humecta y cuida la piel con avena.",
        "codigo_barras": "7411001000803",
        "precio_base": D("0.95"),
        "imagen_url": "https://images.unsplash.com/photo-1600857544200-b2f666a9a2ec?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón de Tocador Palmolive Naturals Oliva 110g",
        "descripcion": "Sensación humectante y fragancia suave con extracto de oliva y aloe.",
        "codigo_barras": "7411001000810",
        "precio_base": D("0.85"),
        "imagen_url": "https://images.unsplash.com/photo-1546552768-9e3a94b38a59?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Champú Head & Shoulders Limpieza Renovadora 375ml",
        "descripcion": "Fórmula dermasense para hasta 100% libre de caspa y cabello fresco.",
        "codigo_barras": "7411001000827",
        "precio_base": D("4.50"),
        "imagen_url": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Champú Pantene Pro-V Restauración 400ml",
        "descripcion": "Ayuda a reparar el cabello dañado desde la raíz hasta las puntas.",
        "codigo_barras": "7411001000834",
        "precio_base": D("4.25"),
        "imagen_url": "https://images.unsplash.com/photo-1705155733070-16069099b94a?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Desodorante Rexona Men Cobalt Roll-On 50ml",
        "descripcion": "Protección antitranspirante 48 horas activada por el movimiento.",
        "codigo_barras": "7411001000841",
        "precio_base": D("2.20"),
        "imagen_url": "https://images.unsplash.com/photo-1616763355548-1b606f439f86?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Desodorante Lady Speed Stick Fresh Fusion Roll-On 50ml",
        "descripcion": "Control del sudor y olor con aroma femenino y sin dejar manchas blancas.",
        "codigo_barras": "7411001000858",
        "precio_base": D("2.15"),
        "imagen_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Crema Corporal Nivea Milk Nutritiva 250ml",
        "descripcion": "Infusión de serum de hidratación profunda y aceite de almendras para piel seca.",
        "codigo_barras": "7411001000865",
        "precio_base": D("3.80"),
        "imagen_url": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Toallas Sanitarias Kotex Nocturnas con Alas 10u",
        "descripcion": "Máxima absorción y protección durante toda la noche con tecnología anti-derrames.",
        "codigo_barras": "7411001000872",
        "precio_base": D("1.65"),
        "imagen_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Alcohol en Gel Antibacterial Germ-X 250ml",
        "descripcion": "Gel desinfectante con 70% de alcohol etílico y humectantes para manos limpias.",
        "codigo_barras": "7411001000889",
        "precio_base": D("1.50"),
        "imagen_url": "https://images.unsplash.com/photo-1584483766114-2cea6facdf57?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Protector Solar Nivea Sun Protect & Moisture FPS 50 125ml",
        "descripcion": "Protección UVA/UVB alta resistente al agua y humectación inmediata.",
        "codigo_barras": "7411001000896",
        "precio_base": D("7.90"),
        "imagen_url": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?auto=format&fit=crop&w=600&q=80",
    },

    # --- 9. LIMPIEZA DEL HOGAR (11) ---
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente en Polvo Rinso Rinde Más 1 kg",
        "descripcion": "Detergente para ropa blanca y de color con espuma controlada y rico aroma.",
        "codigo_barras": "7411001000902",
        "precio_base": D("2.40"),
        "imagen_url": "https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente en Polvo Xedex Acción Antibacterial 1 kg",
        "descripcion": "Remueve manchas difíciles y elimina olores atrapados en las fibras.",
        "codigo_barras": "7411001000919",
        "precio_base": D("2.85"),
        "imagen_url": "https://images.unsplash.com/photo-1624372635310-01d078c05dd9?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Suavizante de Telas Suavitel Fresco Aroma 850ml",
        "descripcion": "Deja tu ropa increíblemente suave, fácil de planchar y con aroma duradero.",
        "codigo_barras": "7411001000926",
        "precio_base": D("1.85"),
        "imagen_url": "https://images.unsplash.com/photo-1585421514738-01798e348b17?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Clorox Tradicional Galón 3.78L",
        "descripcion": "Desinfectante clorado multisuperficies y blanqueador concentrado.",
        "codigo_barras": "7411001000933",
        "precio_base": D("2.60"),
        "imagen_url": "https://images.unsplash.com/photo-1584813470613-5b1c1cad3d69?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Limpiador Líquido Fabuloso Lavanda 1 Litro",
        "descripcion": "Limpiador multiusos con aroma a lavanda que neutraliza malos olores.",
        "codigo_barras": "7411001000940",
        "precio_base": D("1.35"),
        "imagen_url": "https://images.unsplash.com/photo-1583947215259-38e31be8751f?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Jabón Líquido Lavaplatos Axion Limón 750ml",
        "descripcion": "Poderoso arrancagrasa concentrado que rinde cientos de platos limpios.",
        "codigo_barras": "7411001000957",
        "precio_base": D("2.10"),
        "imagen_url": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Esponja Salvaúñas Scotch-Brite Pack x2",
        "descripcion": "Fibra verde abrasiva y esponja absorbente con hendidura protectora de uñas.",
        "codigo_barras": "7411001000964",
        "precio_base": D("1.25"),
        "imagen_url": "https://images.unsplash.com/photo-1584634731339-252c581abfc5?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Papel Higiénico Scott Rinde Más 4 Rollos",
        "descripcion": "Rollos dobles con tecnología de hojas acolchadas más suaves y resistentes.",
        "codigo_barras": "7411001000971",
        "precio_base": D("2.10"),
        "imagen_url": "https://images.unsplash.com/photo-1584475784921-d9dbfd9d17ca?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Papel Toalla de Cocina Bounty 2 Rollos",
        "descripcion": "Toallas de papel absorbentes ultra resistentes para limpiar derrames en la cocina.",
        "codigo_barras": "7411001000988",
        "precio_base": D("2.30"),
        "imagen_url": "https://images.unsplash.com/photo-1584820927498-cfe5211fd8bf?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Bolsas de Basura Grandes Rey Pack x10",
        "descripcion": "Bolsas plásticas resistentes tamaño grande para basureros de patio o cocina.",
        "codigo_barras": "7411001000995",
        "precio_base": D("1.75"),
        "imagen_url": "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=600&q=80",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Insecticida Baygon Aerosol Casa y Jardín 400ml",
        "descripcion": "Fórmula eficaz contra moscas, zancudos, cucarachas y hormigas.",
        "codigo_barras": "7411001001008",
        "precio_base": D("3.50"),
        "imagen_url": "https://images.unsplash.com/photo-1587293852726-70cdb56c2866?auto=format&fit=crop&w=600&q=80",
    },
]


def poblar() -> None:
    print(f"Iniciando carga de {len(PRODUCTOS_DATA)} productos en la base de datos...")

    with SessionLocal() as db:
        # 1. Asegurar o crear Categorías
        categorias_existentes = {c.nombre: c for c in db.scalars(select(m.Categoria)).all()}
        categorias_map = {}

        for cat_info in CATEGORIAS_DATA:
            nombre = cat_info["nombre"]
            if nombre in categorias_existentes:
                categorias_map[nombre] = categorias_existentes[nombre]
            else:
                nueva_cat = m.Categoria(
                    nombre=nombre,
                    descripcion=cat_info["descripcion"]
                )
                db.add(nueva_cat)
                db.flush()
                categorias_map[nombre] = nueva_cat
                print(f"  [+] Categoría creada: {nombre}")

        # Si había categorías viejas simples (como 'Comida', 'Baño', 'Hogar', 'Limpieza'), también mapearlas si aplican
        for cat in db.scalars(select(m.Categoria)).all():
            categorias_map[cat.nombre] = cat

        # 2. Obtener sucursales activas para asignar inventario
        sucursales = db.scalars(select(m.Sucursal).where(m.Sucursal.activa.is_(True))).all()
        print(f"Sucursales encontradas para inventario: {len(sucursales)}")

        # 3. Insertar o actualizar Productos
        creados = 0
        actualizados = 0
        inventario_creado = 0

        for p_data in PRODUCTOS_DATA:
            cat_obj = categorias_map.get(p_data["categoria"])
            if not cat_obj:
                print(f"  [!] Categoría no encontrada: {p_data['categoria']}")
                continue

            # Buscar si el producto ya existe por código de barras o por nombre
            producto = None
            if p_data["codigo_barras"]:
                producto = db.scalar(
                    select(m.Producto).where(m.Producto.codigo_barras == p_data["codigo_barras"])
                )
            if not producto:
                producto = db.scalar(
                    select(m.Producto).where(m.Producto.nombre == p_data["nombre"])
                )

            if producto:
                # Actualizar campos
                producto.id_categoria = cat_obj.id_categoria
                producto.descripcion = p_data["descripcion"]
                producto.precio_base = p_data["precio_base"]
                producto.imagen_url = p_data["imagen_url"]
                producto.activo = True
                actualizados += 1
            else:
                # Crear nuevo producto
                producto = m.Producto(
                    id_categoria=cat_obj.id_categoria,
                    codigo_barras=p_data["codigo_barras"],
                    nombre=p_data["nombre"],
                    descripcion=p_data["descripcion"],
                    precio_base=p_data["precio_base"],
                    imagen_url=p_data["imagen_url"],
                    activo=True,
                )
                db.add(producto)
                db.flush()
                creados += 1

            # 4. Asegurar inventario en cada sucursal activa
            for sucursal in sucursales:
                inv = db.scalar(
                    select(m.Inventario).where(
                        m.Inventario.id_sucursal == sucursal.id_sucursal,
                        m.Inventario.id_producto == producto.id_producto,
                    )
                )
                if not inv:
                    db.add(
                        m.Inventario(
                            id_sucursal=sucursal.id_sucursal,
                            id_producto=producto.id_producto,
                            stock_disponible=50,
                        )
                    )
                    inventario_creado += 1

        db.commit()
        print(f"\nProceso finalizado con éxito:")
        print(f"  - Productos nuevos creados: {creados}")
        print(f"  - Productos actualizados: {actualizados}")
        print(f"  - Registros de inventario generados: {inventario_creado}")


if __name__ == "__main__":
    poblar()
