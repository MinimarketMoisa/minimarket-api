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


SEED_PRODUCTS_IMAGES = {
    "Arroz 1 lb": "https://walmartsv.vteximg.com.br/arquivos/ids/894752/M-5_walmartsv_NEDMdLbClp_124672_01.jpg",
    "Frijoles 1 lb": "https://walmartsv.vteximg.com.br/arquivos/ids/738824/63468_01.jpg",
    "Aceite 1 L": "https://walmartsv.vteximg.com.br/arquivos/ids/751028/47494_01.jpg",
    "Jabón de baño": "https://walmartsv.vteximg.com.br/arquivos/ids/865846/jabon-protex-omega-3-3-pack-660-g-0099176922780.webp",
    "Papel higiénico x4": "https://walmartsv.vteximg.com.br/arquivos/ids/904090/papel-higienico-scott-balance-32-ea-2-p-7441008104988.webp",
    "Detergente 1 kg": "https://walmartsv.vteximg.com.br/arquivos/ids/885202/M-5_walmartsv_MODVqOzupG_120250_01.jpg",
    "Cloro 1 galón": "https://walmartsv.vteximg.com.br/arquivos/ids/882994/cloro-great-value-bt-3785-ml-galon-7441078231140.webp",
    "Escoba": "https://walmartsv.vteximg.com.br/arquivos/ids/921183/M-5_walmartsv_XpbvCIAKTl_51839_01.jpg",
    "Vasos plásticos x50": "https://walmartsv.vteximg.com.br/arquivos/ids/771059/46419_01.jpg",
}


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
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/894752/M-5_walmartsv_NEDMdLbClp_124672_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Precocido San Francisco 908g",
        "descripcion": "Arroz precocido grano entero suelto y esponjoso, rendimiento superior.",
        "codigo_barras": "7411001000025",
        "precio_base": D("1.25"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/708129/41519_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Rojo de Seda San Francisco 800g",
        "descripcion": "Frijol rojo salvadoreño de seda, grano suave de cocción rápida.",
        "codigo_barras": "7411001000032",
        "precio_base": D("1.45"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408830/Frijol-Rojo-De-Seda-Sabemas-1816Gr-1-8333.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijoles Rojos Molidos Natura's 400g",
        "descripcion": "Frijoles rojos molidos estilo casero listos para servir.",
        "codigo_barras": "7411001000049",
        "precio_base": D("0.95"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/738824/63468_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Aceite Vegetal Mazola 1 Litro",
        "descripcion": "Aceite vegetal 100% puro libre de colesterol, ideal para freír y cocinar.",
        "codigo_barras": "7411001000056",
        "precio_base": D("2.50"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/733967/50843_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Aceite de Oliva Extra Virgen Carbonell 500ml",
        "descripcion": "Aceite de oliva virgen extra de primera presión en frío, botella de vidrio.",
        "codigo_barras": "7411001000063",
        "precio_base": D("5.90"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/686675/55658_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Azúcar Blanca Cañal 1 kg",
        "descripcion": "Azúcar blanca refinada de alta pureza 100% salvadoreña.",
        "codigo_barras": "7411001000070",
        "precio_base": D("1.10"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/809585/azucar-del-canal-blanca-1000-g-7411500000934.webp",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Harina de Maíz Maseca 1 kg",
        "descripcion": "Harina de maíz nixtamalizado para tortillas, pupusas y tamales.",
        "codigo_barras": "7411001000087",
        "precio_base": D("1.20"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/511205/63294_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Pasta Espagueti Ina 200g",
        "descripcion": "Pasta alimenticia clásica enriquecida con vitaminas y minerales.",
        "codigo_barras": "7411001000094",
        "precio_base": D("0.45"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/698614/71841_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Pasta Coditos Ina 200g",
        "descripcion": "Pasta de sémola de trigo durum en forma de coditos para sopas y ensaladas.",
        "codigo_barras": "7411001000100",
        "precio_base": D("0.45"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/935605/pasta-fama-coditos-200-g-0097294742631.webp",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Salsa de Tomate Ranchera Natura's 210g",
        "descripcion": "Salsa de tomates naturales con cebolla, chile verde y especias.",
        "codigo_barras": "7411001000117",
        "precio_base": D("0.55"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/949578/M-5_walmartsv_XdQjxXJiYH_119088_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Pasta de Tomate Del Fuerte 210g",
        "descripcion": "Pasta concentrada de tomate maduro para guisados y carnes.",
        "codigo_barras": "7411001000124",
        "precio_base": D("0.65"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/851672/pasta-de-tomate-campofresco-87-g-7421001653393.webp",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Atún en Trozos en Agua Sardimar 140g",
        "descripcion": "Lomo de atún aleta amarilla en agua, bajo en grasa y rico en proteína.",
        "codigo_barras": "7411001000131",
        "precio_base": D("1.35"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/721350/48221_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Atún en Trozos en Aceite Calvo 140g",
        "descripcion": "Atún claro en aceite vegetal calidad gourmet en lata abre fácil.",
        "codigo_barras": "7411001000148",
        "precio_base": D("1.40"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/721350/48221_01.jpg",
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Café Molido El Sol Tradicional 400g",
        "descripcion": "Café 100% arábica tostado y molido de estricta altura salvadoreño.",
        "codigo_barras": "7411001000155",
        "precio_base": D("3.25"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/858088/el-manzano-topeca-cafe-molido-340-g-0840186000377.jpg",
    },

    # --- 2. BEBIDAS Y REFRESCOS (12) ---
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Coca-Cola Original 2.5 Litros",
        "descripcion": "Refresco carbonatado sabor original familiar botella PET no retornable.",
        "codigo_barras": "7411001000162",
        "precio_base": D("2.50"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/591882/43832_01.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Coca-Cola Sin Azúcar 1.5 Litros",
        "descripcion": "Gaseosa Coca-Cola sabor original con cero calorías y sin azúcar.",
        "codigo_barras": "7411001000179",
        "precio_base": D("1.60"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/595275/86900_01.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Kolashanpan 1.5 Litros",
        "descripcion": "El sabor salvadoreño único de caña de azúcar en botella de 1.5L.",
        "codigo_barras": "7411001000186",
        "precio_base": D("1.35"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/405967/Gaseosa-Kolashanpan-Mini-12Pk-2304Ml-1-23930.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Pepsi Regular 2 Litros",
        "descripcion": "Refresco de cola refrescante tamaño familiar botella 2L.",
        "codigo_barras": "7411001000193",
        "precio_base": D("1.75"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/605138/50514_01.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa 7Up Lima Limón 1.5 Litros",
        "descripcion": "Refresco carbonatado transparente con sabor natural a lima-limón sin cafeína.",
        "codigo_barras": "7411001000209",
        "precio_base": D("1.30"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/578112/45827_01.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Petit Néctar de Manzana 1 Litro",
        "descripcion": "Néctar de manzana pasteurizado fortificado con vitamina C en envase Tetra Pak.",
        "codigo_barras": "7411001000216",
        "precio_base": D("1.25"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/748174/53528_01.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Kern's Néctar de Melocotón 1 Litro",
        "descripcion": "Delicioso néctar con pulpa de melocotón de textura suave.",
        "codigo_barras": "7411001000223",
        "precio_base": D("1.35"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/682625/53860_01.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Agua Purificada Las Perlitas Galón 3.78L",
        "descripcion": "Agua de mesa 100% purificada con ozono y luz ultravioleta.",
        "codigo_barras": "7411001000230",
        "precio_base": D("1.50"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960607/M-5_walmartsv_EudflbRMAX_50523_01.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Agua Purificada Alpina 600ml",
        "descripcion": "Botella individual de agua purificada ligera con tapa deportiva.",
        "codigo_barras": "7411001000247",
        "precio_base": D("0.50"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/962876/M-5_walmartsv_TTeoGcxQis_109747_01.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gatorade Cool Blue 600ml",
        "descripcion": "Bebida isotónica con electrolitos sabor mora azul para hidratación activa.",
        "codigo_barras": "7411001000254",
        "precio_base": D("1.20"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/881180/bebida-gatorade-berry-blue-500-ml-0024474006818.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Cerveza Pilsener Nacional Lata 355ml",
        "descripcion": "La cerveza tradicional de El Salvador estilo lager rubia refrescante.",
        "codigo_barras": "7411001000261",
        "precio_base": D("1.15"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/385740/Cerveza-Pilsener-Lata-355-Ml-1-3640.jpg",
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Cerveza Golden Extra Lata 355ml",
        "descripcion": "Cerveza tipo golden lager suave, ligera y fácil de tomar.",
        "codigo_barras": "7411001000278",
        "precio_base": D("1.10"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/963520/M-5_walmartsv_YhJiPFKWiz_126472_01.jpg",
    },

    # --- 3. LÁCTEOS Y HUEVOS (12) ---
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Entera Salud 1 Litro UHT",
        "descripcion": "Leche 100% de vaca entera ultrapasteurizada, fortificada con vitamina A y D.",
        "codigo_barras": "7411001000285",
        "precio_base": D("1.55"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/580196/54897_01.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Semidescremada Dos Pinos 1 Litro",
        "descripcion": "Leche semidescremada 2% grasa en envase larga vida Tetra Brik.",
        "codigo_barras": "7411001000292",
        "precio_base": D("1.60"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/579437/52914_01.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Deslactosada Salud 1 Litro",
        "descripcion": "Leche entera deslactosada de fácil digestión para personas intolerantes a la lactosa.",
        "codigo_barras": "7411001000308",
        "precio_base": D("1.75"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/330655/Leche-Deslactosada-Marca-Salud-Semidescremada-2-grasa-1892ml-1-33874.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Crema Pura Especial Salud 400ml",
        "descripcion": "Crema de leche salvadoreña espesa y con sabor tradicional para pupusas o frijoles.",
        "codigo_barras": "7411001000315",
        "precio_base": D("1.65"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/873987/crema-san-julian-pura-especial-340-g-0708916010082.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Quesillo Especial San Julián 1 lb",
        "descripcion": "Quesillo tradicional salvadoreño con el punto exacto de hebra para derretir.",
        "codigo_barras": "7411001000322",
        "precio_base": D("3.25"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/604623/53955_01.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Fresco Petacones 1 lb",
        "descripcion": "Queso duro blando salvadoreño con el sello de calidad inconfundible Petacones.",
        "codigo_barras": "7411001000339",
        "precio_base": D("3.95"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/782180/82438_01.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Crema Philadelphia Clásico 210g",
        "descripcion": "Queso crema para untar, suave y cremoso ideal para postres y tostadas.",
        "codigo_barras": "7411001000346",
        "precio_base": D("2.85"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/604509/51105_01.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Mantequilla con Sal Dos Pinos 115g",
        "descripcion": "Mantequilla de pura crema de leche pasteurizada con sal añadida.",
        "codigo_barras": "7411001000353",
        "precio_base": D("1.15"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/885415/M-5_walmartsv_fOsKqHeyrq_121718_01.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Margarina Mirasol Barra 100g",
        "descripcion": "Margarina clásica con sal enriquecida con vitaminas para repostería y cocina.",
        "codigo_barras": "7411001000360",
        "precio_base": D("0.55"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/789940/69880_01.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Yogur Líquido Yes Fresa 750g",
        "descripcion": "Yogur bebible con probióticos activos sabor fresa natural.",
        "codigo_barras": "7411001000377",
        "precio_base": D("1.85"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/948550/M-5_walmartsv_EbdmhyGSzz_3746_5.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Cartón de Huevos Santa Anita 30 Unidades",
        "descripcion": "Huevos frescos medianos de granja controlada en empaque protector de cartón.",
        "codigo_barras": "7411001000384",
        "precio_base": D("4.95"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408955/Huevo-Marron-Fresco-Grande-30-Unidades-1-12504.jpg",
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Media Cartón de Huevos Santa Anita 15 Unidades",
        "descripcion": "15 huevos frescos seleccionados de cascarón limpio y yema brillante.",
        "codigo_barras": "7411001000391",
        "precio_base": D("2.60"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408974/Huevo-Jumbo-El-Granjero-20unidades-1-25356.jpg",
    },

    # --- 4. SNACKS Y GOLOSINAS (12) ---
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Churritos Diana 150g",
        "descripcion": "Snack de maíz horneado con el inconfundible sabor saladito y crujiente Diana.",
        "codigo_barras": "7411001000407",
        "precio_base": D("0.90"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/694033/65384_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Elotitos Diana con Queso y Chile 150g",
        "descripcion": "Palitos de maíz inflado con cobertura de queso y un toque picante salvadoreño.",
        "codigo_barras": "7411001000414",
        "precio_base": D("0.90"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/694056/45226_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Jalapeños Diana 150g",
        "descripcion": "Crujientes hojuelas de maíz con el auténtico y fuerte sabor a chile jalapeño.",
        "codigo_barras": "7411001000421",
        "precio_base": D("0.90"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/576465/65385_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Quesitos Diana 150g",
        "descripcion": "Aros de maíz crujiente con abundante sabor a queso cheddar.",
        "codigo_barras": "7411001000438",
        "precio_base": D("0.90"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/810270/boquitas-diana-quesitos-maiz-queso-125-g-0748757000149.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Palitos Diana 150g",
        "descripcion": "Palitos de harina de trigo tostados y ligeramente salados, ideales para dip.",
        "codigo_barras": "7411001000445",
        "precio_base": D("0.90"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/930338/M-5_walmartsv_yYgdgRPAXI_45228_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Tortillitas Diana Saladas 150g",
        "descripcion": "Tortillas de maíz tostadas con sal marina, textura extra crujiente.",
        "codigo_barras": "7411001000452",
        "precio_base": D("0.85"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/694033/65384_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Oreo Original Paquete x6",
        "descripcion": "Galletas de sándwich de cacao con crema sabor a vainilla.",
        "codigo_barras": "7411001000469",
        "precio_base": D("1.35"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/706555/48933_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Chiky Chocolate Paquete x6",
        "descripcion": "Galleta crujiente bañada en una rica capa de chocolate con leche Pozuelo.",
        "codigo_barras": "7411001000476",
        "precio_base": D("1.20"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/958159/galletas-pozuelo-chiky-chocolate-480-g-0086581010881.webp",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Club Social Original 6 Pack",
        "descripcion": "Galletas saladas horneadas individuales para llevar a cualquier parte.",
        "codigo_barras": "7411001000483",
        "precio_base": D("1.25"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/709619/51128_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Papas Fritas Lay's Clásicas 110g",
        "descripcion": "Hojuelas de papa natural fritas y sazonadas con el toque exacto de sal.",
        "codigo_barras": "7411001000490",
        "precio_base": D("1.65"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/518659/49437_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Papas Pringles Original Tubo 149g",
        "descripcion": "Papas tostadas en tubo apilables con forma hiperbólica perfecta.",
        "codigo_barras": "7411001000506",
        "precio_base": D("2.45"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/776350/110620_01.jpg",
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Snickers Barra 52.7g",
        "descripcion": "Barra de chocolate con leche rellena de turrón, caramelo y cacahuates.",
        "codigo_barras": "7411001000513",
        "precio_base": D("0.95"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/826837/chocolate-snickers-almendras-barra-49-9-g-0040000001058.jpg",
    },

    # --- 5. EMBUTIDOS Y CARNES (8) ---
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha de Pavo Toledo Paquete 454g",
        "descripcion": "Salchichas bajas en grasa de pura carne de pavo empacadas al vacío.",
        "codigo_barras": "7411001000520",
        "precio_base": D("2.10"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/702852/80570_01.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Viena Toledo 200g",
        "descripcion": "Salchicha estilo viena condimentada ideal para panchos o guisados.",
        "codigo_barras": "7411001000537",
        "precio_base": D("0.95"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/705950/43595_01.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón de Pierna Cocido Toledo 250g",
        "descripcion": "Rebanadas delgadas de jamón de pierna curado y cocido.",
        "codigo_barras": "7411001000544",
        "precio_base": D("2.30"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/861410/jamon-fud-ahumado-selva-negra-350-g-7441008931256.webp",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Tocineta Ahumada Rebanada Toledo 200g",
        "descripcion": "Tiras de tocino de cerdo ahumadas con maderas finas listas para dorar.",
        "codigo_barras": "7411001000551",
        "precio_base": D("2.65"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/669026/65318_01.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Pechuga de Pollo Deshuesada Pollo Indio 1 lb",
        "descripcion": "Pechuga de pollo fresca sin piel ni hueso, corte limpio certificado.",
        "codigo_barras": "7411001000568",
        "precio_base": D("3.45"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/878648/pechuga-de-pollo-indio-deshuesada-y-marinada-precio-indicado-por-libra-354-g-2594170000000.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Carne Molida Especial de Res 1 lb",
        "descripcion": "Carne molida 90% magra de res fresca salvadoreña sin aditivos.",
        "codigo_barras": "7411001000575",
        "precio_base": D("3.85"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/873038/carne-molida-super-especial-precio-indicado-por-libra-454-g-2523220000004.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Chorizos Criollos San Miguel 400g",
        "descripcion": "Chorizos estilo tradicional oriental con hierbas aromáticas y achiote.",
        "codigo_barras": "7411001000582",
        "precio_base": D("2.80"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/663402/98897_01.jpg",
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón de Pavo Virginia Zwan 250g",
        "descripcion": "Jamón virginia de pechuga de pavo ahumado bajo en sodio.",
        "codigo_barras": "7411001000599",
        "precio_base": D("2.75"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/481469/78221_01.jpg",
    },

    # --- 6. PANADERÍA Y DESAYUNO (8) ---
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Blanco Mediano Bimbo 560g",
        "descripcion": "Pan de caja clásico con leche y calcio para sándwiches suaves.",
        "codigo_barras": "7411001000605",
        "precio_base": D("1.95"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/801228/pan-blanco-bimbo-mediano-450-g-7441029556759.webp",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Integral 100% Bimbo 680g",
        "descripcion": "Pan elaborado con grano entero y fibra dietética para cuidar tu salud.",
        "codigo_barras": "7411001000612",
        "precio_base": D("2.40"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/821699/pan-cuadrado-bimbo-integral-100-grano-entero-530-g-7441029500325.webp",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan para Hamburguesa Bimbo Bimbollos 8u",
        "descripcion": "Bollos suaves con ajonjolí tostado listos para hamburguesas caseras.",
        "codigo_barras": "7411001000629",
        "precio_base": D("2.15"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/821684/pan-bimbo-para-super-hamburguesa-4-piezas-320-g-7441029507768.webp",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan para Hot Dog Bimbo Medias Noches 8u",
        "descripcion": "Pan alargado esponjoso para preparar perros calientes con facilidad.",
        "codigo_barras": "7411001000636",
        "precio_base": D("1.95"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/875237/pan-bimbo-hot-dog-sin-ajonjoli-8-piezas-325-g-7441029500301.webp",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Tostadas Clásicas Bimbo 210g",
        "descripcion": "Rebanadas de pan tostado crujientes enriquecidas con vitaminas.",
        "codigo_barras": "7411001000643",
        "precio_base": D("1.45"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/821714/tortilla-bimbo-trigo-burritos-clasicas-5-uds-250-g-7441029555653.webp",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Corn Flakes Kellogg's 380g",
        "descripcion": "Hojuelas de maíz tostadas sin gluten añadidas con hierro y vitaminas B.",
        "codigo_barras": "7411001000650",
        "precio_base": D("2.70"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/623757/59182_01.jpg",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Zucaritas Kellogg's 400g",
        "descripcion": "Ricas hojuelas de maíz azucaradas para despertar la energía del tigre.",
        "codigo_barras": "7411001000667",
        "precio_base": D("3.15"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/741361/63319_01.jpg",
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Avena en Hojuelas Quaker 360g",
        "descripcion": "Avena de grano entero rica en fibra soluble para el colesterol y digestión.",
        "codigo_barras": "7411001000674",
        "precio_base": D("1.25"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/806701/avena-en-hojuelas-quaker-mosh-1200-g-0803275306378.webp",
    },

    # --- 7. FRUTAS Y VERDURAS (10) ---
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Tomate de Cocina Maya 1 lb",
        "descripcion": "Tomates frescos seleccionados de madurez media para salsas y guisos.",
        "codigo_barras": "7411001000681",
        "precio_base": D("0.65"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/934692/tomate-de-cocina-2-a-4-unidades-precio-indicado-por-libra-454-g-2546640000003.webp",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Cebolla Blanca Importada 1 lb",
        "descripcion": "Cebollas blancas firmes y frescas de bulbo limpio.",
        "codigo_barras": "7411001000698",
        "precio_base": D("0.75"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/454576/Cebolla-Blanca-Precio-Indicado-Por-Libra-454-G-1-83.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Cebolla Morada Fresca 1 lb",
        "descripcion": "Cebolla morada crujiente ideal para curtidos, ensaladas y mariscos.",
        "codigo_barras": "7411001000704",
        "precio_base": D("0.85"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/860082/cebolla-hurtifruti-morada-precio-por-libra-2-a-4-unidades-por-lb-aproximadamente-2595500000004.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Papa Blanca Lavada 1 lb",
        "descripcion": "Papa blanca lisa de pulpa suave perfecta para puré, fritas o sopas.",
        "codigo_barras": "7411001000711",
        "precio_base": D("0.70"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395181/Papa-Soloma-Libra-1-87.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Chile Verde Dulce Unidad",
        "descripcion": "Chile pimiento verde fresco con piel gruesa y aromática.",
        "codigo_barras": "7411001000728",
        "precio_base": D("0.35"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/859980/chile-verde-grande-1-unidad-0000000074858.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Limón Pérsico Jugoso Bolsa 1 lb",
        "descripcion": "Limones verdes sin semilla con abundante jugo natural.",
        "codigo_barras": "7411001000735",
        "precio_base": D("0.90"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395451/Limon-Persico-10-Unidades-1-10249.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Plátano Maduro de Primera Unidad",
        "descripcion": "Plátano maduro con dulzura perfecta para canoas, fritos o sancochados.",
        "codigo_barras": "7411001000742",
        "precio_base": D("0.40"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/812119/snack-pro-platano-maduro-70-9-g-7441005714838.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Roja Gala Unidad",
        "descripcion": "Manzana dulce importada de pulpa firme y cáscara brillante.",
        "codigo_barras": "7411001000759",
        "precio_base": D("0.60"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395431/Manzana-Gala-Paquete-6-Unidades-1-12514.jpg",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Banano Criollo Racimo 5 Unidades",
        "descripcion": "Bananos dulces madurados al punto ricos en potasio y energía.",
        "codigo_barras": "7411001000766",
        "precio_base": D("0.75"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/868677/guineo-hortifruti-de-seda-5-a-7-unidades-precio-indicado-por-libra-454-g-2574500000009.webp",
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Zanahoria Fresca Lavada 1 lb",
        "descripcion": "Zanahorias dulces crocantes listas para picar, cocinar o rallar.",
        "codigo_barras": "7411001000773",
        "precio_base": D("0.55"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/757676/50476_01.jpg",
    },

    # --- 8. CUIDADO PERSONAL (12) ---
    {
        "categoria": "Cuidado Personal",
        "nombre": "Pasta Dental Colgate Triple Acción 100ml",
        "descripcion": "Protección anticaries, dientes blancos y aliento fresco con menta original.",
        "codigo_barras": "7411001000780",
        "precio_base": D("1.40"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/944908/pasta-dental-colgate-triple-accion-75-ml-7509546000985.webp",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Cepillo Dental Colgate Zig Zag Pack x2",
        "descripcion": "Cerdas en ángulo multi-nivel para una limpieza profunda entre los dientes.",
        "codigo_barras": "7411001000797",
        "precio_base": D("1.75"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/902887/cepillo-de-dientes-colgate-zig-zag-carbon-3-uds-8718951179912.webp",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón de Tocador Protex Avena Antibacterial 110g",
        "descripcion": "Elimina el 99.9% de bacterias mientras humecta y cuida la piel con avena.",
        "codigo_barras": "7411001000803",
        "precio_base": D("0.95"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/869102/jabon-protex-carbon-6-pack-6-60-g-7509546690773.webp",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón de Tocador Palmolive Naturals Oliva 110g",
        "descripcion": "Sensación humectante y fragancia suave con extracto de oliva y aloe.",
        "codigo_barras": "7411001000810",
        "precio_base": D("0.85"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/903702/jabon-de-tocador-palmolive-naturals-mixto-4-pack-400-g-7509546683072.webp",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Champú Head & Shoulders Limpieza Renovadora 375ml",
        "descripcion": "Fórmula dermasense para hasta 100% libre de caspa y cabello fresco.",
        "codigo_barras": "7411001000827",
        "precio_base": D("4.50"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/733076/100627_01.jpg",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Champú Pantene Pro-V Restauración 400ml",
        "descripcion": "Ayuda a reparar el cabello dañado desde la raíz hasta las puntas.",
        "codigo_barras": "7411001000834",
        "precio_base": D("4.25"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/206664/Acondicionador-Pantene-Pro-V-Restauraci-n-200Ml-1-4101.jpg",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Desodorante Rexona Men Cobalt Roll-On 50ml",
        "descripcion": "Protección antitranspirante 48 horas activada por el movimiento.",
        "codigo_barras": "7411001000841",
        "precio_base": D("2.20"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/915230/rexona-m-aob-deo-aero-active-150-ml-7791293051581.jpg",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Desodorante Lady Speed Stick Fresh Fusion Roll-On 50ml",
        "descripcion": "Control del sudor y olor con aroma femenino y sin dejar manchas blancas.",
        "codigo_barras": "7411001000858",
        "precio_base": D("2.15"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/895108/desodorante-lady-speed-stick-clinical-complete-aerosol-150-ml-7509546073828.webp",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Crema Corporal Nivea Milk Nutritiva 250ml",
        "descripcion": "Infusión de serum de hidratación profunda y aceite de almendras para piel seca.",
        "codigo_barras": "7411001000865",
        "precio_base": D("3.80"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/950414/crema-corporal-nivea-milk-nutricion-y-humectacion-profunda-400-ml-7501054504535.webp",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Toallas Sanitarias Kotex Nocturnas con Alas 10u",
        "descripcion": "Máxima absorción y protección durante toda la noche con tecnología anti-derrames.",
        "codigo_barras": "7411001000872",
        "precio_base": D("1.65"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/816948/toallas-femeninas-kotex-sport-14-unidades-7441008172536.webp",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Alcohol en Gel Antibacterial Germ-X 250ml",
        "descripcion": "Gel desinfectante con 70% de alcohol etílico y humectantes para manos limpias.",
        "codigo_barras": "7411001000889",
        "precio_base": D("1.50"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/892249/M-5_walmartsv_mHVbrIyced_115305_01.jpg",
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Protector Solar Nivea Sun Protect & Moisture FPS 50 125ml",
        "descripcion": "Protección UVA/UVB alta resistente al agua y humectación inmediata.",
        "codigo_barras": "7411001000896",
        "precio_base": D("7.90"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/526552/73035_01.jpg",
    },

    # --- 9. LIMPIEZA DEL HOGAR (11) ---
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente en Polvo Rinso Rinde Más 1 kg",
        "descripcion": "Detergente para ropa blanca y de color con espuma controlada y rico aroma.",
        "codigo_barras": "7411001000902",
        "precio_base": D("2.40"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/885202/M-5_walmartsv_MODVqOzupG_120250_01.jpg",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente en Polvo Xedex Acción Antibacterial 1 kg",
        "descripcion": "Remueve manchas difíciles y elimina olores atrapados en las fibras.",
        "codigo_barras": "7411001000919",
        "precio_base": D("2.85"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/871708/det-polvo-xedex-pe-suav-lavanda-900-gr-7401001695319.jpg",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Suavizante de Telas Suavitel Fresco Aroma 850ml",
        "descripcion": "Deja tu ropa increíblemente suave, fácil de planchar y con aroma duradero.",
        "codigo_barras": "7411001000926",
        "precio_base": D("1.85"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/940980/suavizante-de-telas-suavitel-complete-aqua-720-ml-7509546692098.webp",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Clorox Tradicional Galón 3.78L",
        "descripcion": "Desinfectante clorado multisuperficies y blanqueador concentrado.",
        "codigo_barras": "7411001000933",
        "precio_base": D("2.60"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/919974/M-5_walmartsv_rfooapKyKh_51485_01.jpg",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Limpiador Líquido Fabuloso Lavanda 1 Litro",
        "descripcion": "Limpiador multiusos con aroma a lavanda que neutraliza malos olores.",
        "codigo_barras": "7411001000940",
        "precio_base": D("1.35"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/914156/desinfectante-fabuloso-multiusos-frescura-activa-antibacterial-lavanda-900-ml-0099176132608.webp",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Jabón Líquido Lavaplatos Axion Limón 750ml",
        "descripcion": "Poderoso arrancagrasa concentrado que rinde cientos de platos limpios.",
        "codigo_barras": "7411001000957",
        "precio_base": D("2.10"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/864989/lavaplatos-axion-limon-liquido-1-5-l-7702010382079.webp",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Esponja Salvaúñas Scotch-Brite Pack x2",
        "descripcion": "Fibra verde abrasiva y esponja absorbente con hendidura protectora de uñas.",
        "codigo_barras": "7411001000964",
        "precio_base": D("1.25"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/734043/64561_01.jpg",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Papel Higiénico Scott Rinde Más 4 Rollos",
        "descripcion": "Rollos dobles con tecnología de hojas acolchadas más suaves y resistentes.",
        "codigo_barras": "7411001000971",
        "precio_base": D("2.10"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/905702/papel-higienico-scott-rindemax-doble-hoja-4-rollos-7441008168324.webp",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Papel Toalla de Cocina Bounty 2 Rollos",
        "descripcion": "Toallas de papel absorbentes ultra resistentes para limpiar derrames en la cocina.",
        "codigo_barras": "7411001000988",
        "precio_base": D("2.30"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/723002/46334_01.jpg",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Bolsas de Basura Grandes Rey Pack x10",
        "descripcion": "Bolsas plásticas resistentes tamaño grande para basureros de patio o cocina.",
        "codigo_barras": "7411001000995",
        "precio_base": D("1.75"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/534003/75111_01.jpg",
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Insecticida Baygon Aerosol Casa y Jardín 400ml",
        "descripcion": "Fórmula eficaz contra moscas, zancudos, cucarachas y hormigas.",
        "codigo_barras": "7411001001008",
        "precio_base": D("3.50"),
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/578632/50916_01.jpg",
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
                elif inv.stock_disponible < 10:
                    inv.stock_disponible = 50

        # 5. Asegurar imágenes oficiales e inventario para los productos base de la semilla (seed)
        seed_actualizados = 0
        for nombre_seed, url_seed in SEED_PRODUCTS_IMAGES.items():
            prod_seed = db.scalar(select(m.Producto).where(m.Producto.nombre == nombre_seed))
            if prod_seed:
                prod_seed.imagen_url = url_seed
                prod_seed.activo = True
                seed_actualizados += 1
                for sucursal in sucursales:
                    inv_s = db.scalar(
                        select(m.Inventario).where(
                            m.Inventario.id_sucursal == sucursal.id_sucursal,
                            m.Inventario.id_producto == prod_seed.id_producto,
                        )
                    )
                    if not inv_s:
                        db.add(m.Inventario(id_sucursal=sucursal.id_sucursal, id_producto=prod_seed.id_producto, stock_disponible=50))
                    elif inv_s.stock_disponible < 10:
                        inv_s.stock_disponible = 50

        db.commit()

        # 6. Verificación exhaustiva: Ningún producto debe quedar sin imagen
        productos_sin_imagen = db.scalars(
            select(m.Producto).where(
                (m.Producto.imagen_url.is_(None)) | (m.Producto.imagen_url == "")
            )
        ).all()
        total_productos = len(db.scalars(select(m.Producto)).all())

        print(f"\nProceso finalizado con éxito:")
        print(f"  - Productos nuevos creados: {creados}")
        print(f"  - Productos actualizados: {actualizados}")
        print(f"  - Productos semilla actualizados con imagen: {seed_actualizados}")
        print(f"  - Registros de inventario generados: {inventario_creado}")
        print(f"  - Total de productos en base de datos: {total_productos}")
        if productos_sin_imagen:
            print(f"  [ALERTA] Productos aún sin imagen: {len(productos_sin_imagen)}")
            for p in productos_sin_imagen:
                print(f"    * ID {p.id_producto}: {p.nombre}")
        else:
            print(f"  [OK] ¡100% de productos tienen imagen oficial asignada (0 faltantes)!\n")


if __name__ == "__main__":
    poblar()
