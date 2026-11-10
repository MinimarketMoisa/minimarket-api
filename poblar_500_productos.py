"""
Script optimizado de bajo consumo de memoria (para VPS con 1 GB RAM) para poblar
la base de datos con 500+ productos reales salvadoreños (Walmart SV / Despensa de Don Juan).

Ejecuta en lotes de 50 registros liberando la sesión SQLAlchemy tras cada lote.

Uso:
    python poblar_500_productos.py
"""

import gc
from decimal import Decimal
from sqlalchemy import select
from app import models as m
from app.database import SessionLocal
import poblar_100_productos as p100


def D(valor) -> Decimal:
    return Decimal(str(valor))


PRODUCTOS_ADICIONALES = [
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Salpor De Arroz Und.",
        "descripcion": "El salpor de arroz es un delicioso pan dulce típico empacado. De textura suave y sabor ligeramente dulce, es ideal para acompañar bebidas calientes. Perfecto para disfrutar en cualquier momento del día. Su empaque garantiza la frescura y calidad del producto. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0000000002653",
        "precio_base": "0.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/402159/Salpor-De-Arroz-Und-1-9.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Jasmine Dynasty -907g",
        "descripcion": "Disfruta Arroz Jasmine Dynasty 907 g, una opción práctica que se convierte en tu aliada de todos los días. Cuenta con varias ventajas: su presentación facilita medir la porción justa para cada ocasión; es una opción versátil para acompañar comidas, postres o reuniones; es fácil de incorporar en recetas, loncheras o meriendas rápidas; su empaque práctico permite conservarlo en buen estado hasta el momento de servirlo; su formato facilita compartirlo en familia o guardarlo para más adelant...",
        "codigo_barras": "0011152263557",
        "precio_base": "5.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/576536/78106_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Blanco San Francisco 1816gr",
        "descripcion": "El arroz blanco San Francisco en su presentación de 1816 g, es una opción práctica para preparar acompañamientos y comidas caseras de uso diario. Puede utilizarse en arroz blanco, gallo pinto, arroz con vegetales, sopas, guarniciones, bowls, ensaladas frías o preparaciones con pollo, carne, pescado y legumbres. Su formato permite mantener una cantidad rendidora en la despensa para almuerzos y cenas familiares. Es una alternativa conveniente para hogares que buscan un ingrediente básico y...",
        "codigo_barras": "7411000501276",
        "precio_base": "2.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/894752/M-5_walmartsv_NEDMdLbClp_124672_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Precocido Papadan 454 Gr",
        "descripcion": "El arroz precocido Papadan en presentación de 454 g es un producto de alta calidad, ideal para quienes buscan un grano suelto, suave y de sabor neutro para complementar sus comidas diarias. Su textura ligera y cocción uniforme lo convierten en el acompañante perfecto para una gran variedad de platillos, desde guisos tradicionales hasta recetas más elaboradas. Empacado cuidadosamente para conservar su frescura y pureza, este arroz garantiza resultados consistentes en cada preparación. Su ...",
        "codigo_barras": "7410010749135",
        "precio_base": "0.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/773621/110161_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Blanco As De Oros 1816 Gr",
        "descripcion": "Prueba Arroz Blanco As De Oros 1816 g y encuentra un nuevo favorito para tu mesa de cada día. Cuenta con varias ventajas: su presentación facilita medir la porción justa para cada ocasión; se integra sin complicaciones a tu lista de compras semanal; su empaque práctico permite conservarlo en buen estado hasta el momento de servirlo; su sabor y textura lo hacen apto tanto para grandes como para chicos; su formato facilita compartirlo en familia o guardarlo para más adelante; es una opción...",
        "codigo_barras": "0822325000295",
        "precio_base": "2.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/920612/arroz-blanco-as-de-oros-1816-gr-0822325000295.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Omoa Blanco 1814 g",
        "descripcion": "Arroz Omoa Blanco 1814 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411400300394",
        "precio_base": "2.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/470821/48393_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Harina De Arroz As De Oros 1.81 Kg",
        "descripcion": "Harina De Arroz As De Oros 1.81 Kg el producto indispensable en tu despensa diseñado para convertirse en la base o el sazón perfecto de tus comidas. Destaca por su gran rendimiento, calidad y versatilidad culinaria, siendo una alternativa ideal para enriquecer, preparar o complementar una amplia variedad de platillos y recetas. Un componente esencial que garantiza consistencia y un excelente sabor en tu mesa.",
        "codigo_barras": "7411400100598",
        "precio_base": "2.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/954464/M-5_walmartsv_moMoujVIIk_69367_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Omoa Blanco 1362 g",
        "descripcion": "Arroz Omoa Blanco 1362 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411400300325",
        "precio_base": "1.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/949873/M-5_walmartsv_TnCFqernZC_48392_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Precocido 3B 400 g",
        "descripcion": "Arroz Precocido 3B 400 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411400300417",
        "precio_base": "0.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/957949/arroz-precocido-3-b-400-g-7411400300417.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Omoa Precocido 1814 g",
        "descripcion": "Arroz Omoa Precocido 1814 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411400300400",
        "precio_base": "2.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/470854/48394_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Precocido As De Oros 1816 Gr",
        "descripcion": "Suma Arroz Precocido As De Oros 1816 g a tu carrito y ten una opción lista para cualquier antojo. Cuenta con varias ventajas: resulta cómodo de transportar, ya sea para la casa, el trabajo o un paseo; su empaque práctico permite conservarlo en buen estado hasta el momento de servirlo; su sabor y textura lo hacen apto tanto para grandes como para chicos; su presentación facilita medir la porción justa para cada ocasión; se integra sin complicaciones a tu lista de compras semanal; su forma...",
        "codigo_barras": "0822325000257",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/905390/M-5_walmartsv_TOiWpgnIBd_125065_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Harina de arroz Suamiga -11.34 kg.",
        "descripcion": "Harina De Arroz Suamiga 11.34 Kg el producto indispensable en tu despensa diseñado para convertirse en la base o el sazón perfecto de tus comidas. Destaca por su gran rendimiento, calidad y versatilidad culinaria, siendo una alternativa ideal para enriquecer, preparar o complementar una amplia variedad de platillos y recetas. Un componente esencial que garantiza consistencia y un excelente sabor en tu mesa.",
        "codigo_barras": "7411000501436",
        "precio_base": "11.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/709037/89755_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz San Francisco precocido -454 g",
        "descripcion": "Arroz San Francisco Precocido 454 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411000511114",
        "precio_base": "0.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/708088/41517_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "2pack Arroz Precocido As De Oros 908 Gr",
        "descripcion": "Renueva tu despensa con 2 unidades Arroz Precocido As De Oros 908 g, pensado para quienes disfrutan probar algo distinto. Cuenta con varias ventajas: es una opción versátil para acompañar comidas o reuniones; su sabor y textura lo hacen apto tanto para grandes como para chicos; se integra sin complicaciones a tu lista de compras semanal; es fácil de incorporar en recetas, loncheras o meriendas rápidas; su formato facilita compartirlo en familia o guardarlo para más adelante; su presentac...",
        "codigo_barras": "0822325000318",
        "precio_base": "1.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/920637/2-pack-arroz-precocido-as-de-oros-908-gr-0822325000318.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Harina Omoa De Arroz - 2270 g",
        "descripcion": "El ingrediente esencial para una cocina saludable y versátil. Elaborada a partir de arroz selecto, esta harina es un básico imprescindible en tu despensa, ideal para aquellos que buscan alternativas sin gluten y nutritivas. Versatilidad en la Cocina:** Úsala para preparar panes, bizcochos, tortillas, crepes, salsas, rebozados y mucho más. Su textura fina y suave garantiza resultados excepcionales en cada preparación. ¡Disfruta de su sabor neutro y su textura excepcional en todas tus prep...",
        "codigo_barras": "6009230010128",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/807107/harina-omoa-de-arroz-2270-g-6009230010128.webp"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Cinco Estrellas blanco -454 g",
        "descripcion": "Arroz Cinco Estrellas Blanco 454 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411000505014",
        "precio_base": "0.76",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/708101/41515_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Mr Rice Precocido 1816 g",
        "descripcion": "Arroz Mr Rice Precocido 1816 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411000591314",
        "precio_base": "2.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/478733/69363_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Cinco Estrellas Blanco 2270 g",
        "descripcion": "Arroz Cinco Estrellas Blanco 2270 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411000505052",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/511021/41516_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Suli Blanco - 1816 g",
        "descripcion": "Arroz blanco Suli de alta calidad, ideal para preparar todo tipo de platillos. Su grano largo y esponjoso garantiza una excelente textura y sabor en cada bocado. Presentación de 1816g.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7411000590461",
        "precio_base": "2.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/469947/41520_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Harina De Arroz Omoa - 908 g",
        "descripcion": "Descubre la Harina de Arroz Omoa, tu aliada perfecta para una alimentación equilibrada y deliciosa. Con su presentación de 908 gramos, esta harina de arroz de la reconocida marca OMOA te ofrece un mundo de posibilidades culinarias, ideal para personas con sensibilidad al gluten o que simplemente buscan alternativas nutritivas en su dieta.",
        "codigo_barras": "6009230010012",
        "precio_base": "1.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/826785/harina-de-arroz-omoa-908-g-6009230010012.webp"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz 3B Precocido 2Pack 3200 g",
        "descripcion": "Arroz precocido en empaque de 2 unidades, marca 3B. Perfecto para cocinar en menos tiempo, con la misma cantidad de nutrientes del arroz tradicional. Contenido total de 3200 g Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "8415031001766",
        "precio_base": "5.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/405651/2-Pack-Arroz-3B-Precocido-3200Gr-1-2190.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Sabemas Precocido - 2270 g",
        "descripcion": "Arroz precocido Sabemas, perfecto para una cocción rápida y fácil, ideal para acompañar tus comidas favoritas. Presentación de 2270 gramos, excelente calidad y sabor garantizado.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7411000500422",
        "precio_base": "3.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/576574/41507_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Omoa Blanco 2Pack De 354 g",
        "descripcion": "Arroz Omoa Blanco 2Pack De 354 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "6009230010029",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/714241/54418_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Arroz Suli Precocido - 1816 g",
        "descripcion": "Arroz precocido Suli de alta calidad, ideal para preparar comidas rápidas y deliciosas. Este arroz ha sido previamente cocido para reducir el tiempo de cocción en casa. Viene en un empaque de 1816 g, perfecto para grandes familias o eventos. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7411000590478",
        "precio_base": "2.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/385734/Arroz-Suli-Precocido-1816-Gr-1-1431.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Rojo Papadan, de seda -1816g",
        "descripcion": "Frijol Rojo Papadan, de seda -1816g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7410010749012",
        "precio_base": "5.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/576222/45964_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Entero Negro Sierra 560gr",
        "descripcion": "Frijoles La Sierra Enteros Negros En Lata - 560 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7501052424606",
        "precio_base": "2.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/963390/M-5_walmartsv_cHmytTtXGc_115544_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Ducal Frijol Molido Negro 794 g",
        "descripcion": "Disfruta el auténtico sabor casero con los Frijoles Ducal Volteados Negros en su presentación de 794 g. Listos para servir, ofrecen una textura suave y un sabor delicioso que recuerda a los frijoles hechos en casa. Son ideales como acompañamiento, para rellenar tortillas, pupusas, burritos o preparar tus platillos favoritos de forma rápida y práctica. Están elaborados con ingredientes de alta calidad y sin conservantes artificiales, lo que los convierte en una opción nutritiva y convenie...",
        "codigo_barras": "0088313008968",
        "precio_base": "1.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/897037/M-5_walmartsv_JNFtuyHQqw_95508_5.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Rojo De Seda Sabemas 1816 g",
        "descripcion": "Frijol rojo de seda Sabemas de 1816 g, compuesto por frijoles rojos enteros procesados cuidadosamente. La gran cantidad se adapta a familias numerosas o a quienes compran en volumen. Los frijoles rojos enteros requieren remojo previo durante varias horas y posterior cocción para ablandarse adecuadamente. Una vez cocidos, se usan en arroces con frijoles, guisos, ensaladas o como acompañamiento de diferentes platillos. La marca Sabemas es reconocida por ofrecer productos confiables. Propor...",
        "codigo_barras": "7411400800658",
        "precio_base": "5.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408830/Frijol-Rojo-De-Seda-Sabemas-1816Gr-1-8333.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Sabemas De Seda - 908 g",
        "descripcion": "Frijol de seda Sabemas, calidad superior. Ideal para diversas recetas culinarias, textura suave y sabor delicioso. Perfecto para acompañar tus comidas diarias. - 908grInformación del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7411400800641",
        "precio_base": "2.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/576296/48396_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Omoa rojo - 908 g",
        "descripcion": "El frijol rojo Omoa en presentación de 908 g es una opción práctica para preparar comidas tradicionales y recetas de uso frecuente en el hogar. Puede utilizarse en sopas, guisos, arroces, acompañamientos y otras preparaciones caseras, permitiendo adaptarlo a diferentes estilos de cocina según la preferencia familiar. Su formato resulta conveniente para disponer de varias porciones y organizar mejor el uso del producto dentro de la despensa. Esta presentación facilita medir la cantidad ne...",
        "codigo_barras": "7411400300240",
        "precio_base": "2.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/470847/48388_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Entero La Sierra Charros 560gr",
        "descripcion": "Frijol La Sierra Entero Charro - 560 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7501052424620",
        "precio_base": "2.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/845891/frijol-entero-la-sierra-charros-560-gr-7501052424620.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Dilosa Rojo De Seda 908 g",
        "descripcion": "Frijol Dilosa Rojo De Seda 908 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "0822325000028",
        "precio_base": "2.7",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960515/M-5_walmartsv_ShqxgRZZNu_91844_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol De Seda As De Oros 2Pack 1814 g",
        "descripcion": "El frijol de seda As de Oros 2 pack de 1814 g es una opción práctica y versátil para preparar comidas tradicionales con una textura suave y un sabor que se adapta muy bien a distintas recetas caseras. Su presentación en dos unidades facilita organizar el consumo y contar con una alternativa rendidora para desayunos, almuerzos y cenas, ya sea acompañado con arroz, tortillas, queso, huevos o carnes. Puede utilizarse en sopas, guisos, frijoles cocidos o como base de preparaciones típicas de...",
        "codigo_barras": "0822325000448",
        "precio_base": "10.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/702118/54126_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Omoa Negro - 908 g",
        "descripcion": "Frijol Omoa Negro - 908 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7411400300356",
        "precio_base": "2.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/850946/frijol-omoa-negro-908-g-7411400300356.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Frijolitos Rojo De Seda 1814 g",
        "descripcion": "Frijol rojo de seda de alta calidad Mis Frijolitos, ideal para preparar una gran variedad de platillos. Empacado en una bolsa resistente de 1814 g, perfecto para mantener su frescura y sabor. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7410010428023",
        "precio_base": "5.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/409093/Frijol-Rojo-De-Seda-Mis-Frijolitos-1814gr-1-33355.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Rojo San Francisco 2pack 3632gr",
        "descripcion": "El frijol rojo San Francisco 2 pack en su presentación de 3632 g ofrece un formato de gran capacidad para preparar comidas familiares, reuniones o varias recetas durante la semana. Puede utilizarse en sopas, guisos, arroces, ensaladas, rellenos, dips y platos tradicionales, combinándose con carnes, vegetales, especias y otros acompañamientos. La modalidad de dos paquetes facilita organizar el consumo, abrir una unidad a la vez y mantener la otra reservada para uso posterior. Su cantidad ...",
        "codigo_barras": "7411000591567",
        "precio_base": "9.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/894722/M-5_walmartsv_ZpvwOWPMqp_124673_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Bayo Entero La Sierra 560gr",
        "descripcion": "Frijoles La Sierra Enteros Bayos - 560 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7501052424613",
        "precio_base": "2.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/845890/frijol-bayo-entero-la-sierra-560-gr-7501052424613.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Rigua Elote Riogran De Frijol 640 g",
        "descripcion": "La rigua Rio Grande de frijol en presentación de 640 g es una alternativa práctica para resolver comidas o meriendas de forma sencilla dentro del hogar. Su formato resulta conveniente para compartir en desayunos, cenas ligeras o antojos durante el día, pudiendo acompañarse con crema, queso, salsas u otros complementos según la preferencia. Esta presentación permite disponer de varias porciones en un solo empaque, lo que facilita organizar mejor el consumo familiar o servir una cantidad a...",
        "codigo_barras": "0738529004635",
        "precio_base": "3.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/472253/81463_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol rojo San Francisco - 1816 g",
        "descripcion": "El frijol rojo San Francisco en su presentación de 1816 g es un ingrediente básico para preparar distintas comidas de estilo tradicional y recetas caseras. Puede cocinarse para servir como acompañamiento de arroz, carnes, huevos y otros alimentos, utilizarse en sopas y guisos o convertirse en la base de preparaciones con frijoles molidos. También puede combinarse con arroz para elaborar platos completos o incorporarse a rellenos y otras recetas según la costumbre de cada hogar. Su cantid...",
        "codigo_barras": "7411000507636",
        "precio_base": "5.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/895147/M-5_walmartsv_PfAAIkNVXy_124674_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "La Chula Frijol Rojo Molido 737 g",
        "descripcion": "La Chula Frijol Rojo Molido 737 g",
        "codigo_barras": "7410030504516",
        "precio_base": "1.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/895138/M-5_walmartsv_uqgYOPdNpb_123774_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol rojo San Francisco - 908 g",
        "descripcion": "El frijol rojo San Francisco en su presentación de 908 g, ofrece una opción práctica para preparar recetas tradicionales y acompañamientos de uso frecuente en la cocina. Su formato permite cocinar porciones según la cantidad de personas y utilizar los frijoles en sopas, guisos, casamientos, refritos, ensaladas y otros platos según la preferencia. San Francisco presenta una alternativa conveniente para mantener en la despensa y contar con un ingrediente básico para almuerzos y cenas famil...",
        "codigo_barras": "7411000506035",
        "precio_base": "2.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/895195/M-5_walmartsv_tYVHFOhxmH_124681_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Tio Paco Rojo - 1814 g",
        "descripcion": "Frijol Tío Paco Rojo - 1814 g el alimento esencial y tradicional que no puede faltar en tu mesa para complementar tus comidas. Destaca por su cuidadoso proceso de selección, garantizando un grano limpio, rendidor y de consistencia ideal tras su cocción. Una alternativa sumamente nutritiva y versátil que se adapta a la perfección como base de tus recetas favoritas, aportando el rendimiento y la calidad que tu familia merece.",
        "codigo_barras": "7410010428092",
        "precio_base": "5.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/576600/43701_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol Rojo De Seda Omoa 2pack 3632 g",
        "descripcion": "Complementa tu mesa con Frijol Rojo De Seda Omoa 2 unidades 3632 g, ideal para quienes buscan sabor y practicidad en un mismo empaque. Cuenta con varias ventajas: su presentación facilita medir la porción justa para cada ocasión; es una opción versátil para acompañar comidas o reuniones; su empaque práctico permite conservarlo en buen estado hasta el momento de utilizarlo; se integra sin complicaciones a tu lista de compras semanal. Combina bien con otros ingredientes de tu cocina para p...",
        "codigo_barras": "6009230010104",
        "precio_base": "12.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/883199/M-5_walmartsv_LPltjegNKh_121628_01.jpg"
    },
    {
        "categoria": "Abarrotes y Despensa",
        "nombre": "Frijol rojo La Chula molido -907 g",
        "descripcion": "La Chula Frijol Rojo Molido 907 g el producto indispensable en tu despensa diseñado para convertirse en la base o el sazón perfecto de tus comidas. Destaca por su gran rendimiento, calidad y versatilidad culinaria, siendo una alternativa ideal para enriquecer, preparar o complementar una amplia variedad de platillos y recetas. Un componente esencial que garantiza consistencia y un excelente sabor en tu mesa.",
        "codigo_barras": "7410030504011",
        "precio_base": "1.29",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/725345/106112_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Tropical  Fresa -2.5 L",
        "descripcion": "Gaseosa Tropical Fresa -2.5 L la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7411001870210",
        "precio_base": "1.96",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/653510/101548_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa 7Up Pet 600 ml",
        "descripcion": "Agua Mineral Shangri-La by Dasani, presentado en cómodas latas de 2124 ml, perfectas para mantenerte hidratado en cualquier momento del día. Esta agua mineral natural proviene de fuentes cuidadosamente seleccionadas, ofreciendo un sabor limpio y refrescante que revitaliza tu cuerpo y mente. Ideal para acompañar tus comidas, actividades deportivas o simplemente para mantener un estilo de vida saludable, cada lata conserva todas las propiedades minerales esenciales que tu organismo necesit...",
        "codigo_barras": "7401005941030",
        "precio_base": "0.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/577426/45832_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Mirinda Naranja 1500 ml",
        "descripcion": "La gaseosa Mirinda Naranja en presentación de 1500 ml es una bebida refrescante que captura el sabor vibrante y dulce de la naranja con una efervescencia perfecta. Su fórmula carbonatada ofrece una textura burbujeante que realza cada sorbo, proporcionando una sensación refrescante ideal para cualquier momento del día. Este envase grande es perfecto para compartir en reuniones familiares, eventos o simplemente para tener siempre a mano una bebida que satisface los antojos de frescura y sa...",
        "codigo_barras": "7401005912115",
        "precio_base": "1.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/457184/Gaseosa-Mirinda-Naranja-1500Ml-1-5758.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Bebida Gaseosa Big Cola 250ml",
        "descripcion": "Bebida gaseosa Big Cola 250ml la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7445072001440",
        "precio_base": "0.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/886509/M-5_walmartsv_SQNhxSfKll_119015_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Bebida Gaseosa Big Limon 250ml",
        "descripcion": "Bebida Big Limón de 250 ml ofrece una experiencia refrescante y vibrante, capturando el sabor cítrico y natural del limón en cada sorbo. Su equilibrio entre acidez y dulzura proporciona una sensación ligera y agradable, ideal para acompañar comidas, meriendas o momentos de descanso. La presentación de 250 ml resulta práctica y fácil de transportar, permitiendo disfrutar de la bebida en cualquier lugar, ya sea en el hogar, la oficina o actividades al aire libre. Elaborada bajo estrictos e...",
        "codigo_barras": "7445072006803",
        "precio_base": "0.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/899303/M-5_walmartsv_NPUQrFTrns_50116_5.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa 7Up - 1.5 L",
        "descripcion": "La Gaseosa 7Up en presentación de 1500 ml es una opción refrescante y deliciosa para disfrutar en cualquier momento del día. Su sabor cítrico y burbujeante combina frescura y dulzura en cada sorbo, ofreciendo una experiencia revitalizante perfecta para acompañar comidas, reuniones familiares, celebraciones o simplemente para calmar la sed. La botella de 1500 ml asegura cantidad suficiente para compartir y disfrutar con amigos o en familia. 7Up destaca por su sabor único y su capacidad de...",
        "codigo_barras": "7401005912030",
        "precio_base": "1.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/578112/45827_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Kolashanpan Mini 12Pk 2304 ml",
        "descripcion": "Gaseosa Kolashanpan Mini 12 Pack de 2304 ml ofrece una experiencia refrescante y práctica, ideal para compartir en familia, reuniones o cualquier momento del día. Cada botella contiene la cantidad perfecta para disfrutar del sabor característico de Kolashanpan, con burbujas suaves y un aroma único que hacen de cada sorbo una experiencia agradable y vivaz. Su presentación en pack de 12 unidades asegura practicidad y disponibilidad para varias ocasiones, manteniendo la frescura y consisten...",
        "codigo_barras": "0731809002987",
        "precio_base": "2.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/405967/Gaseosa-Kolashanpan-Mini-12Pk-2304Ml-1-23930.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Fanta regular - 1.25 L",
        "descripcion": "Gaseosa Fanta sabor naranja en botella PET. Ideal para refrescarte en cualquier momento del día. Su sabor cítrico y burbujeante es perfecto para disfrutar con amigos y familia. Presentación de 1.25 L.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7411001803546",
        "precio_base": "1.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/577542/43809_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Tropical regular - 1.25 L",
        "descripcion": "Gaseosa Tropical Regular de 1.25 L ofrece una experiencia refrescante y agradable en cada sorbo, combinando burbujas suaves con un sabor característico y equilibrado. Su presentación de 1.25 L es ideal para compartir en familia, acompañar comidas o disfrutar en cualquier momento del día, asegurando varias porciones de bebida fresca y lista para servir. Elaborada con ingredientes seleccionados, Tropical Regular mantiene un aroma y sabor consistentes, brindando la sensación refrescante que...",
        "codigo_barras": "7411001803508",
        "precio_base": "1.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/807746/gaseosa-tropical-regular-1-25-l-7411001803508.webp"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Kolashanpan Lata - 355 ml",
        "descripcion": "La Gaseosa Kolashanpan Lata de 355 ml ofrece un sabor clásico, burbujeante y dulce que brinda frescura y placer en cada sorbo. Su equilibrio característico permite disfrutarla sola, acompañando comidas o compartiendo en reuniones, ofreciendo una experiencia refrescante y agradable al paladar. Esta bebida destaca por mantener su autenticidad y calidad constante, convirtiéndose en una opción versátil que satisface el gusto de toda la familia y proporciona momentos de frescura, diversión y ...",
        "codigo_barras": "0731809001997",
        "precio_base": "0.36",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/384373/Gaseosa-Kolashanpan-Lata-355Ml-1-2855.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Pepsi 12 Pack 355 ml",
        "descripcion": "La Gaseosa Pepsi 12 Pack de 355 ml ofrece el sabor clásico y refrescante de Pepsi en cada sorbo, combinando dulzura y burbujas que brindan una experiencia agradable al paladar. Su sabor equilibrado la hace ideal para acompañar comidas, compartir en reuniones o disfrutar sola en cualquier momento del día. Esta bebida destaca por su frescura constante y autenticidad, siendo perfecta para quienes buscan una opción versátil que mantenga la intensidad y calidad característica de Pepsi, propor...",
        "codigo_barras": "7411602706161",
        "precio_base": "5.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/592212/59994_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Mountain Dew - 600 ml",
        "descripcion": "Gaseosa Mountain Dew, una bebida refrescante y energizante con un sabor único. Ideal para cualquier ocasión y perfecta para hidratarse con un toque diferente. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7421601105803",
        "precio_base": "0.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/385794/Mountain-Dew-Gaseosa-1-12810.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Sprite regular - 2.5 L",
        "descripcion": "Gaseosa SpRite regular - 2.5 L la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7411001831266",
        "precio_base": "1.96",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/591888/43827_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Fresca regular - 2.5 L",
        "descripcion": "La gaseosa de toronja Fresca es una refrescante bebida carbonatada ideal para saciar la sed. Con un sabor cítrico y una burbujeante textura, esta gaseosa es perfecta para cualquier ocasión. Presentación de 2.5 litros, ideal para compartir con familiares y amigos.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7411001800941",
        "precio_base": "1.96",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/578701/43778_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Pepsi Pet - 3.3 L",
        "descripcion": "El refresco de cola Pepsi Jumbazo es una bebida carbonatada de 3.3 litros. Ideal para compartir en reuniones y fiestas, ofrece el clásico sabor de Pepsi en un formato grande y conveniente. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401005980824",
        "precio_base": "2.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/741874/45835_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Salutaris Torojan - 1.5 L",
        "descripcion": "Gaseosa Salutaris Torojan de 1.5 L es la bebida refrescante ideal para disfrutar en cualquier momento del día. Su sabor único y burbujeante ofrece una experiencia deliciosa y revitalizante que encanta a grandes y chicos. Su presentación garantiza que siempre tengas suficiente bebida para compartir en reuniones, comidas o momentos especiales en familia combinando frescura, sabor y practicidad, convirtiéndose en la opción perfecta para quienes buscan un refresco confiable, delicioso y list...",
        "codigo_barras": "7411602705331",
        "precio_base": "1.01",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/578159/50521_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Salutaris Pet - 600 ml",
        "descripcion": "Gaseosa Salutaris en presentación PET de 600ml. Ideal para refrescarse en cualquier momento del día. Su envase práctico permite llevarla a cualquier lugar, ofreciendo una bebida con el sabor y calidad que caracteriza a Salutaris. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401005941054",
        "precio_base": "0.68",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/857510/gaseosa-salutaris-pet-600-ml-7401005941054.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Pepsi Envase Pet 600 ml",
        "descripcion": "Una refrescante gaseosa Pepsi en un práctico envase PET de 600 ml. Ideal para calmar la sed con su inconfundible sabor a cola. Perfecta para llevar y disfrutar en cualquier momento del día. Refrigera antes de servir para una experiencia óptima. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401005941016",
        "precio_base": "0.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/577421/45831_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Bebida Gaseosa Ramune Original 200 Ml",
        "descripcion": "La bebida gaseosa Ramune Original de Inotea en presentación de 200 ml es una refrescante opción que destaca por su sabor único y burbujeante. Originaria de Japón, esta bebida se caracteriza por su envase tradicional con cierre tipo canica, que aporta un toque especial y divertido al momento de disfrutarla. Su fórmula original ofrece un sabor dulce y equilibrado, ideal para refrescarse en cualquier ocasión. Perfecta para acompañar comidas o simplemente para disfrutar como un snack refresc...",
        "codigo_barras": "0111522167994",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/762192/105151_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Bebida Gaseosa Ramune Melon 200 Ml",
        "descripcion": "La bebida gaseosa Ramune sabor melón de Inotea, en presentación de 200 ml, ofrece una refrescante experiencia con un delicado sabor a melón dulce y afrutado. Originaria de Japón, esta bebida destaca por su envase único con cierre de canica, que añade un toque divertido y distintivo al momento de abrirla. Su efervescencia suave y equilibrada convierte a Ramune en una opción ideal para refrescarse durante el día, aportando un sabor ligero y delicioso. Perfecta para acompañar snacks o simpl...",
        "codigo_barras": "0111522256162",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/762213/105152_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Bebida Gaseosa Ramune Fresa 200 Ml",
        "descripcion": "La bebida gaseosa Ramune sabor fresa de Inotea, en presentación de 200 ml, ofrece una experiencia refrescante y divertida con un toque frutal dulce y vibrante. Proveniente de Japón, esta bebida se distingue por su característico envase con cierre tipo canica, que brinda un método único y entretenido para abrirla. Su sabor a fresa combina perfectamente la dulzura natural con una efervescencia suave, ideal para refrescarse en cualquier momento del día. Perfecta para acompañar snacks o simp...",
        "codigo_barras": "0111522168052",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/762076/105150_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Mountain Dew Lata 355 ml",
        "descripcion": "La Gaseosa Mountain Dew en lata de 355 ml es una bebida carbonatada y refrescante, reconocida por su sabor cítrico y burbujeante que ofrece una experiencia única en cada sorbo. Ideal para disfrutar sola o acompañando tus comidas favoritas, proporciona un impulso de frescura y energía. Su presentación en lata de 355 ml es práctica, perfecta para llevar a la oficina, la escuela o disfrutar en reuniones y eventos. Mountain Dew combina sabor intenso, burbujeante y refrescante, convirtiéndose...",
        "codigo_barras": "7401005905780",
        "precio_base": "0.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/183512/Gaseosa-Mountain-Dew-Lata-355Ml-1-5746.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Bebida Gaseosa Ramune Lychee 200 Ml",
        "descripcion": "La bebida gaseosa Ramune sabor lychee de Inotea, en presentación de 200 ml, ofrece una experiencia refrescante y exótica que destaca por su delicado y dulce sabor a lychee, una fruta tropical muy apreciada. Proveniente de Japón, esta bebida se distingue por su característico envase con cierre tipo canica, que aporta un toque único y divertido al abrirla. Su burbujeante efervescencia combina perfectamente con el sabor frutal, brindando una sensación ligera y refrescante ideal para cualqui...",
        "codigo_barras": "0111522256544",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/762080/105154_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Pepsi Cola - 1500 ml",
        "descripcion": "Bebida Carbonatada Pepsi de 1500 ml, opciones ideales para quienes buscan refrescarse en cualquier momento del día. La 7Up ofrece un característico sabor cítrico y burbujeante que combina perfectamente con comidas, reuniones o simplemente para saciar la sed con ligereza y frescura. Por su parte, Pepsi brinda un sabor único y equilibrado, con su tradicional efervescencia que ha conquistado a generaciones, haciendo de cada sorbo una experiencia refrescante y revitalizante. Ambas presentaci...",
        "codigo_barras": "7401005912016",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/857505/gaseosa-pepsi-cola-1500-ml-7401005912016.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Mirinda Naranja - 3 L",
        "descripcion": "Disfruta de la gaseosa Mirinda con un refrescante sabor a naranja. Ideal para compartir en reuniones o disfrutar en familia. Viene en una presentación de 3000 ml para saciar tu sed por más tiempo. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401005915116",
        "precio_base": "2.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/578141/45830_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Gaseosa Coca Cola regular - 3 L",
        "descripcion": "Gaseosa de cola, Coca Cola. Su sabor inconfundible y burbujeante la convierte en la elección favorita para cualquier ocasión. Presentación en botella PET de 3000 ml, ideal para compartir.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7411001888932",
        "precio_base": "2.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/591882/43832_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Alvia Jugo Mango 490ml",
        "descripcion": "Alvia Jugo Mango 490ml la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7410010838174",
        "precio_base": "1.39",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/954403/M-5_walmartsv_UZflJtfMhC_100623_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Leyde Jugo De Jamaica 500ml",
        "descripcion": "Jugo Leyde De Jamaica 500 Ml la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas diarias, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7422540030539",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/853155/leyde-jugo-de-jamaica-500-ml-7422540030539.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Alvia Jugo Sandia 490 Ml",
        "descripcion": "Alvia Jugo Sandia 490 Ml",
        "codigo_barras": "7410010838228",
        "precio_base": "1.39",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/895296/M-5_walmartsv_IzAhQDmIjg_115423_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Quanty Jugo De Naranja 500 ml",
        "descripcion": "Quanty Jugo De Naranja 500 ml la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "0611594000125",
        "precio_base": "0.38",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/938879/M-5_walmartsv_PSmzHMBkci_63089_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Naturalisimo Mandarina - 1795ml",
        "descripcion": "Jugo Marca Naturalisimo: Descubre la naturaleza en cada gota con el sabor puro y refrescante de la mandarina. 100% natural, una experiencia cítrica y auténtica en cada sorbo.",
        "codigo_barras": "7404003700838",
        "precio_base": "4.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/900797/M-5_walmartsv_uaDEucwyCr_52548_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Premium Pinaguayaba 1895 ml",
        "descripcion": "Jugo Premium Piñaguayaba 1895 ml la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7412900300655",
        "precio_base": "3.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/194862/Jugo-Premium-Pinaguayaba-1895Ml-1-14837.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Del Valle Mandarina 250ml Pet",
        "descripcion": "Jugo Del Valle Mandarina 250ml Pet",
        "codigo_barras": "7411001806363",
        "precio_base": "0.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/891441/M-5_walmartsv_OKuAHkKkQu_121859_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Jumex de piña - 960 ml",
        "descripcion": "Bebida de jugo y pulpa de piña, elaborada para conservar aroma y sabor natural. Rica en frescura y textura, ofrece una experiencia tropical y nutritiva. Presentada en envase práctico de 960 ml, resulta ideal para acompañar comidas, compartir o disfrutar como bebida refrescante en cualquier momento. Una opción versátil y deliciosa para quienes buscan sabor auténtico y natural. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te r...",
        "codigo_barras": "7501013109689",
        "precio_base": "1.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/806529/nectar-jumex-pina-960-ml-7501013109689.webp"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Frutado Sabor Pera 600 ml",
        "descripcion": "El Jugo Frutado Sabor Pera de 600 ml ofrece la frescura y dulzura natural de la pera, brindando una experiencia ligera y agradable al paladar en cada sorbo. Su sabor equilibrado permite disfrutarlo solo, acompañado de comidas o en reuniones, siendo ideal para cualquier momento del día. Este jugo destaca por su autenticidad y frescura, proporcionando una bebida versátil y deliciosa que mantiene el sabor natural de la pera, ofreciendo satisfacción, vitalidad y placer en cada degustación, c...",
        "codigo_barras": "0024474007402",
        "precio_base": "0.48",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/405766/Jugo-Frutado-Sabor-Pera-600ml-1-19251.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo De Naranja Clasico Carton 473 ml",
        "descripcion": "Jugo de naranja Sula en presentación de 473 ml. Elaborado con naranjas frescas para ofrecer un sabor cítrico y natural. Ideal para disfrutar a cualquier hora del día y complementar tus comidas con una bebida saludable y refrescante. Envasado en cartón para mantener su frescura y calidad.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actu...",
        "codigo_barras": "7421000823131",
        "precio_base": "0.59",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/759973/50741_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Del Valle Mandarina 2.5 l",
        "descripcion": "Jugo Del Valle Mandarina 2.5 l la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7411001806394",
        "precio_base": "1.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/858270/jugo-del-valle-mandarina-2-5-l-7411001806394.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Sula De Naranja Zanahoria 946 ml",
        "descripcion": "El jugo Sula de Naranja y Zanahoria en presentación de 946 ml es una bebida deliciosa y saludable que combina el sabor refrescante de la naranja con los beneficios nutritivos de la zanahoria. Rico en vitaminas, antioxidantes y minerales esenciales, contribuye al fortalecimiento del sistema inmunológico, la energía diaria y el bienestar general. Su textura suave y su sabor natural lo hacen perfecto para disfrutar en desayunos, meriendas o como acompañante de comidas. La botella de 946 ml ...",
        "codigo_barras": "7421000842743",
        "precio_base": "2.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/342669/Jugo-Sula-De-Naranja-Zanahoria-946Ml-1-24097.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Welchs 24Pack Surtido 7080 ml",
        "descripcion": "Jugo Welchs 24Pack Surtido 7080 Ml",
        "codigo_barras": "0041800479108",
        "precio_base": "20.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/240999/Jugo-Welchs-24Pack-Surtido-7080-Ml-1-20339.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo De Uva Welch's En Botella  -1892ml",
        "descripcion": "El jugo de uva en botella Welchs es un refresco hecho 100% de Uva. Tiene 2 veces el poder antioxidante que el jugo de naranja. Welch's es hecho con cascaras, semillas. No contiene azúcar agregada, colorantes ni saborizantes. Tiene un sabor delicioso y natural, está lleno de vitaminas y minerales. Es perfecto para tomar en cualquier momento, siendo una excelente opción para mantenerte hidratado",
        "codigo_barras": "0041800207503",
        "precio_base": "7.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/736200/49300_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Sula De Naranja Zanahoria 473 ml",
        "descripcion": "Bebida a base de jugo de naranja y zanahoria, Sula. Ideal para acompañar tus comidas, refrescante y saludable. Sin pulpa. Presentación de 473ml.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7421000841357",
        "precio_base": "0.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/579378/52807_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Del Valle Mandarina 1500ml Pet",
        "descripcion": "Jugo Del Valle Mandarina 1500ml Pet",
        "codigo_barras": "7411001806387",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/891163/M-5_walmartsv_oJTDXLXyqF_121861_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo De Naranja Dr Juice 350 ml",
        "descripcion": "Jugo de Naranja Dr Juice de 350 ml ofrece una experiencia refrescante y natural, capturando el auténtico sabor de la naranja en cada sorbo. Su equilibrio entre dulzura y acidez proporciona una bebida ligera y agradable, ideal para acompañar desayunos, meriendas o cualquier momento del día en que se desee disfrutar de frescura y sabor natural. Cada envase mantiene la calidad y frescura del jugo, asegurando que su aroma y sabor característicos se conserven en cada porción. Su presentación ...",
        "codigo_barras": "7410030701496",
        "precio_base": "2.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/342599/Jugo-De-Naranja-Dr-Juice-350Ml-1-8125.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Alvia guanábana - 490 ml",
        "descripcion": "El jugo Alvia Guanábana de El Porvenir en su presentación de 490 ml es una opción pensada para acompañar distintos momentos de consumo con una referencia de sabor guanábana. Puede servirse durante desayunos, almuerzos, meriendas o reuniones, según la preferencia personal y la ocasión. Su cantidad resulta práctica para disponer de una bebida lista para integrar a comidas o pausas durante el día. Es una alternativa conveniente para quienes disfrutan variar sus bebidas habituales y desean c...",
        "codigo_barras": "7410010838235",
        "precio_base": "1.39",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/733121/100624_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche de soya Incaparina Con Leche 6 Pack - 1200 ml",
        "descripcion": "Leche de soya Incaparina con leche 6 pack en presentación de 1200 ml combina ingredientes vegetales con leche, ofreciendo una alternativa diferente dentro de las bebidas diarias. Su formato en unidades individuales permite un consumo práctico en cualquier momento del día. Puede consumirse directamente o integrarse en preparaciones. Es ideal para quienes buscan variedad en su alimentación. Su presentación facilita el transporte y almacenamiento. Compra en línea y disfruta esta opción en t...",
        "codigo_barras": "0081537307022",
        "precio_base": "2.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/774445/51682_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Kikitos Caf Con Leche 54gr",
        "descripcion": "Kikitos Caf Con Leche 54gr",
        "codigo_barras": "7413402802470",
        "precio_base": "0.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/954239/M-5_walmartsv_bhUDuyKLXi_126795_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Tribe Kefir Leche Natural 473ml",
        "descripcion": "Suma Tribe Kefir Leche Natural 473 ml a tu carrito y ten una opción lista para cualquier antojo. Cuenta con varias ventajas: es fácil de incorporar en recetas, loncheras o meriendas rápidas; su sabor y textura lo hacen apto tanto para grandes como para chicos; resulta cómodo de transportar, ya sea para la casa, el trabajo o un paseo; es una opción versátil para acompañar comidas, postres o reuniones; su formato facilita compartirlo en familia o guardarlo para más adelante; su empaque prá...",
        "codigo_barras": "7410010885420",
        "precio_base": "3.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/929306/tribe-kefir-leche-natural-473-ml-7410010885420.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Barra de chocolate tutto de leche - 80 g",
        "descripcion": "La barra de chocolate con leche Tutto de 80 g es una deliciosa opción que combina la cremosidad de la leche con el sabor intenso del cacao. Ideal para disfrutar como snack o postre, esta barra satisface tus antojos de chocolate de una manera irresistible. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7702007072402",
        "precio_base": "2.05",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/558234/62998_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Tribe Kefir Leche De Coco 473ml",
        "descripcion": "Disfruta Tribe Kefir Leche De Coco 473 ml, una opción práctica que se convierte en tu aliada de todos los días. Cuenta con varias ventajas: su empaque práctico permite conservarlo en buen estado hasta el momento de servirlo; su presentación facilita medir la porción justa para cada ocasión; su formato facilita compartirlo en familia o guardarlo para más adelante; es fácil de incorporar en recetas, loncheras o meriendas rápidas; se integra sin complicaciones a tu lista de compras semanal;...",
        "codigo_barras": "7410010885376",
        "precio_base": "3.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/929299/tribe-kefir-leche-de-coco-473-ml-7410010885376.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Semidescremada Dos Pinos -1 L",
        "descripcion": "Leche Semidescremada Dos Pinos es una opción diseñada para el consumo diario que combina practicidad, versatilidad y un formato pensado para adaptarse a distintas rutinas dentro del hogar. Su presentación permite integrarla fácilmente en bebidas como café, cereales o batidos, así como en preparaciones culinarias tanto dulces como saladas según el tipo de producto. En sus versiones líquidas, facilita el consumo directo sin preparación adicional, mientras que en formatos múltiples o promoc...",
        "codigo_barras": "7441001601064",
        "precio_base": "1.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/579437/52914_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Economilk Leche Cond 397 g",
        "descripcion": "Economilk leche condensada en su presentación de 397 g, es una opción práctica para endulzar y dar textura cremosa a postres, bebidas y recetas caseras. Puede utilizarse en flanes, tres leches, arroz con leche, helados, cafés, batidos, gelatinas, rellenos, salsas dulces o preparaciones de repostería. Su formato permite dosificar la cantidad necesaria según la receta y mantenerla disponible en la despensa para distintos usos. Es una alternativa conveniente para quienes buscan un ingredien...",
        "codigo_barras": "0785381028804",
        "precio_base": "2.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/905308/M-5_walmartsv_KcTswHNTYr_124770_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Tribe Kefir Leche Arandanos 473ml",
        "descripcion": "Prueba Tribe Kefir Leche Arándanos 473 ml y encuentra un nuevo favorito para tu mesa de cada día. Cuenta con varias ventajas: es fácil de incorporar en recetas, loncheras o meriendas rápidas; resulta cómodo de transportar, ya sea para la casa, el trabajo o un paseo; su empaque práctico permite conservarlo en buen estado hasta el momento de servirlo; su presentación facilita medir la porción justa para cada ocasión; se integra sin complicaciones a tu lista de compras semanal; su sabor y t...",
        "codigo_barras": "7410010885437",
        "precio_base": "3.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/929300/tribe-kefir-leche-arandanos-473-ml-7410010885437.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Paleta Alaska Leche Condensada 75g",
        "descripcion": "La paleta Alaska sabor leche condensada de 75 g es una opción refrescante para disfrutar un postre helado con un perfil dulce, cremoso y agradable en distintos momentos del día. Su sabor inspirado en la leche condensada aporta una experiencia suave y reconfortante, ideal para quienes prefieren opciones clásicas con una textura que resulta fácil de disfrutar en días cálidos o como un antojo especial. Su presentación individual facilita el consumo sin preparación adicional, por lo que pued...",
        "codigo_barras": "7441001621727",
        "precio_base": "0.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/841259/paleta-alaska-leche-condensada-75-g-7441001621727.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Dos Pinos Pinito - 1000 ml",
        "descripcion": "Leche Dos Pinos Pinito en presentación de 1000 ml es una opción versátil para el consumo diario que se integra fácilmente en bebidas, café, cereales o recetas. Su formato de 1 litro permite servir varias porciones en el hogar, facilitando el uso continuo en diferentes momentos del día. Puede consumirse fría o caliente, adaptándose a preferencias y preparaciones. Su envase práctico permite almacenamiento en refrigeración y manejo sencillo. Es ideal para quienes buscan una leche funcional ...",
        "codigo_barras": "7441001601118",
        "precio_base": "2.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/782465/52917_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Salud Uht - 1000 ml",
        "descripcion": "Leche Salud UHT en presentación de 1000 ml es una opción práctica para el consumo cotidiano con facilidad de almacenamiento. Puede utilizarse en bebidas, café o recetas, adaptándose a distintos usos. Compra en línea y mantén esta leche disponible.",
        "codigo_barras": "7412900306473",
        "precio_base": "1.55",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/580249/54935_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Condensada La Lechera Original -335g",
        "descripcion": "Leche condensada La Lechera original en presentación de 335 g es una alternativa práctica para quienes buscan un tamaño intermedio en sus preparaciones. Su textura espesa facilita su uso en recetas como pasteles, flanes o bebidas, adaptándose a diferentes usos. Su formato permite un manejo sencillo en la cocina y almacenamiento conveniente. Compra en línea y mantén este ingrediente disponible.",
        "codigo_barras": "7501059278868",
        "precio_base": "2.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/766232/41948_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Condensada Pronto - 380 g",
        "descripcion": "Leche condensada Pronto en presentación de 380 g es una alternativa versátil para la preparación de recetas dulces en el hogar. Su textura permite utilizarla como relleno, cobertura o base en diferentes preparaciones, adaptándose a múltiples usos. Es ideal para quienes buscan practicidad en la cocina diaria. Compra en línea y agrégala a tu despensa.",
        "codigo_barras": "7501200486005",
        "precio_base": "1.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/733092/100384_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Salud Carton - 473 ml",
        "descripcion": "Leche Salud Cartón es una bebida diseñada para el consumo diario que destaca por su practicidad y perfil de sabor diferenciado según su presentación, ideal para integrarse fácilmente en distintas rutinas dentro del hogar. Su formato permite consumirla directamente sin preparación adicional, lo que la convierte en una alternativa conveniente para meriendas, desayunos o pausas rápidas durante el día. Dependiendo de su versión, ofrece opciones como descremada, deslactosada o combinaciones c...",
        "codigo_barras": "7412900301058",
        "precio_base": "0.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/962641/M-5_walmartsv_AZCKtkaWxB_54896_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Entera Salud - 1.8 L",
        "descripcion": "Leche entera Salud en presentación de 1.8 litros es una opción versátil pensada para quienes buscan un equilibrio entre volumen y practicidad en el hogar. Su tamaño permite servir varias porciones durante el día, siendo ideal para bebidas, café, cereales o recetas. Puede consumirse directamente o utilizarse en preparaciones culinarias, adaptándose a distintos momentos del día. Su envase facilita el almacenamiento en refrigeración y su uso continuo. Es una alternativa funcional para quien...",
        "codigo_barras": "7412900301089",
        "precio_base": "3.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/580196/54897_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Evaporada Australian - 410 g",
        "descripcion": "Leche evaporada Australian en presentación de 410 g es un ingrediente versátil para la cocina, ideal para preparaciones dulces o saladas. Su textura concentrada permite aportar consistencia y sabor a recetas como sopas, salsas o postres. Es una opción práctica para quienes buscan un ingrediente funcional en la cocina. Su formato facilita el almacenamiento antes de abrir. Compra en línea y agrégala a tu despensa.",
        "codigo_barras": "7402000016938",
        "precio_base": "1.73",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/754038/52528_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Condensada Australian - 397 g",
        "descripcion": "Leche condensada Australian en presentación de 397 g es un ingrediente clásico para la preparación de postres y bebidas dulces. Su textura espesa y cremosa facilita su uso como relleno, cobertura o complemento en recetas como flanes, pasteles o café. Es ideal para quienes buscan un producto versátil en la cocina. Su formato permite almacenarlo fácilmente antes de abrir. Compra en línea y añade este ingrediente a tus preparaciones.",
        "codigo_barras": "8992702000827",
        "precio_base": "2.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/755202/46896_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Pastel 1/4 Relleno Dulce De Leche",
        "descripcion": "El pastel 1/4 relleno de dulce de leche, es una opción dulce y práctica para compartir en celebraciones pequeñas, reuniones familiares o como postre especial después de las comidas. Su relleno aporta una textura cremosa y un sabor agradable que combina con bebidas calientes o frías. Puede servirse en porciones y acompañarse con café, leche, chocolate caliente, té o bebidas de preferencia. Su formato de 1/4 resulta conveniente para ocasiones donde se requiere una cantidad moderada, fácil ...",
        "codigo_barras": "2504270000008",
        "precio_base": "14.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/921494/pastel-1-4-relleno-dulce-de-leche-2504270000008.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche DescremadaSalud - 1892 ml",
        "descripcion": "Leche Descremada Salud es una bebida diseñada para el consumo diario que destaca por su practicidad y perfil de sabor diferenciado según su presentación, ideal para integrarse fácilmente en distintas rutinas dentro del hogar. Su formato permite consumirla directamente sin preparación adicional, lo que la convierte en una alternativa conveniente para meriendas, desayunos o pausas rápidas durante el día. Dependiendo de su versión, ofrece opciones como descremada, deslactosada o combinacion...",
        "codigo_barras": "7412900307777",
        "precio_base": "3.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408966/Leche-Salud-Descremada-1892Ml-1-14897.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Entera Australian - 2200 g",
        "descripcion": "Leche entera Australian en presentación de 2200 g es una opción de alto rendimiento para quienes buscan abastecer el hogar con una leche en polvo práctica y versátil. Su formato amplio permite preparar numerosas porciones según la necesidad, lo que facilita su uso en desayunos, bebidas calientes, cereales o distintas recetas de cocina. Este tamaño resulta ideal para familias o para quienes tienen un consumo frecuente y prefieren contar con una base láctea disponible por más tiempo. Su pr...",
        "codigo_barras": "7410031970013",
        "precio_base": "26.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/670346/63229_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Bolsas Evenflo Para Almacenar Leche Materna",
        "descripcion": "Bolsas Para Almacenar Leche Materna Evenflo destaca por su calidad y funcionalidad, siendo una opción confiable en cada uso. Pensado para facilitar la vida del consumidor, ofrece practicidad sin sacrificar la calidad. Una compra inteligente que garantiza satisfacción en cada uso.",
        "codigo_barras": "7501027579683",
        "precio_base": "15.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/370926/Bolsas-Evenflo-Para-Almacenar-Leche-Materna-1-36273.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche Semidescremada Salud - 1892 ml",
        "descripcion": "Leche semidescremada Salud en presentación de 1892 ml es una opción diseñada para quienes buscan un equilibrio en contenido de grasa dentro de su consumo diario. Su tamaño permite servir múltiples porciones, facilitando su uso en bebidas, café, cereales o recetas. Puede consumirse fría o caliente según preferencia. Su envase permite almacenamiento práctico en refrigeración. Es ideal para consumo familiar moderado. Compra en línea y mantén esta leche disponible para tu rutina diaria.",
        "codigo_barras": "7412900300334",
        "precio_base": "3.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/430046/Leche-Salud-Semidescremada-1892Ml-1-14834.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Tribe Kefir Leche Coco Arandanos 473ml",
        "descripcion": "Tribe Kefir Leche Coco Arandanos 473ml",
        "codigo_barras": "7410010885406",
        "precio_base": "3.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/945266/M-5_walmartsv_UIUbsDOyIa_125800_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Leche entera Sabemas - 1 L",
        "descripcion": "Leche entera Sabemas en presentación de 1 litro es una alternativa práctica para el consumo diario, ideal para bebidas, café o cereales. Su formato permite varias porciones y su envase facilita el almacenamiento en refrigeración. Compra en línea y agrégala a tu rutina.",
        "codigo_barras": "7441078217700",
        "precio_base": "1.55",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/883009/leche-entera-sabemas-1-l-7441078217700.webp"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Kraft Cuatro Queso Estilo Mex - 226 g",
        "descripcion": "Cheese Kraft Mexican Rallado 226g Este producto de la categoría de lácteos es una opción de excelente calidad, ideal para quienes buscan incorporar frescura, gran sabor y nutrientes esenciales en la alimentación diaria de toda la familia. Su cuidadoso proceso de selección y cadena de frío garantizan una textura ideal y una consistencia óptima, convirtiéndose en el ingrediente perfecto para enriquecer tus recetas.",
        "codigo_barras": "0840370901343",
        "precio_base": "4.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/877925/queso-kraft-mexican-rallado-226-g-0840370901343.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Lactolac Queso Mantequilla 400g",
        "descripcion": "Lactolac Queso Mantequilla 400 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "0787003005446",
        "precio_base": "4.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/853205/lactolac-queso-mantequilla-400-g-0787003005446.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Manchego 2pin 340g",
        "descripcion": "Saboreá el Queso Manchego Dos Pinos en presentación de 340 gramos. Madurado, semiduro, pasteurizado, sin gluten. Disfrutalo con pan, mermeladas, aceite de oliva o para marinar tus vinos. Agregalo al carrito.",
        "codigo_barras": "7441001627330",
        "precio_base": "7.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/653038/101002_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Muenster Kreef Lb",
        "descripcion": "Queso Muenster Kreef Lb desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "2555060000005",
        "precio_base": "11.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960274/M-5_walmartsv_NFfIhCAADj_79558_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Monteverde Cheddar 226g",
        "descripcion": "El queso Monteverde cheddar, en su presentación de 226 g, es una opción práctica para complementar diferentes tiempos de comida en casa. Puede utilizarse en sándwiches, hamburguesas, bocadillos, desayunos y diversas preparaciones donde se busca un ingrediente fácil de servir e incorporar. Su formato resulta conveniente para almacenar en refrigeración y utilizarlo gradualmente según la necesidad de cada ocasión. También puede formar parte de recetas calientes o frías, aportando variedad a...",
        "codigo_barras": "7441000505790",
        "precio_base": "5.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/964436/queso-monteverde-cheddar-226-g-7441000505790.webp"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Provolone Kreff Lb",
        "descripcion": "El queso provolone Kreef ofrece una textura firme y un sabor lácteo intenso que resulta ideal para disfrutar en tablas, sándwiches, gratinados y preparaciones calientes. Al fundirse adquiere una consistencia cremosa y elástica, por lo que combina muy bien con carnes, vegetales, panes y pastas. También puede servirse en rebanadas como aperitivo acompañado de aceitunas, frutos secos o embutidos. Su perfil ligeramente salado aporta carácter sin opacar otros ingredientes. Se recomienda mante...",
        "codigo_barras": "2555050000008",
        "precio_base": "13.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/427656/Queso-Provolone-Kreff-Lb-1-42976.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Morolique Lactolac 340 G",
        "descripcion": "Queso Morolique Lactolac 340 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "0787003005132",
        "precio_base": "5.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/953469/M-5_walmartsv_NLzzuyFKXq_101110_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Mozarella Kreef - Libra",
        "descripcion": "Queso Mozarella Kreef - Libra desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "2529330000002",
        "precio_base": "8.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/365957/Queso-Mozarella-Kreef-Libra-1-28166.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Monteverde Cheddar Block Lb",
        "descripcion": "Queso Monteverde Cheddar Block Lb desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "2565000000002",
        "precio_base": "9.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960037/M-5_walmartsv_kzPlWpSZEe_79559_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Montasio Zanetti 150 g",
        "descripcion": "Queso Montasio Zanetti 150 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "7401122302165",
        "precio_base": "6.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/604474/50328_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Torta De Queso - 1 Unidad",
        "descripcion": "La torta de queso, es una opción dulce y cremosa para disfrutar como postre individual, merienda o complemento después de las comidas. Su sabor a queso aporta un perfil suave y agradable, ideal para acompañar con café, leche, chocolate caliente, té o bebidas de preferencia. Su formato por unidad facilita adquirir solo la cantidad necesaria, servirla de forma práctica o llevarla para consumo inmediato. Puede compartirse en reuniones pequeñas, incluirse en mesas de postres o disfrutarse co...",
        "codigo_barras": "2539030000004",
        "precio_base": "3.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/921353/torta-de-queso-1-unidad-2539030000004.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Galleta Ritz Taco Queso 75g",
        "descripcion": "Galleta Ritz Queso Tubo 75g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque Práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "7622202309595",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/808778/galleta-ritz-taco-queso-75-gr-7622202309595.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Petacones Cottage 228 g",
        "descripcion": "Queso Cottage Petacones, fresco y cremoso. Ideal para ensaladas, postres o como acompañamiento. Empaque de 228 g, práctico y fácil de almacenar. Perfecto para quienes buscan una opción saludable y deliciosa.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7412900180424",
        "precio_base": "3.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/580197/54878_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Morolique Lactolac 170 G",
        "descripcion": "Queso Morolique Lactolac 170 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "0787003005248",
        "precio_base": "2.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960629/M-5_walmartsv_RbMTrRPlwP_101114_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "President Queso Feta Crumbled 170gr",
        "descripcion": "El queso feta Président crumbles de 170 g es una opción práctica para enriquecer distintas preparaciones con una textura desmenuzada y un sabor característico que resalta en cada plato. Resulta ideal para ensaladas, pastas, pizzas, tablas de quesos, vegetales y recetas frías o calientes que buscan un toque más especial al momento de servir. Su formato desmoronado facilita la porción y el uso directo en la cocina diaria, aportando comodidad y rapidez. Es una alternativa versátil para quie...",
        "codigo_barras": "0077901007810",
        "precio_base": "4.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/898347/M-5_walmartsv_dgfkrpBxOd_4146866_5.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Helado Sarita, Queso Fresa -1L",
        "descripcion": "Helado Sarita Litro Quesofresa 500gr el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "7401090801653",
        "precio_base": "3.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/700072/48157_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Izalqueno San Julian 340 g",
        "descripcion": "Queso Izalqueno San Julian 340 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "0708916032541",
        "precio_base": "5.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/604739/63109_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Izalqueno San Julian 200 g",
        "descripcion": "Queso Izalqueno San Julian 200 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "0708916030042",
        "precio_base": "3.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/951100/queso-izalqueno-san-julian-200-g-0708916030042.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Bandeja Mainstays para galletas",
        "descripcion": "La bandeja para galletas Mainstays es el complemento ideal para cualquier cocina, diseñada para ofrecer practicidad, durabilidad y resultados uniformes en cada horneado. Fabricada con materiales resistentes de alta calidad, esta bandeja distribuye el calor de manera uniforme, garantizando que tus galletas, pasteles y otros productos horneados queden perfectamente cocidos, con una textura dorada y deliciosa. Información del producto: La información de este producto es proporcionada por fa...",
        "codigo_barras": "6923610015742",
        "precio_base": "4.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/839662/utensilios-de-reposteria-mainstays-sidekick-mini-moldes-para-hornear-ms-6923610015742.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Rejilla Bakers Secrets para Galletas",
        "descripcion": "Rejilla Para Galletas Bakers Secrets lleva la eficiencia a tu hogar con este artículo de cocina, una opción de excelente diseñada especialmente para quienes buscan practicidad, durabilidad y el máximo rendimiento en la preparación de sus recetas diarias. Su estructura ergonómica e innovadora incorpora materiales que soportan el uso constante,un manejo cómodo, seguro y un mantenimiento sencillo que facilita su limpieza en pocos minutos.",
        "codigo_barras": "6935780111742",
        "precio_base": "3.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/866553/rejilla-para-galletas-bakers-secrets-6935780111742.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Chiky Vainilla - 400 g",
        "descripcion": "Descubre el delicioso sabor de las Galletas Chiky Vainilla, en un práctico paquete de 10 unidades y un peso total de 400 g.&nbsp; Estas galletas dulces, de la reconocida y favorita de todos: marca CHIKY, perfectas para satisfacer tus antojos con una exquisita combinación de galleta crujiente y un suave relleno de vainilla. Ideales para compartir en una merienda con amigos o disfrutar solo en cualquier momento del día. El empaque conveniente asegura que puedas llevarlas a donde quieras: a...",
        "codigo_barras": "7441163408167",
        "precio_base": "2.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/833167/galletas-chiky-vainilla-400-g-7441163408167.webp"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas María Pozuelo Original -252 g",
        "descripcion": "Galleta Maria de la marca Pozuelo en un práctico empaque con 12 unidades. Cada galleta ofrece un sabor dulce y textura crujiente perfecta para el disfrute en cualquier momento del día. Ideal para acompañar con bebidas calientes o como un snack rápido. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0086581006280",
        "precio_base": "2.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/326501/Galletas-Mar-a-marca-Pozuelo-Original-252g-1-13721.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Bandeja Bakers Secret para hornear galletas",
        "descripcion": "Bandeja Para Hornear Galletas Bakers Sec destaca por su calidad y funcionalidad, siendo una opción confiable en cada uso. Pensado para facilitar la vida del consumidor, ofrece practicidad sin sacrificar la calidad. Una compra inteligente que garantiza satisfacción en cada uso.",
        "codigo_barras": "6935780118369",
        "precio_base": "2.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/868293/bandeja-para-hornear-galletas-bakers-sec-6935780118369.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Caja De Galletas Peanuts Musical 113 g",
        "descripcion": "Caja De Galletas Peanuts Musical 113 g",
        "codigo_barras": "0654954258385",
        "precio_base": "6.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960550/M-5_walmartsv_MJHFLhiYBa_121996_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Cremas Estrella - 396 g",
        "descripcion": "Galletas cremadas mixtas de chocolate y vainilla con relleno de crema de vainilla. Una perfecta opción de merienda para disfrutar en la escuela o en casa. Presentación en bolsa de 396 gramos con 12 paquetes de 6 galletas cada uno",
        "codigo_barras": "7441163411839",
        "precio_base": "2.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/828219/galletas-pozuelo-cremas-estrella-396-g-7441163411839.webp"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Tosh Miel - 270 g",
        "descripcion": "Galletas integrales con miel, una opción de snack baja en grasa y en sodio, ofrecen un sabor delicioso y nutritivo en cada bocado. Perfectas para un snack saludable, ideales para toda la familia en presentación de 270 gramos con 9 paquetes de 30 gramos cada uno.",
        "codigo_barras": "0086581009403",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/789072/53779_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Tosh Avena Chocolate - 180 g",
        "descripcion": "Galletas Tosh Avena Chocolate - 180 g desarrollado bajo altos estándares para ofrecer una experiencia indulgente y llena de sabor en cada ocasión. Su versatilidad lo convierte en el aliado ideal para incorporar en tus desayunos, postres o reuniones sociales, garantizando esa sensación agradable que buscas en un producto de su categoría. Una elección inteligente que combina gran aceptación y la practicidad necesaria para tus días.",
        "codigo_barras": "7441163415011",
        "precio_base": "2.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/621259/75129_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Familia Navidad - 150 g",
        "descripcion": "Deliciosas y dulces galletas de vainilla hechas con increíbles moldes navideños con diferentes diseños. Perfectas para compartir en compañía de familia y amigos. Ideales para consumir con bebidas calientes. Bolsa con 150 gramos.&nbsp;",
        "codigo_barras": "7441163400741",
        "precio_base": "1.02",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/789681/36801_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Familia Navidad - 257 g",
        "descripcion": "Galletas Navideñas deliciosas para compartir que incluyen: Galleta de vainilla con cobertura de leche condensada, Galletas canasta con pasta de chocolate y relleno de chocolate blanco, Galleta de chocolate con relleno de naranja, Galleta de vainilla rellena de crema sabor dulce de leche y Dedos de señora. Presentación de 257 gramos.",
        "codigo_barras": "7441163401281",
        "precio_base": "3.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/789687/59086_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Sweet Well de almendra - 208 g",
        "descripcion": "Disfruta de las galletas Sweet Well de almendras, una opción deliciosa sin azúcar y sin gluten. Ideales para quienes buscan un snack saludable y con un sabor único. Cada paquete contiene 208 g de galletas crujientes y sabrosas, perfectas para cualquier momento del día. Vienen en un empaque que asegura su frescura y calidad. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fab...",
        "codigo_barras": "7443011627676",
        "precio_base": "7.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/787280/etas-Sweetwell-De-Almendras-Sin-Az-car-Sin-Gluten-26gr-1-32871_638502610565892583.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Nevadas Navidad  - 366 g",
        "descripcion": "Icónicas y deliciosas galletas con cobertura sabor a leche condensada. La opción perfecta para disfrutar en compañía de familiares y amigos en la temporada navideña. En presentación de 10 paquetes de 36,6 gramo cada uno.",
        "codigo_barras": "7441163408556",
        "precio_base": "3.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/789656/97390_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Chiky Chocolate - 480 g",
        "descripcion": "Chiky Chocolate, deliciosa, icónica e irresistible galleta de vainilla con cobertura sabor a chocolate. Presentación de 12 paquetes. 480 g. Ponete creativo y prepará deliciosas recetas con un máximo de sabor: paletas Chiky Cream, Choco Chiky Shakes, Chiky hielos con leche, Chiky barramellows, Chiky Donitas, Chiky chocobrownies, Chiky brigadelis, Chicky churriquísimos, Chikycupcakes, Chiky rolls, Chikyscake.",
        "codigo_barras": "0086581010881",
        "precio_base": "2.39",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/958159/galletas-pozuelo-chiky-chocolate-480-g-0086581010881.webp"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Cremas Vainilla - 252 g",
        "descripcion": "Deliciosa galleta Pozuelo Cremas Vainilla, galleta cremada de vainilla con relleno de crema de vainilla, una opción de merienda para diferentes momentos del día. Presentación de 8 paquetes individuales.",
        "codigo_barras": "7441163415189",
        "precio_base": "1.39",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/828209/galletas-pozuelo-cremas-vainilla-252-g-7441163415189.webp"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas María Suli Rollo - 135 g",
        "descripcion": "Las galletas Maria Sabemas son unas galletas elaboradas a base de harina, azúcar, huevos, mantequilla, leche, aroma de vainilla y sal. Son unas galletas de textura crujiente y sabor a vainilla. En su presentación de 135 gramos. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7441078256617",
        "precio_base": "0.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/729424/65295_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Cheez It Cheddar Jack - 351 g",
        "descripcion": "Si te encantan las botanas sabor a Cheddar Jack, definitivamente Cheez-it serán tus favoritas. Tienen textura crujiente, única e inigualable llena de sabor. Son un snack perfecto para disfrutar en cualquier momento. Botana crujiente de trigo con sabor a queso cheddar. • Hecho con queso 100% real • Delicioso snack para compartir ¡Llévate estas galletas saladas contigo y disfrútalas a cualquier hora!",
        "codigo_barras": "0024100788873",
        "precio_base": "5.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/741297/51459_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Gamesa Crackets Mini Sandwich - 38 g",
        "descripcion": "Las Galletas tipo sándwich Gamesa Mini Crackets contienen un relleno con intenso sabor a queso y una textura crujiente. Las galletas horneadas son ideales para botanear y acompañar tus comidas. Disfruta tu platillo favorito en compañía de unas deliciosas Mini Crackets®.",
        "codigo_barras": "7500478027118",
        "precio_base": "0.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/345172/Galleta-Mini-Sandwich-Crackets-Sabor-Queso-38g-1-36582.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Tosh María sin azúcar - 168 g",
        "descripcion": "Galletas Tosh María sin azúcar , 0% colesterol y 0 gramos de grasas trans sin colores ni sabores artificiales, bajas en sodio y su empaque es reciclable. Son 8 paquetes para compartir, ideales para una merienda, acompañar una bebida o disfrutarlas solitas.",
        "codigo_barras": "7441163415998",
        "precio_base": "1.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/621549/93156_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Diana picnic sabor fresa - 156 g",
        "descripcion": "Las galletas Diana picnic sabor fresa de 156 g son una opción práctica para disfrutar una merienda dulce con un toque frutal agradable en cualquier momento del día. Su sabor a fresa las hace ideales para loncheras, pausas en el trabajo, meriendas en casa o para acompañar bebidas calientes y frías. Son ideales para compartirlas o disfrutarlas como gusto solitario según la ocasión. Son una alternativa conveniente para quienes buscan galletas fáciles de llevar, con un sabor llamativo y una ...",
        "codigo_barras": "0748757007117",
        "precio_base": "1.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/471960/69944_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Tosh Fusión de Cereales - 256.5 g",
        "descripcion": "Galletas Pozuelo Tosh Fusión de Cereales , galleta tipo cracker multicereal con trigo linaza, arroz, maíz, avena, salvado de trigo y almendras, una opción de snack bajo en grasa y libre de azúcar, en presentación de 252. 5 gramos con 9 paquetes de 28 gramos cada uno.",
        "codigo_barras": "7441163400611",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/828178/galletas-pozuelo-tosh-fusion-de-cereales-256-5-g-7441163400611.webp"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Bimbo Artesano frutos rojos - 250 g",
        "descripcion": "Las galletas Bimbo Artesano frutos rojos en su presentación de 250 g son un producto alimenticio elaborado como snack dulce destinado al consumo como colación. Este tipo de galleta puede consumirse directamente desde el envase o acompañar bebidas como café, leche o té según la preferencia del consumidor. Puede formar parte de meriendas o colaciones durante el día. Su formato permite ingerir las galletas en porciones individuales o compartir el producto. El empaque facilita su transporte ...",
        "codigo_barras": "7441029524192",
        "precio_base": "2.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/806458/galleta-bimbo-artesano-frutos-rojo-250-g-7441029524192.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Cremas Dark 12 pack -432 g",
        "descripcion": "Las galletas Pozuelo Cremas Dark en presentación de 12 unidades y 432 g se utilizan como snack dulce para consumo individual o para compartir en reuniones y meriendas. Su formato permite servir porciones de manera práctica, integrándose en loncheras, pausas de café o consumo en el hogar. Resultan adecuadas para acompañar bebidas calientes o frías, apoyando momentos de descanso. Su empaque facilita el almacenamiento y el consumo progresivo. Son una opción funcional para quienes buscan gal...",
        "codigo_barras": "7441163416810",
        "precio_base": "2.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/822190/galleta-cremas-dark-bs-432-g-ea-7441163416810.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Hershey’s Kisses con crema - 62 g",
        "descripcion": "Las galletas Hershey’s Kisses con crema combinan una base crujiente con un relleno suave y cremoso inspirado en el sabor característico de los chocolates Hershey’s Kisses. Son adecuadas para consumirse como snack, acompañar bebidas calientes o disfrutar en distintos momentos del día. Su presentación permite un consumo práctico y controlado, facilitando llevarlas en loncheras, bolsos o mantenerlas en la despensa del hogar. La combinación de textura crujiente y relleno cremoso ofrece una e...",
        "codigo_barras": "0034000940196",
        "precio_base": "1.86",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/745741/65557_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Oreo Sabor Original 12 Pack - 432 g",
        "descripcion": "Deliciosas galletas Oreo de sabor original en presentación de 12 packs de 36g cada uno, ideales para compartir o disfrutar en cualquier momento. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7590011151110",
        "precio_base": "3.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/706555/48933_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Galletas Pozuelo Cremas Mixtas 12 Pack - 378 g",
        "descripcion": "Deliciosas galletas Pozuelo con relleno de vainilla, ideales para disfrutar en cualquier momento del día. Su textura cremosa y sabor exquisito las hacen perfectas para acompañar con leche, café o té. Presentadas en un empaque de 378g, son ideales para compartir con la familia y amigos. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actua...",
        "codigo_barras": "0086581005085",
        "precio_base": "1.88",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/747098/53768_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Muffin Chocolate",
        "descripcion": "Muffin Chocolate la opción perfecta para acompañar tus desayunos, cafés de la tarde o momentos de compartir en la mesa. Este producto destaca por su cuidadoso proceso de horneado, ofreciendo una textura ideal, frescura y un perfil de sabor balanceado que resalta en cada mordida. Una alternativa sumamente versátil que se adapta a cualquier ocasión, garantizando ese toque tradicional y reconfortante que buscas en la panadería de calidad.",
        "codigo_barras": "0000000006378",
        "precio_base": "0.55",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/892233/M-5_walmartsv_rSPemPyNmQ_74796_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Feastables, Sabor Milk Chocolate - 35 g",
        "descripcion": "¡Descubre el placer irresistible de los Chocolate Feastables, Sabor Milk Chocolate! Esta deliciosa barra de chocolate de 35 g está diseñada para satisfacer los antojos más dulces y ofrecerte un momento de felicidad en cada bocado. Fabricada por la reconocida marca Feastables, cada pieza refleja un compromiso con la calidad y el sabor excepcional. El chocolate con sabor a leche se derrite suavemente en tu boca, brindando una experiencia de textura cremosa que es simplemente divina. Perfec...",
        "codigo_barras": "0850027880174",
        "precio_base": "2.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/767585/101819_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Feastables Sabor Milk Chocolate - 60 g",
        "descripcion": "Disfruta de una experiencia indulgente con las Chocolate Feastables Sabor Milk Chocolate de Mr. Beast, presentadas en un conveniente paquete de 60 g. Estas deliciosas tabletas de chocolate son perfectas para aquellos que buscan el equilibrio ideal entre cremosidad y dulzura. Con cada bocado, sentirás cómo se derrite en tu boca, gracias a su exquisita textura y su rico sabor a chocolate con leche.Cada tableta está elaborada con ingredientes de alta calidad, lo que garantiza un placer auté...",
        "codigo_barras": "0850027880129",
        "precio_base": "3.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/702198/101817_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Choco Trio Nestlé Sabor Chocolate - 90 g",
        "descripcion": "El Chocolate CHOCO TRIO NESTLÉ® Sabor Chocolate ofrece una experiencia intensa gracias a su sabor profundo y equilibrado, ideal para quienes disfrutan de la riqueza del cacao en cada bocado. Presentado en una barra de 90 gramos, es práctico para compartir o consumir en cualquier momento del día. Su textura suave y cremosa se complementa con un perfil aromático que resalta la esencia del chocolate tradicional. Perfecto para acompañar bebidas calientes, utilizar en repostería o simplemente...",
        "codigo_barras": "7891000377598",
        "precio_base": "2.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/772062/109921_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate El Buen Chocolate tablilla extra grande - 450 g",
        "descripcion": "El chocolate El Buen Chocolate tablilla extra grande en su presentación de 450 g, es una opción práctica para preparar bebidas calientes y distintas recetas tradicionales en el hogar. Su formato facilita su uso en porciones según la necesidad, permitiendo incorporarlo en preparaciones como chocolate caliente, postres o mezclas caseras que requieran un sabor característico. Resulta adecuado para compartir en familia y para disfrutar en momentos especiales o de consumo cotidiano. Su presen...",
        "codigo_barras": "7411700100052",
        "precio_base": "2.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408934/El-Buen-Chocolate-Tablilla-Xgrande-450Gr-1-10472.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Helado Dos Pinos proteína chocolate con chispas de chocolate - 252 g",
        "descripcion": "Disfruta del delicioso Helado Dos Pinos Proteína Sabor Chocolate con Chispas de Chocolate en su presentación de 252 g, una opción ideal para quienes buscan un postre indulgente y nutritivo. Con su cremoso sabor a chocolate y la adición de chispas de chocolate, este helado no solo satisface tu antojo, sino que también te ofrece una fuente de proteína que lo convierte en una opción más equilibrada.",
        "codigo_barras": "7441001630903",
        "precio_base": "3.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/640307/71188_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Kikitos Sabor Chocolate 54gr",
        "descripcion": "Kikitos Sabor Chocolate 54gr",
        "codigo_barras": "7413402802432",
        "precio_base": "0.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/943544/M-5_walmartsv_koQSIhcNwq_126793_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Botoneta Best Chocolate 108gr",
        "descripcion": "Botonetas Chocolate 12 unidades el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "0756956005674",
        "precio_base": "1.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/942846/M-5_walmartsv_jAETdvQSQp_123039_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Domino Chocolate 2 Und",
        "descripcion": "El dominó de chocolate en su presentación de 2 unidades, es una opción dulce y práctica para compartir, disfrutar como merienda o servir como postre en momentos de consumo cotidiano. Su formato facilita dividir porciones y llevar una alternativa lista para acompañar café, leche, chocolate caliente, té o bebidas de preferencia. Puede colocarse en loncheras, mesas de postres o disfrutarse en casa durante la tarde. Es conveniente para quienes buscan un producto de repostería sencillo, fácil...",
        "codigo_barras": "2571020000007",
        "precio_base": "1.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/303155/Domino-Chocolate-2-Und-1-14238.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Snickers Minis Milk Chocolate Maní Y Caramelo - 124.7 g",
        "descripcion": "Snickers Minis es un delicioso chocolate de leche relleno de maní y caramelo, perfecto para esos momentos en los que necesitas un pequeño antojo. Vienen en un práctico empaque de 124.7g que es ideal para compartir o disfrutar individualmente.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0040000015024",
        "precio_base": "3.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/723801/47096_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Caliente Nestlé Rich Chocolate Caja 50 unidades -  1.01 kg",
        "descripcion": "Nestlé Hot Cocoa Mix en su presentación de 1.01 kg ofrece una deliciosa experiencia de chocolate caliente con un sabor intenso y reconfortante. en su presentación de 1.01 kg ofrece una deliciosa experiencia de chocolate caliente con un sabor intenso y reconfortante. Su preparación es sencilla y permite disfrutar un momento cálido en cualquier momento del día. Con el respaldo de Nestlé, este chocolate caliente es perfecto para compartir, consentirse o acompañar desayunos y meriendas con u...",
        "codigo_barras": "0050000143740",
        "precio_base": "16.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/869308/chocolate-caliente-nestle-rich-chocolate-caja-50-unidades-1-01-kg-0050000143740.webp"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Hershey's's De Almendras Con Chocolate Share Pack - 283 g",
        "descripcion": "Los chocolates Hershey's Kisses con almendra en presentación share pack de 283 g son una opción práctica para disfrutar como golosina, compartir en reuniones o utilizar como complemento en postres y celebraciones. Su formato permite servir porciones individuales con facilidad, lo que los hace adecuados para mesas de dulces, meriendas, detalles para compartir o antojos durante el día. También pueden incorporarse en repostería casera y otras preparaciones dulces según la preferencia. Esta ...",
        "codigo_barras": "0034000134533",
        "precio_base": "8.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/405096/Choc-Hersheys-Almen-Choc-Share-Pck-283Gr-1-2425.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Helado Sarita Chocolate 500 g",
        "descripcion": "Helado Sarita Chocolate - 500 g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "7401090801639",
        "precio_base": "3.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/879014/helado-sarita-chocolate-500-g-7401090801639.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Socado Naranja Almendra 230gr",
        "descripcion": "Chocolate Socado Naranja Almendra 230gr",
        "codigo_barras": "8000017110930",
        "precio_base": "5.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/926892/M-5_walmartsv_WtOwmWlZfI_124938_01.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Syrup Hersheys Shell Chocolate 7.25Oz",
        "descripcion": "Syrup Hersheys Shell Chocolate 7.25Oz desarrollado bajo altos estándares para ofrecer una experiencia indulgente y llena de sabor en cada ocasión. Su versatilidad lo convierte en el aliado ideal para incorporar en tus desayunos, postres o reuniones sociales, garantizando esa sensación agradable que buscas en un producto de su categoría. Una elección inteligente que combina gran aceptación y la practicidad necesaria para tus días.",
        "codigo_barras": "0034000006007",
        "precio_base": "5.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/936639/syrup-hersheys-shell-chocolate-7-25-oz-0034000006007.jpg"
    },
    {
        "categoria": "Snacks y Golosinas",
        "nombre": "Chocolate Socado Bolsa Blancorojo 1000gr",
        "descripcion": "Chocolate Socado Bolsa Blancorojo 1000gr",
        "codigo_barras": "8000017110367",
        "precio_base": "15.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/926697/M-5_walmartsv_qTljZCfCQU_124967_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Franks 400 Gramos",
        "descripcion": "Salchicha Franks 400 Gramos",
        "codigo_barras": "7401004590048",
        "precio_base": "1.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/917256/M-5_walmartsv_ojnWXWqDsl_125604_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Fud de pavo - 500 g",
        "descripcion": "Salchicha de pavo Fud, deliciosa y nutritiva, ideal para comidas rápidas y saludables. Perfecta para asar o cocinar en sartenes, manteniendo el sabor y los nutrientes del pavo. Empaque de 500 g. Es ideal para disfrutar en cualquier momento del día, ya sea en el desayuno, en un sándwich, como parte de un plato principal o en una receta rápida.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especific...",
        "codigo_barras": "7501040003417",
        "precio_base": "2.7",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/766716/53101_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha De Pollo Richi - 400 g",
        "descripcion": "Salchicha De Pollo Richi - 400 g la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "7414100200728",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/456344/Salchicha-De-Pollo-400-G-Richi-1-48722.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Pollo Sihamcita 3 30 g",
        "descripcion": "La salchicha de pollo Sihamcita en su presentación de 330 g, es una opción práctica para preparar hot dogs, desayunos, meriendas saladas o comidas rápidas en el hogar. Puede calentarse en sartén, plancha, agua caliente, parrilla u horno, y servirse con pan, huevos, arroz, ensaladas, papas, vegetales o salsas de preferencia. Su formato permite dosificar porciones según el consumo del hogar y conservar el resto siguiendo las indicaciones del empaque. Es una alternativa conveniente para qui...",
        "codigo_barras": "7410031940030",
        "precio_base": "1.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/890274/M-5_walmartsv_UVOEguRLyD_81981_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha De Pollo Tamano Fam 800 g Lcr",
        "descripcion": "Salchicha De Pollo Tamaño Fam 800 g Lcr la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "7410010724552",
        "precio_base": "2.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408698/Salchicha-De-Pollo-Tamano-Fam-800Gr-Lcr-1-5874.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha De Pavo Kreef Paquete - 454 g",
        "descripcion": "Salchicha De Pavo Kreef Paquete - 454 g la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "7414100313572",
        "precio_base": "4.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/888805/M-5_walmartsv_eTnDHzyPrx_81055_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha De Pollo Franks 12u - 400 g",
        "descripcion": "La salchicha de pollo con queso Franks es una opción de sabor suave, textura jugosa y toque cremoso, ideal para comidas rápidas o preparaciones familiares. Puede cocinarse a la plancha, sartén, parrilla o integrarse en panes, arroces, pastas, huevos, tacos, guisos y platos con vegetales. Combina bien con mostaza, salsa de tomate, queso, papas, tortillas, ensaladas, frijoles y aderezos cremosos. Es ideal para desayunos completos, almuerzos prácticos, cenas informales, loncheras y reunione...",
        "codigo_barras": "7414101002055",
        "precio_base": "1.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/416009/Salchicha-De-Pollo-Franks-12u-400gr-1-34708.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha La Única Americana - 454 g",
        "descripcion": "La salchicha La Única americana en su presentación de 400 g, es una opción práctica para preparar hot dogs, desayunos, meriendas saladas o comidas rápidas en el hogar. Puede calentarse en sartén, plancha, agua caliente, parrilla u horno, y servirse con pan, huevos, arroz, ensaladas, papas, vegetales o salsas de preferencia. Su formato permite dosificar porciones según el consumo del hogar y conservar el resto siguiendo las indicaciones del empaque. Es una alternativa conveniente para qui...",
        "codigo_barras": "7411900100326",
        "precio_base": "1.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/890331/M-5_walmartsv_cJBdaxdhed_50601_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Pollo Embutido La Campiña 300 g",
        "descripcion": "La salchicha de pollo Campina es una opción de sabor suave, textura jugosa y uso versátil en comidas rápidas o preparaciones caseras. Puede cocinarse a la plancha, sartén, parrilla o integrarse en arroces, pastas, guisos, panes, tacos, huevos y platos con vegetales. Combina bien con mostaza, salsa de tomate, queso, papas, ensaladas, tortillas, frijoles y aderezos cremosos. Es ideal para desayunos completos, almuerzos prácticos, cenas informales, loncheras y reuniones familiares donde se ...",
        "codigo_barras": "7410010724248",
        "precio_base": "1.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408696/Salchicha-La-Campi-a-Del-Rey-De-Pollo-400Gr-1-5864.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Jumbo Americana Toledo - 460 g",
        "descripcion": "Si hay algo capaz de mejorar cualquier platillo, es prepararlo con Toledo. Prepara unas deliciosas Salchichas Jumbo Tipo Americana a la parilla, y compruébalo.",
        "codigo_barras": "7401004530815",
        "precio_base": "2.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/705950/43595_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Eckrich Ahumada Coctel - 794 g",
        "descripcion": "La salchicha ahumada coctel Eckrich en su presentación de 28 oz, es una opción salada de tamaño pequeño, práctica para preparar entradas, meriendas, platos para compartir o comidas rápidas. Su sabor ahumado combina bien con salsas dulces, picantes o cremosas, y puede servirse con papas, arroz, pastas, vegetales, pan, tortillas, ensaladas o como parte de una mesa de picar. También funciona en recetas calientes como guisos, pinchos, salteados y bocadillos. Es conveniente para reuniones fam...",
        "codigo_barras": "0027815002470",
        "precio_base": "11.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/890122/M-5_walmartsv_LOtkakSRRD_53598_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Pollo Super Dog 18 cm 660 g",
        "descripcion": "La salchicha de pollo Super Dog 18 cm en su presentación de 660 g, es una opción práctica para preparar hot dogs, meriendas saladas, comidas rápidas o platos para compartir. Su tamaño permite servirla en panes largos con aderezos, queso, vegetales, salsas, cebolla o acompañamientos como papas, ensaladas y arroz. También puede utilizarse en recetas con huevos, pastas, tortillas, guisos o picadillos, aportando sabor suave y fácil preparación. Es conveniente para reuniones, loncheras, almue...",
        "codigo_barras": "7410031940207",
        "precio_base": "3.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/474862/81982_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha La Única Parrillera Ahumada - 300 g",
        "descripcion": "Salchicha La Única Parrillera Ahumada - 300 g la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "7410031420969",
        "precio_base": "3.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408708/Salchicha-La-nica-Parrillera-Ahumada-300Gr-1-8185.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Tipo Americana Jumbo Con Queso Toledo 2 Pack - 920 g",
        "descripcion": "Salchicha jumbo tipo americana con queso de la marca Toledo. Ideal para parrilladas y comidas rápidas. Viene en un práctico empaque de 2 Uds, Si hay algo capaz de mejorar cualquier platillo, es prepararlo con Toledo.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401004531898",
        "precio_base": "4.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/702844/43597_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Con Pavo Fud fuente de Proteína - 266 g",
        "descripcion": "Salchicha de pavo en presentación de 266 gramos, elaborada con carne magra y seleccionada para ofrecer una opción saludable y sabrosa. Su textura firme y jugosa, combinada con un sabor suave, la hace ideal para preparar platillos variados como hot dogs, guisos o snacks. Bajo en grasas saturadas y con un perfil nutricional equilibrado, es una alternativa nutritiva para quienes buscan cuidar su alimentación sin renunciar al sabor. Además, su empaque práctico facilita su almacenamiento y us...",
        "codigo_barras": "7501040009761",
        "precio_base": "1.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/755513/53112_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Eckrich Ahumada Tocino y Cheddar - 13 oz",
        "descripcion": "Salchicha Eckrich ahumada tocino cheddar - 369 g la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "0027815300996",
        "precio_base": "5.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/273270/Eck-Salchicha-Ahumada-Tocin-Cheddar-130Z-1-20040.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jimmy Dean muffin huevo queso salchicha - 521 g",
        "descripcion": "El muffin Jimmy Dean egg cheese sausage en presentación de 510 g es una opción práctica para resolver desayunos o comidas rápidas dentro de la rutina diaria. Su formato resulta conveniente para quienes buscan una alternativa fácil de preparar y servir en casa. Puede disfrutarse como desayuno, merienda o comida ligera según la ocasión, adaptándose a distintos momentos del día. Esta presentación permite disponer de varias porciones en un solo empaque y ayuda a organizar mejor el consumo se...",
        "codigo_barras": "0077900502132",
        "precio_base": "9.99",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/849090/jimmy-dean-muffin-egg-cheese-sau-510-gr-0077900502132.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Toledo Hot Dog 12 pack - 460 g",
        "descripcion": "El soporte I2Go Zero Gravity está diseñado para sostener dispositivos móviles de forma estable durante el uso cotidiano en escritorios, oficinas o espacios de trabajo en el hogar. Su formato permite ajustar el ángulo de visualización, facilitando actividades como videollamadas, lectura de contenido, visualización de videos o navegación prolongada sin necesidad de sostener el dispositivo. Es adecuado para teléfonos inteligentes y dispositivos compatibles, integrándose a rutinas de trabajo...",
        "codigo_barras": "7401004530013",
        "precio_base": "1.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/669009/43594_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Toledo tipo Americana con Queso - 460 g",
        "descripcion": "¿Con antojo de algo diferente? Prueba estas ricas Salchichas Tipo Americana con Queso Toledo. Si hay algo capaz de mejorar cualquier platillo, es prepararlo con Toledo.",
        "codigo_barras": "7401004530938",
        "precio_base": "2.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/669007/43596_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Gwalney Salchicha de Pollo Para Hotdog Original - 340 g",
        "descripcion": "Gwalney Salchicha de Pollo Para Hotdog Original - 340 g la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "0785331757129",
        "precio_base": "3.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408937/Salchicha-Gwalney-Pollo-Hotdog-Original-12onzas-1-27210.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha Fud Con Pavo Hot Dog - 500 g",
        "descripcion": "Deliciosa salchicha de pavo Fud, ideal para preparar hot dogs. De excelente sabor y calidad, hace que cada bocado sea irresistible. Perfecta para tus reuniones y comidas rápidas favoritas. Presentación de 500 g.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7501040009839",
        "precio_base": "3.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/739477/53113_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Salchicha de Pavo Fud - Precio Indicado por Libra (454 g)",
        "descripcion": "Salchicha de Pavo Fud - Precio Indicado por Libra (454 g) la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "2587010000001",
        "precio_base": "2.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/889830/M-5_walmartsv_XxtSuNZjqm_62689_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Virginia Kreff Lb",
        "descripcion": "Jamón Virginia Kreff Lb la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "2587860000008",
        "precio_base": "8.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/888718/M-5_walmartsv_cMfXxLcsvt_86627_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Miel Smithfield 340g",
        "descripcion": "Jamon Miel Smithfield 340 g la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "0070800233403",
        "precio_base": "7.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/859823/jamon-miel-smithfield-340-g-0070800233403.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Kreef de pavo ahumado",
        "descripcion": "Jamón De Pavo Ahumado Kreef Lb la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "2529290000005",
        "precio_base": "8.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/530813/89456_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Kreef Ahumado - Libra",
        "descripcion": "El jamón ahumado Kreef, es una opción práctica para preparar sándwiches, desayunos, meriendas y comidas ligeras con un sabor característico. Puede combinarse con pan, queso, vegetales, huevos, ensaladas, wraps, galletas saladas o cremas untables según la preferencia del hogar. También puede utilizarse en tablas frías, bocadillos, loncheras o recetas rápidas donde se busque agregar una proteína lista para servir. Su perfil ahumado aporta un toque especial a preparaciones saladas. Se recom...",
        "codigo_barras": "2580950000001",
        "precio_base": "6.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/888728/M-5_walmartsv_FbamZegWtK_84629_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Premium Deli Virginia Gr",
        "descripcion": "El jamón premium Virginia, es una opción práctica para preparar sándwiches, desayunos, meriendas y comidas rápidas en el hogar. Su corte tipo deli facilita servir porciones y combinarlo con pan, queso, vegetales, huevos, ensaladas, wraps o cremas untables según la preferencia. También puede utilizarse en tablas frías, bocadillos o recetas sencillas para loncheras. Su formato permite mantener una cantidad conveniente disponible y dosificar según el consumo familiar. Se recomienda conserva...",
        "codigo_barras": "2577720000002",
        "precio_base": "4.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/888734/M-5_walmartsv_jZfWruljoS_59652_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Underwood, 2Pack -240 g",
        "descripcion": "Jamón Underwood, 2Pack -240 g el aliado perfecto para tener siempre en tu despensa y resolver cualquier comida de forma rápida, práctica y deliciosa. Este producto destaca por su cuidadoso proceso de conservación, manteniendo su frescura, consistencia y un perfil de sabor balanceado listo para disfrutar en cualquier momento. Una alternativa sumamente versátil que se adapta a una gran variedad de recetas, garantizando la calidad que buscas en tu mesa.",
        "codigo_barras": "7411000591413",
        "precio_base": "7.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/430042/Underwood-Jamon-2Pack-240Gr-1-1436.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Black Forest 340 g",
        "descripcion": "El jamón selva negra Smithfield es un embutido de sabor ahumado, textura suave y carácter delicado, ideal para preparar comidas frías o calientes con un toque especial. Puede utilizarse en sándwiches, wraps, paninis, omelets, ensaladas, tablas de embutidos, canapés o bocadillos para compartir. Combina bien con quesos, panes, lechuga, tomate, pepinillos, mostaza, mayonesa, frutas y galletas saladas. Es ideal para desayunos salados, almuerzos ligeros, cenas informales y reuniones donde se ...",
        "codigo_barras": "0070800233410",
        "precio_base": "7.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/859838/jamon-black-forest-340-g-0070800233410.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón De Pavo Kreef, Delgado -454g",
        "descripcion": "El jamón de pavo Kreef delgado, es una opción práctica para preparar sándwiches, desayunos, meriendas y comidas ligeras en el hogar. Su corte delgado facilita servir porciones y combinarlo con pan, queso, vegetales, huevos, ensaladas, wraps, galletas saladas o aderezos de preferencia. También puede utilizarse en loncheras, tablas frías, bocadillos o recetas sencillas donde se busque una proteína lista para servir. Es una alternativa conveniente para mantener disponible en refrigeración y...",
        "codigo_barras": "7414100311011",
        "precio_base": "5.05",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/890372/M-5_walmartsv_AHofSxfvMz_84628_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Underwood, 4Pack -480 g",
        "descripcion": "Jamón Underwood, 4Pack -480 g el aliado perfecto para tener siempre en tu despensa y resolver cualquier comida de forma rápida, práctica y deliciosa. Este producto destaca por su cuidadoso proceso de conservación, manteniendo su frescura, consistencia y un perfil de sabor balanceado listo para disfrutar en cualquier momento. Una alternativa sumamente versátil que se adapta a una gran variedad de recetas, garantizando la calidad que buscas en tu mesa.",
        "codigo_barras": "7411000501399",
        "precio_base": "14.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/430041/Underwood-Jamon-4Pack-480Gr-1-1419.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Familiar 397 Gr Kreef",
        "descripcion": "El jamón familiar Kreef en su presentación de 397 g, es una opción práctica para preparar sándwiches, desayunos, meriendas y comidas rápidas en el hogar. Su formato facilita servir porciones y combinarlo con pan, queso, vegetales, huevos, ensaladas, wraps, galletas saladas o aderezos de preferencia. También puede utilizarse en loncheras, tablas frías, bocadillos o recetas sencillas donde se busque agregar una proteína lista para servir. Es una alternativa conveniente para mantener dispon...",
        "codigo_barras": "7414100310021",
        "precio_base": "4.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/761787/85793_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón De Pavo Toledo - 200 g",
        "descripcion": "El jamón de pavo Toledo en presentación de 200 g es una alternativa práctica para complementar desayunos, meriendas, emparedados y distintas comidas de uso diario. Su formato facilita porcionarlo y utilizarlo en sandwiches, wraps, bocadillos y otras preparaciones donde se busca un ingrediente fácil de servir y combinar. Esta presentación resulta conveniente para mantener una cantidad manejable en refrigeración y disponer de varias porciones listas para usar. También puede incorporarse en...",
        "codigo_barras": "7401004510558",
        "precio_base": "1.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/702852/80570_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Toledo Prensado - 230 g",
        "descripcion": "Jamón Prensado Toledo de 230g, ideal para sandwiches y bocadillos. Elaborado con carne seleccionada y prensada para un sabor suave y textura firme. Perfecto para disfrutar con amigos y familia.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401004510428",
        "precio_base": "1.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/729549/43576_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Serrano 80 g La Alegria",
        "descripcion": "El jamón serrano La Alegría es un embutido curado de sabor intenso, textura delicada y aroma característico, ideal para servir en entradas, tablas frías y bocadillos especiales. Su perfil salado combina bien con panes, quesos, aceitunas, frutos secos, tomate, aceite de oliva, frutas frescas y galletas saladas. Puede disfrutarse en tapas, canapés, ensaladas, paninis o acompañamientos para reuniones. Es ideal para cenas ligeras, celebraciones, picadas gourmet y comidas donde se busca un to...",
        "codigo_barras": "7401122301373",
        "precio_base": "4.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/490057/85710_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Kreef, Pavo Ahumado Brandenburg -227g",
        "descripcion": "El jamón Kreef de pavo ahumado Brandenburg es un embutido de sabor suave con notas ahumadas, textura uniforme y perfil versátil para comidas rápidas o preparaciones frías. Puede utilizarse en sándwiches, wraps, paninis, omelets, ensaladas, canapés, tablas sencillas o meriendas saladas. Combina bien con pan, queso, lechuga, tomate, pepinillos, aguacate, mayonesa, mostaza y galletas saladas. Es ideal para desayunos prácticos, almuerzos ligeros, loncheras, cenas informales y reuniones famil...",
        "codigo_barras": "7414100311851",
        "precio_base": "5.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/887407/M-5_walmartsv_ZLeRGPHpxN_43861_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Underwood Roast Beef 120 g",
        "descripcion": "Jamón Underwood Roast Beef 120 g el aliado perfecto para tener siempre en tu despensa y resolver cualquier comida de forma rápida, práctica y deliciosa. Este producto destaca por su cuidadoso proceso de conservación, manteniendo su frescura, consistencia y un perfil de sabor balanceado listo para disfrutar en cualquier momento. Una alternativa sumamente versátil que se adapta a una gran variedad de recetas, garantizando la calidad que buscas en tu mesa.",
        "codigo_barras": "4780000029381",
        "precio_base": "3.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/953421/M-5_walmartsv_UPvuPpdIYT_85076_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Superior, Familiar - 200 g",
        "descripcion": "Jamón Superior, Familiar - 200 g la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "7411900304601",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/888801/M-5_walmartsv_UPCBpMSyOc_72582_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Kreef, Redondo Ahumado Paquete -454g",
        "descripcion": "Jamón Kreef, Redondo Ahumado Paquete -454g la fuente de proteína ideal para convertirse en el plato fuerte de tus almuerzos, cenas o parrilladas familiares. Destaca por su cuidadoso proceso de selección y empaque, asegurando una textura tierna, gran jugosidad y el perfil de sabor perfecto para tus recetas culinarias. Una alternativa sumamente versátil y rendidora en la cocina, ideal para quienes buscan calidad, frescura y el complemento perfecto para una nutrición balanceada.",
        "codigo_barras": "7414100310243",
        "precio_base": "5.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/889560/M-5_walmartsv_VlrPzshlsZ_86884_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Deshuesado 80 g La Alegria",
        "descripcion": "El jamón 4D La Alegría deshuesado en su presentación de 80 g, es una opción práctica para preparar sándwiches, desayunos, meriendas o bocadillos rápidos en el hogar. Su formato permite servir porciones pequeñas y combinarlo con pan, queso, vegetales, huevos, ensaladas, galletas saladas, cremas untables o salsas de preferencia. Puede utilizarse en loncheras, tablas frías o recetas sencillas donde se busque un ingrediente listo para consumir. Es una alternativa conveniente para quienes nec...",
        "codigo_barras": "7401122302059",
        "precio_base": "5.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/490070/85713_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon Underwood Chicken Spread 120 g",
        "descripcion": "Jamón Underwood Chicken Spread 120 g el aliado perfecto para tener siempre en tu despensa y resolver cualquier comida de forma rápida, práctica y deliciosa. Este producto destaca por su cuidadoso proceso de conservación, manteniendo su frescura, consistencia y un perfil de sabor balanceado listo para disfrutar en cualquier momento. Una alternativa sumamente versátil que se adapta a una gran variedad de recetas, garantizando la calidad que buscas en tu mesa.",
        "codigo_barras": "4780000021323",
        "precio_base": "3.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/959971/M-5_walmartsv_dLOfxmMSOT_85075_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Kreef, Baby Ham Paquete -454g",
        "descripcion": "El jamón Kreef Baby Ham es un embutido de sabor suave, textura tierna y perfil clásico, ideal para preparar comidas frías o calientes con un toque delicado. Puede utilizarse en sándwiches, paninis, wraps, omelets, ensaladas, tablas de embutidos, canapés o bocadillos para compartir. Combina bien con quesos, panes, lechuga, tomate, pepinillos, mostaza, mayonesa, frutas y galletas saladas. Es ideal para desayunos salados, almuerzos ligeros, cenas informales y reuniones donde se busca un jam...",
        "codigo_barras": "7414100310069",
        "precio_base": "6.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/890392/M-5_walmartsv_soTlHSGZlC_43856_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamon De Pollo Richi - 200 g",
        "descripcion": "El jamón de pollo Richi en su presentación de 200 g, es una opción práctica para preparar sándwiches, desayunos, meriendas y comidas ligeras durante el día. Puede combinarse con pan, queso, vegetales, huevos, ensaladas, wraps, galletas saladas, cremas untables o aderezos según la preferencia del consumidor. También es útil para loncheras, tablas frías o bocadillos en reuniones pequeñas, ya que facilita armar preparaciones rápidas sin cocinar. Es una alternativa conveniente para quienes b...",
        "codigo_barras": "7414100200759",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/456345/Jamon-De-Pollo-200-G-Richi-1-48723.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Underwood endiablado - 4.25 oz",
        "descripcion": "El jamón Underwood endiablado de 4.25 oz es una opción práctica para preparar bocadillos, meriendas y comidas ligeras con un producto listo para untar o incorporar en distintas recetas. Su textura permite utilizarlo en pan, galletas saladas, tostadas, sándwiches y canapés, facilitando una preparación rápida en casa, oficina o reuniones informales. También puede emplearse como base para rellenos, dips o mezclas sencillas con otros ingredientes, ofreciendo versatilidad en el uso diario. Su...",
        "codigo_barras": "0047800000144",
        "precio_base": "3.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/477473/51518_01.jpg"
    },
    {
        "categoria": "Embutidos y Carnes",
        "nombre": "Jamón Curado Villani, Prosciutto -100 g",
        "descripcion": "El jamón curado Villani de 100 g es una opción práctica para complementar tablas de aperitivos, bocadillos, sándwiches y distintas preparaciones frías o ligeramente calientes. Su estilo curado le aporta una textura firme y un sabor característico que puede disfrutarse solo o acompañado de quesos, pan, aceitunas, frutas o vegetales. Su presentación resulta conveniente para porciones controladas en el hogar, reuniones o meriendas especiales. Es una alternativa versátil para quienes buscan ...",
        "codigo_barras": "7401122300031",
        "precio_base": "7.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/415974/Jamon-Curado-Prosciutto-Villani-100G-1-21330.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Peperecha",
        "descripcion": "El pan peperecha es una opción tradicional de panadería, con sabor dulce, textura suave y estilo casero, ideal para disfrutar en desayunos, meriendas o reuniones familiares. Su perfil clásico combina muy bien con café, leche, chocolate caliente, té, atol o bebidas frías. Puede servirse solo o acompañado de mantequilla, queso suave, jaleas o cremas dulces. Es ideal para quienes buscan un pan con carácter tradicional, agradable para compartir y fácil de integrar en una mesa de pan dulce, c...",
        "codigo_barras": "0000000006279",
        "precio_base": "0.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/890143/M-5_walmartsv_rGEMuMGElR_40129_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan concha Pan Sinaí - 48 g",
        "descripcion": "El pan concha Pan Sinaí de 48 g es una pieza de pan dulce ideal para disfrutar en desayunos, meriendas o pausas del día con una presentación práctica y lista para consumir. Su textura suave y su estilo tradicional lo convierten en una opción agradable para acompañar café, leche, chocolate caliente o bebidas frías según preferencia. Su tamaño individual resulta conveniente para porciones controladas y para llevar en lonchera, bolso o servir como snack en diferentes momentos. Puede disfrut...",
        "codigo_barras": "7413402800070",
        "precio_base": "0.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/470020/41620_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Blanco Baguette",
        "descripcion": "El pan baguette de Producción Crío BADU destaca por su textura crujiente por fuera y su miga suave y aireada en el interior. Elaborado con ingredientes seleccionados y siguiendo métodos tradicionales, este pan es ideal para acompañar comidas, preparar sándwiches gourmet o disfrutar con mantequilla, quesos o embutidos. Su forma alargada y corteza dorada lo convierten en una opción versátil y atractiva en la mesa. Puede servirse caliente o a temperatura ambiente, conservando su sabor autén...",
        "codigo_barras": "2502280000001",
        "precio_base": "0.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/757774/86237_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Sinai Pan Quesadilla",
        "descripcion": "Sinai Pan Quesadilla la opción perfecta para acompañar tus desayunos, cafés de la tarde o momentos de compartir en la mesa. Este producto destaca por su cuidadoso proceso de horneado, ofreciendo una textura ideal, frescura y un perfil de sabor balanceado que resalta en cada mordida. Una alternativa sumamente versátil que se adapta a cualquier ocasión, garantizando ese toque tradicional y reconfortante que buscas en la panadería de calidad.",
        "codigo_barras": "7413402800391",
        "precio_base": "0.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/470069/41622_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Telera Unidad",
        "descripcion": "El pan telera es una pieza tradicional de la panadería mexicana, reconocida por su forma ovalada y ligeramente aplanada, con tres cortes característicos en la parte superior. Su corteza es suave y ligeramente dorada, mientras que el interior es esponjoso, blanco y con una miga consistente que lo hace ideal para una gran variedad de preparaciones. Gracias a su textura equilibrada y su sabor neutro, este pan es perfecto para la elaboración de tortas, molletes, acompañamientos de guisos o s...",
        "codigo_barras": "0000000005692",
        "precio_base": "0.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/401294/Pan-Telera-Unidad-1-27.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Stick   55 Natural",
        "descripcion": "El pan stick 55 natural es un maquillaje en barra práctico y versátil que ofrece una cobertura uniforme para disimular imperfecciones, manchas y ojeras, dejando un acabado natural y duradero. Su textura cremosa se desliza fácilmente sobre la piel, permitiendo una aplicación rápida y sin esfuerzo. El tono natural está pensado para pieles claras a medias, brindando un aspecto equilibrado y fresco. Gracias a su formato en barra, es ideal para llevar en el bolso y realizar retoques en cualqu...",
        "codigo_barras": "7702044031851",
        "precio_base": "8.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/760796/103834_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Polvo De Pan Simple Krisppys",
        "descripcion": "Polvo De Pan Simple Krisppys destaca por su calidad y funcionalidad, siendo una opción confiable en cada uso. Pensado para facilitar la vida del consumidor, ofrece practicidad sin sacrificar la calidad. Una compra inteligente que garantiza satisfacción en cada uso.",
        "codigo_barras": "7411202900921",
        "precio_base": "2.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/447205/Polvo-De-Pan-Simple-Krisppys-1-49032.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Baguette Con Ajo",
        "descripcion": "Pan baguette con ajo de elaboración artesanal, ideal para acompañar tus comidas. Con una textura crujiente por fuera y suave por dentro, tiene el sabor característico del ajo fresco. Perfecto para aperitivos o platillos principales. Contenido 1 unidad.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0000000006064",
        "precio_base": "0.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/419873/Pan-Baguette-Con-Ajo-1-37886.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Marquesote - Unidad",
        "descripcion": "El pan marquesote, es una opción tradicional de panadería para acompañar desayunos, meriendas o momentos de consumo en el hogar. Su textura suave y sabor dulce lo hacen adecuado para disfrutar solo o junto con café, leche, chocolate caliente, té u otras bebidas de preferencia. Su formato por unidad permite comprar la cantidad necesaria para consumo inmediato o para compartir en una ocasión específica. Es una alternativa conveniente para tener disponible en la cocina y servir como complem...",
        "codigo_barras": "0000000001618",
        "precio_base": "0.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/887403/pan-marquesote-unidad-0000000001618.webp"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Croissant - Por Unidad",
        "descripcion": "Pan Croissant - Unidad la opción perfecta para acompañar tus desayunos, cafés de la tarde o momentos de compartir en la mesa. Este producto destaca por su cuidadoso proceso de horneado, ofreciendo una textura ideal, frescura y un perfil de sabor balanceado que resalta en cada mordida. Una alternativa sumamente versátil que se adapta a cualquier ocasión, garantizando ese toque tradicional y reconfortante que buscas en la panadería de calidad.",
        "codigo_barras": "0000000002851",
        "precio_base": "0.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/889894/M-5_walmartsv_LtjOBqLroa_40106_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Lido Bollo 300 g",
        "descripcion": "Pan Lido Bollo 300 g la opción perfecta para acompañar tus desayunos, cafés de la tarde o momentos de compartir en la mesa. Este producto destaca por su cuidadoso proceso de horneado, ofreciendo una textura ideal, frescura y un perfil de sabor balanceado que resalta en cada mordida. Una alternativa sumamente versátil que se adapta a cualquier ocasión, garantizando ese toque tradicional y reconfortante que buscas en la panadería de calidad.",
        "codigo_barras": "7410031460002",
        "precio_base": "1.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960529/M-5_walmartsv_sTtVSLADxC_48265_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Pirujo Paquete de 10 Unidades",
        "descripcion": "El pan pirujo en su presentación de 10 unidades, es una opción práctica de panadería para acompañar comidas, preparar sándwiches o servir como complemento en desayunos y meriendas. Su formato de piezas individuales facilita compartir, controlar porciones y mantener varias unidades disponibles durante el día. Puede combinarse con queso, jamón, carnes, vegetales, mantequilla, jaleas, cremas untables o salsas de preferencia. También puede calentarse ligeramente para acompañar sopas, pastas,...",
        "codigo_barras": "2569040000008",
        "precio_base": "2.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/890163/M-5_walmartsv_gnAqXgpbvq_54257_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Concha De Vainilla - Precio Por Unidad",
        "descripcion": "Pan Concha De Vainilla - Precio por Unidad la opción perfecta para acompañar tus desayunos, cafés de la tarde o momentos de compartir en la mesa. Este producto destaca por su cuidadoso proceso de horneado, ofreciendo una textura ideal, frescura y un perfil de sabor balanceado que resalta en cada mordida. Una alternativa sumamente versátil que se adapta a cualquier ocasión, garantizando ese toque tradicional y reconfortante que buscas en la panadería de calidad.",
        "codigo_barras": "0000000005968",
        "precio_base": "0.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/889921/M-5_walmartsv_pEVpKmxNRb_74790_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Pirujo Pack 6 - Unidad",
        "descripcion": "Pan Pirujo Pack 6 Unidades la opción perfecta para acompañar tus desayunos, cafés de la tarde o momentos de compartir en la mesa. Este producto destaca por su cuidadoso proceso de horneado, ofreciendo una textura ideal, frescura y un perfil de sabor balanceado que resalta en cada mordida. Una alternativa sumamente versátil que se adapta a cualquier ocasión, garantizando ese toque tradicional y reconfortante que buscas en la panadería de calidad.",
        "codigo_barras": "2571010000000",
        "precio_base": "1.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/889946/M-5_walmartsv_CxPrLZPOYD_54288_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Pullman Lido - 550 g",
        "descripcion": "Pan Pullman Lido - 550 g la opción perfecta para acompañar tus desayunos, cafés de la tarde o momentos de compartir en la mesa. Este producto destaca por su cuidadoso proceso de horneado, ofreciendo una textura ideal, frescura y un perfil de sabor balanceado que resalta en cada mordida. Una alternativa sumamente versátil que se adapta a cualquier ocasión, garantizando ese toque tradicional y reconfortante que buscas en la panadería de calidad.",
        "codigo_barras": "7410031460064",
        "precio_base": "1.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/342601/Pan-Pullman-Lido-550-g-1-37393.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Monarca Sandwich Blanco 480 g",
        "descripcion": "El pan Monarca para sándwich blanco, en su presentación de 480 g, es una opción práctica para acompañar desayunos, meriendas y distintos tiempos de comida. Su formato resulta conveniente para preparar sándwiches, tostadas, bocadillos o consumirlo con mantequilla, mermeladas, quesos y otros complementos de uso cotidiano. El tamaño del empaque permite varias porciones y facilita mantener el producto disponible para la rutina diaria en el hogar. Puede integrarse con facilidad en loncheras, ...",
        "codigo_barras": "7441029503913",
        "precio_base": "1.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/901138/pan-monarca-sandwich-blanco-480-g-7441029503913.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Sinaí sándwich - 540 g",
        "descripcion": "El pan Sinai sándwich en su presentación de 540 g, es una opción práctica y versátil para preparar desayunos, meriendas, almuerzos ligeros o cenas sencillas en el hogar. Su formato resulta adecuado para elaborar sándwiches con diferentes ingredientes, así como para utilizarse en tostadas o preparaciones cotidianas según la preferencia del consumidor. Su textura facilita el manejo y el porcionado, permitiendo un uso cómodo dentro de la cocina diaria. Resulta conveniente para mantener en l...",
        "codigo_barras": "7413402812486",
        "precio_base": "1.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/769344/41645_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Lido Hotdog - 405 g",
        "descripcion": "Pan Lido Hotdog - 405 g la opción perfecta para acompañar tus desayunos, cafés de la tarde o momentos de compartir en la mesa. Este producto destaca por su cuidadoso proceso de horneado, ofreciendo una textura ideal, frescura y un perfil de sabor balanceado que resalta en cada mordida. Una alternativa sumamente versátil que se adapta a cualquier ocasión, garantizando ese toque tradicional y reconfortante que buscas en la panadería de calidad.",
        "codigo_barras": "7413400513170",
        "precio_base": "1.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/381154/Pan-Lido-Hotdog-405Gr-1-1506.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cake Pan La Neveria Med Escoces",
        "descripcion": "El cake pan La Nevería mediano escocés, es una opción dulce y práctica para compartir en celebraciones, reuniones familiares o como postre después de las comidas. Su presentación permite servir porciones de manera sencilla y llevar a la mesa un producto listo para disfrutar sin preparación adicional. Puede acompañarse con café, leche, chocolate caliente, té o bebidas de preferencia, según el momento de consumo. Es una alternativa conveniente para quienes buscan un postre de panadería con...",
        "codigo_barras": "7412700501214",
        "precio_base": "13.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/733146/102942_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Pirujo Con Ajonjoli 3 Und",
        "descripcion": "El pan pirujo con ajonjolí en su presentación de 3 unidades, es una opción práctica de panadería para acompañar comidas, preparar sándwiches o servir como complemento en desayunos y meriendas. Su cubierta con ajonjolí aporta textura y un sabor característico que combina con ingredientes salados o dulces. Puede rellenarse con queso, jamón, carnes, vegetales, cremas untables o disfrutarse solo junto con café, leche o bebidas de preferencia. Su formato facilita compartir y utilizar cada pie...",
        "codigo_barras": "2571000000003",
        "precio_base": "1.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/890183/M-5_walmartsv_jmjWurkVSd_54287_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Espumilla Pan Mama Chela 105 g",
        "descripcion": "Espumilla Pan Mama Chela 105Gr",
        "codigo_barras": "7413405300034",
        "precio_base": "2.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/531444/86876_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Ganada Dulce Alemana 312 g",
        "descripcion": "Pan Granada Dulce Alemana 312Gr",
        "codigo_barras": "7413400700129",
        "precio_base": "1.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/469982/41606_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan integral Lido - 550 g",
        "descripcion": "El pan integral Lido de 550 g es una opción versátil para preparar desayunos, meriendas, loncheras y comidas ligeras con practicidad. Su presentación permite elaborar sándwiches, tostadas, bocadillos y acompañamientos para distintos momentos del día, manteniendo una textura adecuada para combinar con ingredientes dulces o salados. Puede disfrutarse con quesos, embutidos, vegetales, mermeladas, mantequilla de maní o simplemente tostado. El empaque de 550 g brinda un rendimiento convenient...",
        "codigo_barras": "7410031460057",
        "precio_base": "1.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/408712/Pan-Lido-Pullman-Integral-550-Gr-1-8203.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Lido Tostado - 250 g",
        "descripcion": "Pan tostado LIDO, ideal para desayunos y meriendas, crujiente y dorado, elaborado con ingredientes de calidad, en presentación de 250 g. Perfecto para acompañar con mermeladas, mantequilla u otros untables.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7413400503058",
        "precio_base": "2.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/576588/41592_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan para tortas mexicanas venta por unidad",
        "descripcion": "Pan elaborado específicamente para la preparación de tortas mexicanas, caracterizado por su textura suave y miga consistente. Está diseñado para consumo directo como base de emparedados, permitiendo absorber salsas y rellenos sin perder estructura. Es adecuado para utilizarse con carnes, embutidos, vegetales y aderezos, adaptándose a distintas combinaciones. Su formato por unidad facilita el control de porciones y el consumo inmediato. Es una opción práctica dentro de la panadería empaca...",
        "codigo_barras": "0000000003254",
        "precio_base": "0.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/419871/Pan-Tortas-Mexicanas-Precio-por-Unidad-1-37874.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Pan Alemana Rosvill - 204 g",
        "descripcion": "El pan Alemana Rosvill en su presentación de 204 g, es una opción práctica para disfrutar en desayunos, meriendas o como acompañamiento en distintos tiempos de comida. Su textura y sabor lo convierten en una alternativa versátil para consumir solo o combinar con quesos, embutidos, mantequilla, mermeladas u otros ingredientes según la preferencia del consumidor. Su formato facilita el manejo y el porcionado dentro del hogar, permitiendo un uso cómodo en la rutina diaria. Resulta convenien...",
        "codigo_barras": "7412200101846",
        "precio_base": "1.79",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/471379/52702_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Gran Día Cereal Cocoa Flakes - 1000 g",
        "descripcion": "Cocoaflakes gan Día1000 g desarrollado bajo altos estándares para ofrecer una experiencia indulgente y llena de sabor en cada ocasión. Su versatilidad lo convierte en el aliado ideal para incorporar en tus desayunos, postres o reuniones sociales, garantizando esa sensación agradable que buscas en un producto de su categoría. Una elección inteligente que combina gran aceptación y la practicidad necesaria para tus días.",
        "codigo_barras": "7406007082057",
        "precio_base": "3.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/833814/cocoaflakes-gran-dia-1000-g-7406007082057.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kelloggs Special K Cereal Original - 200 g",
        "descripcion": "Cada deliciosa hojuela de Special K Original de Kellogg’s está elaborada con tres distintos cereales: trigo entero, arroz y maíz. Tiene un sabor deliciosamente natural, sin conservadores, sin colorantes, ni saborizantes artificiales. Incorpóralo junto a leche, frutas y yogurt en el desayuno, snack o como cena.Cereal de trigo, maíz y arroz.Gran complemento para tu día a día.Una opción 100% vegetariana.Cuidarte también es delicioso con Special K de Kelloggs. Información del producto: La in...",
        "codigo_barras": "7501008066232",
        "precio_base": "2.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/776934/88419_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Post Fruity Pebbles -311g",
        "descripcion": "Cereal Fruity Pebbles de Post, un cereal dulce y colorido que encanta a los niños y adultos. Ideal para comenzar el día con energía. Cada paquete contiene 311 gramos de crujientes hojuelas con sabor frutal.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0884912129710",
        "precio_base": "6.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/672301/100590_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Nesquik Caja -620 g",
        "descripcion": "Comienza el día con la combinación perfecta de sabor y nutrición con el Cereal Nesquik Chocolate de Nestlé 620 g, una deliciosa opción que transforma el desayuno en el momento favorito de los más pequeños. Con su irresistible sabor a chocolate y una textura crujiente, este cereal no solo encanta al paladar, sino que también aporta los nutrientes esenciales para un día lleno de energía. Información del producto: La información de este producto es proporcionada por fabricantes y distribuid...",
        "codigo_barras": "7501058652690",
        "precio_base": "5.7",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/764894/67648_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Incaparina cereal - 300 g",
        "descripcion": "Incaparina cereal de 300 g es una opción práctica para complementar desayunos y meriendas con una presentación fácil de preparar y servir en el hogar. Su formato resulta conveniente para integrarlo en la rutina diaria, ya sea como parte de una comida de la mañana o en momentos donde se busca una preparación sencilla y rápida. Puede combinarse con leche, bebidas o acompañarse con otros alimentos de consumo cotidiano según la preferencia de cada hogar. Su empaque de 300 g ofrece un rendimi...",
        "codigo_barras": "7406007083153",
        "precio_base": "3.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/757748/86766_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Quaker de Frutas - 312 g",
        "descripcion": "Cereal Fruty Ohs de Quaker, un delicioso cereal dulce con trozos de fruta. Perfecto para el desayuno o como snack. Contiene una mezcla de granos integrales y frutas naturales que brinda un sabor único y nutrición equilibrada en cada porción. Ideal para toda la familia. En su presentación de 312g Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles...",
        "codigo_barras": "0803275000719",
        "precio_base": "2.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/873824/cereal-quaker-de-frutas-312-g-0803275000719.webp"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Nesquik Duo - 300 g",
        "descripcion": "Disfruta de la deliciosa combinación de sabores con el Cereal Nesquik Duo 300 g. Este cereal es perfecto para comenzar el día con energía, ofreciendo un equilibrio ideal entre el chocolate y la vainilla que encantará a grandes y pequeños. Su textura crujiente y su sabor irresistible hacen de cada bocado una experiencia única. Ideal para un desayuno nutritivo o un snack a cualquier hora . ¡No te lo pierdas y pruébalo hoy mismo!",
        "codigo_barras": "7506475125567",
        "precio_base": "3.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/787068/110466_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Bolsa Trix - 340 g",
        "descripcion": "Cereal Bolsa Trix - 340 g desarrollado bajo altos estándares para ofrecer una experiencia indulgente y llena de sabor en cada ocasión. Su versatilidad lo convierte en el aliado ideal para incorporar en tus desayunos, postres o reuniones sociales, garantizando esa sensación agradable que buscas en un producto de su categoría. Una elección inteligente que combina gran aceptación y la practicidad necesaria para tus días.",
        "codigo_barras": "7506475121262",
        "precio_base": "3.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/548971/96326_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Great Value Canela Crunch 538g",
        "descripcion": "Cereal Great Value canela crunch de 538 g, con aros crujientes enriquecidos con sabor a canela que proporciona un desayuno aromático y apetitoso. La canela añade un sabor cálido y especiado que lo diferencia de otros cereales comunes, creando una experiencia de paladar interesante. Cada porción ofrece crujencia sostenida cuando se consume con leche, permitiendo disfrutar de la textura preferida durante varios minutos. Puede consumirse a cualquier hora del día como desayuno, merienda o sn...",
        "codigo_barras": "0194346525638",
        "precio_base": "8.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/891552/cereal-great-value-canela-crunch-538-g-0194346525638.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Malt O Meal Tootie 354 Gr",
        "descripcion": "Cereal Malt-O-Meal Tootie de 354 gramos, un cereal delicioso y colorido que combina diversión y nutrición en cada bocado. Ideal para niños y adultos, este cereal crujiente aporta un toque dulce y un abanico de colores que hacen del desayuno una experiencia alegre y llena de energía. Cada pieza del cereal Malt-O-Meal Tootie destaca por su vibrante mezcla de colores que no solo llaman la atención visualmente, sino que también aportan un sabor dulce y delicioso. Perfecto para quienes buscan...",
        "codigo_barras": "0042400108153",
        "precio_base": "5.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/753324/100583_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kelloggs Corn Flakes - 860 g",
        "descripcion": "Inicia las mañanas en casa con el cereal Corn Flakes de Kellogg's y dale a tu familia una &nbsp;excelente opción para complementar el desayuno. Por su versatilidad puedes combinarlo con leche y fruta o usarlo para realizar diferentes recetas de cocina.&nbsp; Adicionado con vitaminas y hierro. Sin colorantes artificiales. Cereal sin harinas. ¡Este cereal de hojuelas de maíz es un básico que no puede faltar en la alacena!",
        "codigo_barras": "7501008076781",
        "precio_base": "5.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/810952/cereal-kelloggs-corn-flakes-860-g-7501008076781.webp"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kelloggs Corn Flakes - 270 g",
        "descripcion": "Inicia las mañanas en casa con el cereal Corn Flakes de Kellogg's y dale a tu familia una excelente opción para complementar el desayuno. Por su versatilidad puedes combinarlo con leche y fruta o usarlo para realizar diferentes recetas de cocina. • Adicionado con vitaminas y hierro. • Sin colorantes artificiales. • Cereal sin harinas. ¡Este cereal de hojuelas de maíz es un básico que no puede faltar en la alacena!",
        "codigo_barras": "7501008040768",
        "precio_base": "2.59",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/821811/cereal-kelloggs-corn-flakes-270-g-7501008040768.webp"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kelloggs Komplete Almendras - 390 g",
        "descripcion": "El cereal Komplete de almendra de Kellogg's es una opción nutritiva y ligera ideal para un desayuno equilibrado. Enriquecido con fibras y vitaminas, proporciona energía y ayuda a mantener una dieta saludable. Presentado en un empaque de 390 g, es perfecto para toda la familia. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7501008041680",
        "precio_base": "3.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/811002/cereal-kelloggs-komplete-almendras-390-g-7501008041680.webp"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kellogg's Choco Krispis - 620 g",
        "descripcion": "El cereal Choco Krispis de Kellogg's en su presentación de 620 g ofrece una opción de cereal con referencia de chocolate para incorporar a desayunos y meriendas. Puede servirse con leche, combinarse con yogurt o frutas según la preferencia, y también disfrutarse directamente como snack en pequeñas porciones. Su cantidad permite preparar varios tazones para diferentes integrantes del hogar o distribuir el consumo a lo largo de distintos días. Además, puede utilizarse como complemento en a...",
        "codigo_barras": "7501008023556",
        "precio_base": "4.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/927921/cereal-kelloggs-choco-krispis-original-620-g-7501008023556.webp"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kelloggs Komplete Arándanos - 310 g",
        "descripcion": "El cereal Komplete Arándanos de Kellogg's es una combinación de hojuelas de maíz con sabor a cacahuate mezcladas con arándanos, almendras y un toque de miel que le da un sabor ligeramente dulce. Es delicioso y ideal para complementar el desayuno acompañado con leche y fruta o como &nbsp;un snack. Este cereal aporta vitaminas y hierro, nutrientes importantes para toda la familia. ¡Lleva tus cereales Kelloggs contigo!",
        "codigo_barras": "7501008005538",
        "precio_base": "4.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/810964/cereal-kelloggs-komplete-arandanos-310-g-7501008005538.webp"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kelloggs Zucaritas Chocolate - 480 g",
        "descripcion": "Zucaritas sabor chocolate es un cereal de hojuelas de maíz con sabor a chocolate producido por Kellogg's. Está disponible en Nicaragua y otros países de América Central. El cereal está hecho con hojuelas de maíz recubiertas de un glaseado con sabor a chocolate y también están cubiertas con mini malvaviscos. Granos integrales: El chocolate Zucaritas sabor está elaborado con granos integrales, que son una buena fuente de fibra. La fibra puede ayudar a promover la salud digestiva, regular l...",
        "codigo_barras": "7501008042847",
        "precio_base": "4.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/738617/46405_01.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Suli Hojuelas Azúcaradas - 1200 g",
        "descripcion": "Delicioso cereal de hojuelas azucaradas, ideal para un desayuno energético. Presentado por Suli, este cereal combina el sabor crujiente con la dulzura perfecta. Perfecto para consumir con leche o yogur. Paquete de 1200g Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7441078221363",
        "precio_base": "3.7",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/869389/cereal-suli-hojuelas-azucaradas-1200-g-7441078221363.jpg"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kelloggs Komplete Coco - 310 g",
        "descripcion": "El cereal Komplete sabor a Coco con Almendras de Kellogg's es una combinación de hojuelas de maíz sabor a coco mezcladas con almendras y chips de coco. Tiene un sabor delicioso y es ideal para complementar el desayuno acompañado con leche y fruta o como un &nbsp;snack. Este cereal aporta vitaminas y hierro, nutrientes importantes para toda la familia.&nbsp; ¡Lleva tus cereales Kelloggs contigo!",
        "codigo_barras": "7501008031759",
        "precio_base": "3.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/810998/cereal-kelloggs-komplete-coco-310-g-7501008031759.webp"
    },
    {
        "categoria": "Panadería y Desayuno",
        "nombre": "Cereal Kelloggs Komplete Almendras - 610 g",
        "descripcion": "El cereal Komplete de almendras de Kellogg's es una combinación de hojuelas de maíz, avena, arroz y trigo, mezcladas con almendras. Tiene un sabor delicioso y es una gran opción para el desayuno acompañado con leche y fruta o como un &nbsp;snack. Este cereal aporta vitaminas y hierro, nutrientes importantes para toda la familia.&nbsp; ¡Lleva tus cereales Kelloggs contigo!",
        "codigo_barras": "7501008014141",
        "precio_base": "5.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/810969/cereal-kelloggs-komplete-almendras-610-g-7501008014141.webp"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Domo Strudell Manzana",
        "descripcion": "El strudel de manzana en domo, es una opción dulce de panadería para disfrutar como merienda, postre o acompañamiento de bebidas calientes. Su relleno con sabor a manzana aporta un perfil frutal agradable, ideal para quienes prefieren preparaciones suaves y dulces. El empaque tipo domo ayuda a proteger el producto y facilita su manejo, traslado y servicio antes de consumirlo. Puede acompañarse con café, leche, chocolate caliente, té o bebidas de preferencia, según el momento del día. Es ...",
        "codigo_barras": "2569240000006",
        "precio_base": "3.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/889878/M-5_walmartsv_NeWCEqiQQK_54267_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Colado Etif Manzana 113gr",
        "descripcion": "El colado Etiflex de manzana en su presentación de 113 g ofrece una opción de textura suave y sabor frutal para complementar comidas o meriendas infantiles. Su formato individual facilita servir una porción sin procesos extensos, llevarla en el bolso de cuidado o mantenerla disponible para paseos, visitas y momentos fuera de casa. Puede incorporarse dentro de una rutina de alimentación acorde con la etapa del niño y combinarse con otros alimentos apropiados para crear opciones variadas. ...",
        "codigo_barras": "7443013820419",
        "precio_base": "0.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/892053/M-5_walmartsv_YPvMfcifGw_123169_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Gala Paquete - 6 Unidades",
        "descripcion": "Manzana Gala SIN MARCA, paquete de manzanas frescas y dulces, ideal para meriendas o utilizar en recetas. Este paquete contiene 6 manzanas, perfectas para una alimentación saludable.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7410062104975",
        "precio_base": "2.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395431/Manzana-Gala-Paquete-6-Unidades-1-12514.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Roja Paquete - 6 Unidades",
        "descripcion": "Paquete de manzanas rojas sin marca que ofrecen un sabor dulce y crujiente, perfectas para el consumo diario. Cada paquete suele contener aproximadamente seis manzanas frescas.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7410062104982",
        "precio_base": "2.09",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395432/Manzana-Roja-Paquete-6-Unidades-1-12515.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Hortifruti Verde Escolar - 2 a 4 Unidades Aproximadamente, precio Indicado Por Libra (454 g)",
        "descripcion": "Manzana Hortifruti Verde Escolar - Precio Indicado Por Libra (454 g) una alternativa frutal diseñada para brindar una opción de consumo fresco, agradable y de alta calidad dentro de tu rutina de alimentación diaria. Este artículo ha sido seleccionado bajo estrictos estándares para asegurar consistencia, un óptimo estado de maduración y un excelente desempeño en su consumo directo o preparaciones culinarias varias. La opción perfecta para quienes buscan optimizar su nutrición con un produ...",
        "codigo_barras": "2570700000009",
        "precio_base": "1.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395187/Manzana-Hortifruti-Verde-Escolar-Percio-Por-Lb-1-101.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Pink Lady Hortifruti - 2 a 4 Unidades Aproximadamente, precio Indicado Por Libra (454 g)",
        "descripcion": "Manzana Pink Lady Hortifruti - Precio Indicado Por Libra (454 g) una alternativa frutal diseñada para brindar una opción de consumo fresco, agradable y de alta calidad dentro de tu rutina de alimentación diaria. Este artículo ha sido seleccionado bajo estrictos estándares para asegurar consistencia, un óptimo estado de maduración y un excelente desempeño en su consumo directo o preparaciones culinarias varias. La opción perfecta para quienes buscan optimizar su nutrición con un producto ...",
        "codigo_barras": "2530720000007",
        "precio_base": "1.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/402120/Manzana-Pink-Lady-Hortifruti-Percio-Por-Lb-1-41.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Verde Paquete - 6 Unidades",
        "descripcion": "Manzana verde sin marca en paquete, ideal para picar y preparar en diversas recetas. Cada paquete contiene manzanas frescas que aportan nutrientes esenciales y vitaminas para una dieta equilibrada. Apta para consumo directo, ensaladas, o como ingrediente en postres y jugos.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7410062105002",
        "precio_base": "2.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395434/Manzana-Verde-Paquete-6-Unidades-1-12517.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana verde Hortifruti importada - 2 a 4 Unidades Aproximadamente, precio Indicado Por Libra (454 g)",
        "descripcion": "Sumérgete en la frescura y el sabor distintivo de las manzanas verdes Hortifruti importadas, disponibles en una presentación por libra que te brinda la oportunidad de disfrutar de su crujiente textura y sabor refrescante. Estas manzanas verdes, cuidadosamente seleccionadas por su calidad premium y procedencia importada, son reconocidas por ser una excelente fuente de fibra, vitaminas y antioxidantes que contribuyen a tu bienestar general. Las manzanas verdes Hortifruti importadas se dist...",
        "codigo_barras": "2540170000007",
        "precio_base": "1.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395407/Manzana-Verde-Hortifruti-Mediana-Percio-Por-Lb-1-49.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana gala mediana - 2 a 4 Unidades, precio Indicado Por Libra (454 g)",
        "descripcion": "Manzana Gala mediana sin marca, caracterizada por su color rojo vibrante, textura crujiente y jugosa. Ideal para refrigerios saludables o ingredientes en recetas variadas. Presentada en un empaque de 454 gramos aprox.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "2530090000003",
        "precio_base": "1.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/415513/Manzana-Hortifruti-Gala-Mediana-Percio-Por-Lb-1-39.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Gala Hortifruti Escolar - 2 a 4 Unidades Aproximadamente, precio Indicado Por Libra (454 g)",
        "descripcion": "Manzana Gala infantil presentada por libra. Esta variedad de manzana es especialmente seleccionada considerando tamaños y características apropiadas para el consumo infantil. Las manzanas Gala tienen un perfil de sabor dulce y agradable que resulta atractivo para los niños. Se venden por peso en libra, permitiendo seleccionar la cantidad exacta requerida. La textura crujiente y el contenido de jugo las hacen versátiles para múltiples usos. Pueden consumirse directamente como fruta de mer...",
        "codigo_barras": "2541330000004",
        "precio_base": "1.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/868810/manzana-gala-hortifruti-escolar-2-a-4-unidades-aproximadamente-precio-indicado-por-libra-454-g-2541330000004.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Roja Grande - 1 Ud",
        "descripcion": "La manzana roja unidad Hortifruti es una fruta de piel lisa y color rojo vibrante, seleccionada por su calidad, frescura y sabor característico. Su pulpa es firme, jugosa y crujiente, con un perfil dulce y un toque ligeramente ácido que la hace ideal para el consumo directo, ensaladas, postres o jugos naturales. Cultivada bajo prácticas que priorizan la conservación de sus propiedades, es fuente de fibra dietética, vitamina C y antioxidantes. Su aroma suave y textura agradable la convier...",
        "codigo_barras": "0000000075015",
        "precio_base": "0.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/859996/manzana-roja-gran-un-0000000075015.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Pink Lady 900 g Hf",
        "descripcion": "Manzana Pink Lady 900 g Hf",
        "codigo_barras": "7800125010587",
        "precio_base": "3.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960926/M-5_walmartsv_vAecyWfwEp_128174_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Hortifruti Roja - 2 a 4 Unidades Aproximadamente, precio Indicado Por Libra (454 g)",
        "descripcion": "Manzana Hortifruti Roja - Precio indicado por libra una alternativa frutal diseñada para brindar una opción de consumo fresco, agradable y de alta calidad dentro de tu rutina de alimentación diaria. Este artículo ha sido seleccionado bajo estrictos estándares para asegurar consistencia, un óptimo estado de maduración y un excelente desempeño en su consumo directo o preparaciones culinarias varias. La opción perfecta para quienes buscan optimizar su nutrición con un producto confiable y n...",
        "codigo_barras": "2540160000000",
        "precio_base": "1.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395406/Manzana-Roja-Hortifruti-Mediana-Percio-Por-Lb-1-48.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Fuji - 2 a 4 Unidades Aproximadamente, precio Indicado Por Libra (454 g)",
        "descripcion": "Manzana Fuji es una variedad roja de manzana caracterizada por sabor dulce notable y textura crujiente. Esta presentación se vende por kilogramo, permitiendo compra de cantidad flexible según necesidades de consumo familiar. Las manzanas Fuji en presentación kilogramo son apropiadas para familias numerosas, establecimientos de comidas o consumidores frecuentes de esta fruta. El peso de 1 kg, contiene aproximadamente 3 a 5 manzanas dependiendo del tamaño individual de cada fruto. La manza...",
        "codigo_barras": "2541310000000",
        "precio_base": "1.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/859911/manzana-fuji-precio-indicado-por-libra-454-g-2541310000000.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Manzana Mixta Paquete - 6 Unidades",
        "descripcion": "Manzana Mixta, SIN MARCA. Este paquete incluye una selección de manzanas frescas de distintas variedades para disfrutar una mezcla única de sabores y texturas. Ideal para snacks saludables o acompañar en diversas recetas - 1UdInformación del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7410062104999",
        "precio_base": "2.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/395433/Manzana-Mixta-Paquete-6-Unidades-1-12516.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Vinagre Hermel Manzana 700 Ml",
        "descripcion": "Vinagre Hermel Manzana 700 Ml",
        "codigo_barras": "0855533007114",
        "precio_base": "1.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/905375/M-5_walmartsv_hbwwXXBZOT_125279_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Vinagre Reggi De Manzana 3650 ml",
        "descripcion": "Vinagre Reggi De Manzana 3650 ml el complemento perfecto para darle el toque final, la cremosidad y el sabor ideal a todas tus comidas favoritas. Su consistencia balanceada está diseñada para integrarse con total facilidad a tus ensaladas, sándwiches, carnes o boquitas, aportando una experiencia deliciosa en cada porción. Una alternativa sumamente práctica y versátil en la mesa, ideal para quienes buscan realzar sus platillos diarios con la máxima calidad.",
        "codigo_barras": "7410033000503",
        "precio_base": "3.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/950799/M-5_walmartsv_FLIIgGckdP_75156_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Livit Manzana Lata 473 Ml",
        "descripcion": "Producto con venta restringida, solo para mayores de 18 años.Livit Jolly Green Apple Burst 473ml el complemento ideal para tus celebraciones, reuniones sociales o momentos de descanso. Esta opción destaca por su cuidadoso proceso de elaboración, ofreciendo un perfil balanceado que se adapta perfectamente a tus preferencias. Diseñado para disfrutar con responsabilidad, aporta el carácter y la frescura necesarios para elevar cualquier ocasión especial, convirtiéndose en una elección inteli...",
        "codigo_barras": "7422111063669",
        "precio_base": "1.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/837496/livit-manzana-lata-473-ml-7422111063669.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Gv Desinfect Manzana Verd 750ml",
        "descripcion": "Great Value desinfectante con aroma a manzana verde, 750 ml, proporciona una solución concentrada para la desinfección de superficies del hogar. Esta versión de menor capacidad es apropiada para hogares pequeños o personas que prefieren comprar en cantidades manejables. Está diseñado para eliminar bacterias, gérmenes y microorganismos presentes en pisos, baños, cocinas y muebles. El aroma refrescante a manzana verde deja un olor agradable en los espacios después de la limpieza. Se recomi...",
        "codigo_barras": "7441078236114",
        "precio_base": "1.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/862445/gv-desinfect-manzana-verd-750-ml-7441078236114.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Carfresh Lt Pinito Manzana Canela",
        "descripcion": "Aromatizante en forma de pinito de Car Freshner con fragancia de manzana y canela. Ideal para autos, proporciona un aroma fresco y duradero. Fácil de colgar en el retrovisor y mantener el ambiente del vehículo agradable. Presentación de 1 Ud. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0076171103383",
        "precio_base": "1.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/689608/44965_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Vitaldin Vinagre De Manzana 30gummies Unidad",
        "descripcion": "Vitaldin Vinagre De Manzana 30gummies Unidad desarrollado bajo altos estándares de calidad y bienestar para ofrecer un soporte vitamínico consistente, seguro y de excelente asimilación en el organismo. Su formato conveniente está pensado para incorporarse con total facilidad en tus hábitos cotidianos, asegurando esa consistencia, protección y nutrientes esenciales que buscas para cuidar tu salud a largo plazo. Una elección inteligente que combina rendimiento, confianza y cuidado diario.",
        "codigo_barras": "8435472601929",
        "precio_base": "11.05",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/829432/vitaldin-vinagre-de-manzana-30-gummies-unidad-8435472601929.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Gv Desinfect Manzana Ver 3780ml",
        "descripcion": "Great Value desinfectante con aroma a manzana verde, 3780 ml, proporciona una solución de limpieza potente para uso doméstico general. Está formulado para eliminar gérmenes, bacterias y microorganismos de superficies múltiples en pisos, muebles, baños y cocinas. El aroma refrescante a manzana verde proporciona una fragancia natural y agradable después de la limpieza. La gran capacidad garantiza uso prolongado para familias o espacios extensos. Se utiliza diluyendo en agua según las instr...",
        "codigo_barras": "7441078236138",
        "precio_base": "4.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/858123/gv-desinfect-manzana-ver-3780-ml-7441078236138.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Electrolit Suero Rehidrat Manzana 625ml",
        "descripcion": "Electrolit Suero Rehidrat Manzana 625ml desarrollado bajo altos estándares de la industria farmacéutica para ofrecer una respuesta consistente, segura y de gran efectividad en el cuidado de la salud. Su formato práctico está pensado para facilitar una asimilación óptima y oportuna, garantizando esa consistencia, alivio y el respaldo que buscas en un producto de su gama. Una elección inteligente dentro de tu botiquín que combina rendimiento, confianza y bienestar diario.",
        "codigo_barras": "7502268547196",
        "precio_base": "2.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/797655/electrolit-suero-rehidrat-manzana-625-ml-7502268547196.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Polanco Desinfectante Manzana 5 l",
        "descripcion": "Limpia, desinfecta y aromatiza por más tiempo. Fabricados con alcoholes naturales que brindan una eficaz limpieza y efecto antibacterial en todas las superficies. Contienen aditivos bactericidas que ayudan a reducir y eliminar bacterias Gram positivas y negativas, como también una amplia variedad de virus.",
        "codigo_barras": "7401164700073",
        "precio_base": "4.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/899051/M-5_walmartsv_BQjEmLqFGK_4160529_5.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Livit Manzana Vidrio 355 Ml",
        "descripcion": "Producto con venta restringida, solo para mayores de 18 años. Jolly Green Apple Burst de Living Life es un licor a base de brandy con sabor a manzana verde. Ideal para disfrutar solo o en cócteles. Viene en una presentación de 355 ml. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7422111061900",
        "precio_base": "1.55",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/820356/livit-manzana-vidrio-355-ml-7422111061900.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Zambos Platano Salsaverde 70 g",
        "descripcion": "Zambos Plátano Salsaverde 70 g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "0750894612994",
        "precio_base": "1.21",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/420246/Zambos-Platano-Salsaverde-70gr-1-47075.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Platano Nicole Tipicos 340 g",
        "descripcion": "Plátano Nicole Típicos 340 g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "7410010207482",
        "precio_base": "4.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/222795/Platano-Nicole-Tipicos-340-Gr-1-19982.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Platano Tipicos Nicole 198 g",
        "descripcion": "Plátano Típicos Nicole 198 g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "7410010207499",
        "precio_base": "2.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/432804/Platano-Tipicos-Nicole-198-Gr-1-3518.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Zambos Platano Originales 70 g",
        "descripcion": "Zambos Plátano Originales 70 g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "0750894612987",
        "precio_base": "1.21",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/420245/Zambos-Platano-Originales-70gr-1-47074.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Zambos Platano Picositas - 70 g",
        "descripcion": "¡Descubre el sabor explosivo de Zambos Plátano Picositas! Crujientes y deliciosas tajadas de plátano macho, sazonadas con un toque picante que te encantará. Perfectas para satisfacer tus antojos, estas papitas de 70 g son ideales para llevar contigo a donde sea. ¡Una explosión de sabor en cada bocado!",
        "codigo_barras": "0750894612970",
        "precio_base": "1.21",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/939570/M-5_walmartsv_ymBFpLpdms_83408_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Zambos plátano originales - 19 g",
        "descripcion": "Los Zambos plátano originales en su presentación de 19 g, son una opción práctica para disfrutar como snack en una porción individual durante distintos momentos del día. Su textura crujiente y sabor característico los convierten en una alternativa conveniente para meriendas, loncheras, pausas rápidas o consumo fuera de casa. Su formato pequeño facilita llevarlos en bolso, mochila o mantenerlos disponibles como una botana lista para consumir cuando se desee. Es una opción funcional para q...",
        "codigo_barras": "0750894612666",
        "precio_base": "0.34",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/448149/Sv-Zambos-Platano-Originales-19-Gr-1-49227.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Zambos Plátano Picositas - 19 g",
        "descripcion": "El snack Yummies Zambos de plátano picositas, en su presentación de 19 g, es una opción práctica para disfrutar como botana en diferentes momentos del día. Su tamaño individual facilita llevarlo en bolso, mochila o lonchera, permitiendo consumirlo con comodidad en pausas, trayectos o antojos entre comidas. Puede disfrutarse solo o acompañarse con bebidas frías según la preferencia. Su formato compacto ayuda a controlar porciones y simplifica el almacenamiento en casa o fuera de ella. Es ...",
        "codigo_barras": "0750894612659",
        "precio_base": "0.39",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/448148/Sv-Zambos-Platano-Picositas-19-Gr-1-49226.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Plátano Pro Tajada Verde - 180 g",
        "descripcion": "Plátano Pro Tajada Verde - 180 g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "7441005713725",
        "precio_base": "2.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/941713/platano-pro-tajada-verde-180-g-7441005713725.webp"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Snack Pro plátano maduro - 70.9 g",
        "descripcion": "El snack Pro plátano maduro en su presentación de 70.9 g es un producto alimenticio elaborado a partir de plátano maduro procesado y preparado para consumo como botana. Este tipo de snack puede consumirse directamente desde el envase como colación en diferentes momentos del día. Su formato permite ingerir el producto en porciones individuales según la preferencia del consumidor. Puede utilizarse como acompañamiento de bebidas o como parte de meriendas y colaciones. El empaque facilita su...",
        "codigo_barras": "7441005714838",
        "precio_base": "0.96",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/812119/snack-pro-platano-maduro-70-9-g-7441005714838.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Platano Hortifruti - 2 a 4 Unidades, precio Indicado Por Libra (454 g)",
        "descripcion": "Platano Hortifruti - Precio Indicado Por Libra (454 G)",
        "codigo_barras": "2573540000000",
        "precio_base": "0.55",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/868687/platano-hortifruti-2-a-4-unidades-precio-indicado-por-libra-454-g-2573540000000.webp"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Tostada de Platano Dulces Nicole bolsa - 56 g",
        "descripcion": "Las tostada de Platano Dulces Nicole en bolsa en su presentación de 56 g, son una opción práctica para disfrutar como snack en cualquier momento del día. Su formato facilita el consumo directo del empaque y permite llevarlas con comodidad en loncheras, bolsos o mochilas, siendo adecuadas para pausas rápidas o acompañamientos ligeros. Su tamaño resulta conveniente para porción individual y para quienes buscan un producto fácil de almacenar dentro de la despensa. Son una alternativa versát...",
        "codigo_barras": "7410010207147",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/453299/Dulces-Nicole-Tostadas-Platano-Bolsa-56-G-1-1333.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Mix  Diana Yuca Malanga y plátano - 165 g",
        "descripcion": "Delicioso mix de yuca, malanga y plátano, de la marca Diana. Este snack ofrece una mezcla crujiente y sabrosa perfecta para cualquier ocasión. Ideal para picar entre comidas o como acompañamiento. Presentación de 165g. Perfecto para cualquier momento del día, este mix combina raíces y frutas tropicales con un toque artesanal que evoca los sabores más auténticos de la región. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te re...",
        "codigo_barras": "0748757006363",
        "precio_base": "2.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/378408/Mix-Yuca-Malanga-Plantano-Diana-165-gr-1-40555.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Plátanitos maduros Pro con sal - 140 g",
        "descripcion": "Los Plátanitos maduros Pro con sal son un snack crujiente que combina el dulzor natural del plátano maduro con un toque de sal que resalta su sabor. Su textura crocante ofrece una experiencia agradable en cada bocado, siendo una opción ideal para consumir en cualquier momento del día. Su presentación de 140 g permite compartir o disfrutar en varias porciones, adaptándose a diferentes ocasiones como reuniones o meriendas. Son prácticos y listos para consumir, sin necesidad de preparación,...",
        "codigo_barras": "7441005714623",
        "precio_base": "1.82",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/621303/85389_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Snack Zambos Yummies plátanos con sabor a ceviche - 140 g",
        "descripcion": "Disfruta de las tajadas de plátano Yummies con sabor a ceviche. Estas crujientes rodajas son perfectas para tus antojos y meriendas, ofreciendo un delicioso y auténtico sabor a ceviche. Presentadas en un empaque de 140 gramos, son ideales para compartir o disfrutar solo. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0750894610822",
        "precio_base": "1.43",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/752639/69849_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Colado para bebé Parents Choice disney pera y banana - 113 g",
        "descripcion": "Colado Parents Choice es un alimento infantil de textura suave y homogénea presentado en envase de 90 gr con sabor a pera y plátano. Se trata de un producto diseñado para la alimentación complementaria de bebés y niños pequeños, combinando dos frutas en una sola porción. La pera y el plátano son frutas nutritivas que proporcionan vitaminas, minerales y potasio, elementos importantes para el desarrollo infantil. El formato en bolsa o tarro de 90 gr ofrece una porción apropiada para una co...",
        "codigo_barras": "7804655060050",
        "precio_base": "0.55",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/386625/Colado-Parents-Ch-Disney-Perabanana-113G-1-6763.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Platanitos Diana - 165 g",
        "descripcion": "Platanitos Diana - 165 g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "0748757002181",
        "precio_base": "1.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/954505/M-5_walmartsv_DLjmygWDNH_77405_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Platanitos Diana - 70 g",
        "descripcion": "Los platanitos Diana, en su presentación de 70 g, son una opción práctica para disfrutar como snack en distintos momentos del día. Su tamaño facilita llevarlos en bolso, mochila o lonchera, permitiendo consumirlos en pausas, trayectos o antojos entre comidas. Pueden disfrutarse solos o acompañarse con bebidas frías según la preferencia. El empaque compacto ayuda a controlar porciones y facilita el almacenamiento en casa o fuera de ella. Es una alternativa funcional para quienes buscan un...",
        "codigo_barras": "0748757002174",
        "precio_base": "0.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/576489/77404_01.jpg"
    },
    {
        "categoria": "Frutas y Verduras",
        "nombre": "Snack Yummies School Pack -264 g",
        "descripcion": "Yummies School Pack 218 g el producto ideal para saciar tus antojos, disfrutar durante tus meriendas o acompañar tus momentos de descanso y entretenimiento. Destaca por su empaque práctico y su textura ideal, aportando un toque de sabor que alegra cualquier pausa en tu rutina diaria. Una alternativa sumamente versátil, perfecta para llevar contigo a todas partes, disfrutar de un bocadillo rápido o compartir en tus reuniones sociales con amigos y familia.",
        "codigo_barras": "0750894662722",
        "precio_base": "3.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/939442/M-5_walmartsv_khJwEeeblp_102911_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón Campeón - 100 g",
        "descripcion": "Jabón Campeón - 100 g el accesorio ideal diseñado para tus mascotas o animales de compañía en su rutina. Confeccionado con materiales resistentes, seguros y de alta calidad, este artículo destaca por su formato funcional y duradero, adaptándose a la perfección ya sea que aplique a sus momentos de juego, descanso, higiene o alimentación. Una opción confiable para tus compañeros consentidos.",
        "codigo_barras": "7414400202262",
        "precio_base": "1.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/419908/Jabon-Campeon-100gr-1-39110.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabon Baby Nutrine Lavanda 90gr",
        "descripcion": "Jabon Baby Nutrine Lavanda 90gr",
        "codigo_barras": "7421002035006",
        "precio_base": "1.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/891280/M-5_walmartsv_KpqtfxsOMZ_123557_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón Gel Milder Plus Melocotónc- 4000cml",
        "descripcion": "Disfruta de una limpieza suave y delicada con el Jabón Gel Milder Plus de melocotón. Su fórmula rica en nutrientes y extractos naturales limpia eficazmente, eliminando impurezas sin resecar la piel. Deja una sensación de frescura, suavidad y bienestar, mientras su delicado aroma a melocotón envuelve tus sentidos, convirtiendo el lavado diario en un momento agradable. Ideal para todo tipo de piel, protege la barrera natural cutánea y ayuda a mantener la hidratación. Perfecto para el uso d...",
        "codigo_barras": "7411001252283",
        "precio_base": "8.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/388834/Jab-n-gel-Milder-Plus-Melocoton-4000ml-1-3678.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón íntimo Bidex manzanilla -250 ml",
        "descripcion": "Jabón íntimo bidex con una fórmula suave y refrescante de manzanilla. Ideal para el cuidado y la limpieza diaria de la zona íntima femenina. Presentación de 250 ml.",
        "codigo_barras": "7411002105540",
        "precio_base": "5.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/708218/43840_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabon Xtra Paraiso Suavizante 1500 Gr",
        "descripcion": "El Jabón Xtra Fusion Paraíso Suave 3 Uds - 1500 g combina limpieza efectiva con un aroma tropical irresistible que transforma tu rutina diaria en una experiencia sensorial. Su fórmula cuida la piel dejándola suave, hidratada y fresca. Ideal para toda la familia, ofrece rendimiento y calidad en cada uso. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener ...",
        "codigo_barras": "7401001691045",
        "precio_base": "3.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/758199/108774_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabon Xtra Proteccion Suavizante 1500 Gr",
        "descripcion": "Jabon Xtra Fusion Protec Suav 1500g mantén tus prendas impecables y frescas con nuestra línea de productos para el lavado de ropa. Formulados con tecnología avanzada que elimina manchas difíciles y remueve la suciedad profunda, protegen los tejidos y mantienen los colores vivos lavado tras lavado. El aliado perfecto para garantizar una limpieza eficiente, suavidad al tacto y un aroma limpio y duradero en toda tu vestimenta.",
        "codigo_barras": "7401001691748",
        "precio_base": "3.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/813272/jabon-xtra-proteccion-suavizante-1500-gr-7401001691748.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Lixibon Ferson 75 g Jabon Medicado",
        "descripcion": "Lixibon Ferson 75 g Jabón Medicado desarrollado bajo altos estándares de la industria farmacéutica para ofrecer una respuesta consistente, segura y de gran efectividad en el cuidado de la salud. Su formato práctico está pensado para facilitar una asimilación óptima y oportuna, garantizando esa consistencia, alivio y el respaldo que buscas en un producto de su gama. Una elección inteligente dentro de tu botiquín que combina rendimiento, confianza y bienestar diario.",
        "codigo_barras": "7410061200272",
        "precio_base": "6.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/374776/Lixibon-Ferson-75G-Jabon-Medicado-1-31290.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabon Zote Blanco - 400 g",
        "descripcion": "El jabón Zote blanco en su presentación de 400 g, es una opción práctica para el lavado de ropa a mano, pretratamiento de manchas y limpieza de textiles compatibles. Su formato en barra permite aplicar directamente sobre zonas específicas y controlar la cantidad utilizada en cada lavado. Puede emplearse en prendas de uso diario, paños, sábanas, toallas o ropa que requiere cuidado puntual, siguiendo las recomendaciones del empaque. Es una alternativa conveniente para quienes buscan un jab...",
        "codigo_barras": "7501026005374",
        "precio_base": "1.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/864355/jabon-zote-blanco-400-gr-7501026005374.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabon Xtra Aloe Vera 1500 g",
        "descripcion": "Jabón de lavandería en barra de la marca XTRA, con aroma a Aloe Vera. Ideal para limpieza de ropa, dejando un agradable aroma natural. Presentación de 1500 g. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401001680865",
        "precio_base": "3.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/418299/Jabon-Xtra-Aloe-Vera-1620Gr-1-24010.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón Bola Zixx, Nenitos -350 g",
        "descripcion": "Jabón bola Zixx especialmente formulado para la ropa de los más pequeños. Suaviza y limpia eficazmente sin irritar la piel delicada de los niños. Ideal para lavar a mano - 350gr. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0750894642823",
        "precio_base": "1.26",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/365889/Jabon-Bola-Zixx-Nenitos-350-Grs-1-28622.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabón Olimpo Liquido - 460 ml",
        "descripcion": "Disfruta de una limpieza fresca y suave con el jabón Olimpo aqua de 460 ml. Su fórmula líquida elimina impurezas y suciedad, dejando la piel limpia, hidratada y con una sensación agradable al tacto. Enriquecido con agentes humectantes, protege la barrera natural de la piel, evitando la resequedad incluso con lavados frecuentes. Su aroma fresco y delicado aporta una sensación de bienestar y frescura que perdura durante todo el día. Ideal para el uso diario en manos y cuerpo, combina higie...",
        "codigo_barras": "7406171026895",
        "precio_base": "1.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/388558/Jab-n-L-quido-Olimpo-1-1221.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Jabon Liquido Calm Baby Jergens 591ml",
        "descripcion": "Jabon Liquido Calm Baby Jergens 591ml",
        "codigo_barras": "0019100300514",
        "precio_base": "7.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/954905/M-5_walmartsv_ujJWzSRhWL_118814_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Suave Mustela 200ml",
        "descripcion": "Shampoo Suave Mustela 200ml desarrollado bajo altos estándares para ofrecer una solución efectiva, confiable y de gran rendimiento en tu cuidado personal. Su presentación está pensada para adaptarse con total facilidad a tus necesidades, proporcionando lo necesario para mantener una apariencia saludable y radiante. Una elección inteligente para quienes buscan optimizar su bienestar con un producto de uso constante.",
        "codigo_barras": "3504105036126",
        "precio_base": "11.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/834591/shampoo-suave-mustela-200-ml-3504105036126.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Suave Mustela 500ml",
        "descripcion": "Shampoo Suave Mustela 500ml desarrollado bajo altos estándares para ofrecer una solución efectiva, confiable y de gran rendimiento en tu cuidado personal. Su presentación está pensada para adaptarse con total facilidad a tus necesidades, proporcionando lo necesario para mantener una apariencia saludable y radiante. Una elección inteligente para quienes buscan optimizar su bienestar con un producto de uso constante.",
        "codigo_barras": "3504105036133",
        "precio_base": "17.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/853510/shampoo-suave-mustela-500-ml-3504105036133.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Baby Nutrine Manzanilla 300ml",
        "descripcion": "El Shampoo Baby Nutrine Manzanilla está diseñado para limpiar suavemente mientras aporta brillo natural al cabello delicado. Su fórmula con manzanilla ayuda a mantener el cuero cabelludo limpio y el cabello ligero tras cada lavado. Ideal para uso frecuente, contribuye a conservar la suavidad y manejabilidad diaria. Su presentación de 300 ml es práctica para el hogar y facilita una rutina constante. Haz tu compra en línea y recibe tu Shampoo Baby Nutrine con entrega segura.",
        "codigo_barras": "7421002042196",
        "precio_base": "3.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/893398/M-5_walmartsv_MyyYlgqycZ_41282_5.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Baby Nutrine Lavanda 300ml",
        "descripcion": "El Shampoo Baby Nutrine Lavanda en presentación de 300 ml ofrece mayor duración para el cuidado constante del cabello infantil. Su fórmula suave limpia sin resecar y deja un aroma delicado que acompaña la rutina diaria. Ideal para uso frecuente, facilita el enjuague y mantiene el cabello suave y manejable. Perfecto para complementar la higiene diaria con una sensación agradable tras cada baño. Haz tu compra en línea y recibe tu Shampoo Baby Nutrine con envío seguro hasta tu hogar.",
        "codigo_barras": "7421002042172",
        "precio_base": "3.15",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/933516/shampoo-baby-nutrine-lavanda-300-ml-7421002042172.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Gelatti Barbie -300 ml",
        "descripcion": "Shampoo Gelatti Barbie -300 ml línea avanzada de cuidado capilar diseñada para transformar, proteger y embellecer todo tipo de cabello desde la raíz hasta las puntas. Sus fórmulas de alta eficacia limpian con suavidad, nutren profundamente y reparan la fibra capilar, devolviendo el brillo natural, la suavidad y la vitalidad perdida. Ideal tanto para el mantenimiento diario como para proteger el color y mantener la estructura de cabellos procesados, garantizando un aspecto radiante, manej...",
        "codigo_barras": "7804915528887",
        "precio_base": "6.05",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/735783/101958_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Ogx Coconut Milk 385ml",
        "descripcion": "El Shampoo Organix de Leche y Coco 385 ml ofrece limpieza profunda y nutrición intensiva para el cabello, especialmente para cabellos secos o dañados. Su fórmula combina la suavidad de la leche con el poder hidratante del coco, dejando el cabello sedoso, brillante y manejable. Protege la fibra capilar del desgaste diario y ayuda a reducir el frizz, restaurando la vitalidad natural de cada hebra. Ideal para todo tipo de cabello, incluso los tratados químicamente, este shampoo limpia sin r...",
        "codigo_barras": "0022796910059",
        "precio_base": "10.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/876364/shampoo-ogx-coconut-milk-385-ml-0022796910059.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Bioland Inf Argan 350ml",
        "descripcion": "Shampoo Bioland Inf Argan 350ml",
        "codigo_barras": "7451110881769",
        "precio_base": "8.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/930194/M-5_walmartsv_dJbPRlTEXP_126020_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Bioland Inf Aloe 350ml",
        "descripcion": "Shampoo Bioland Inf Aloe 350ml",
        "codigo_barras": "7451110881783",
        "precio_base": "8.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/929362/shampoo-bioland-inf-aloe-350-ml-7451110881783.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Schwarzkoff Matizante 200 ml",
        "descripcion": "El Shampoo Matizante Schwarzkopf en presentación de 200 ml es un producto especializado en el cuidado del cabello teñido, especialmente diseñado para mantener y realzar los tonos rubios, grises y platinos. Contiene pigmentos violetas que neutralizan los tonos amarillos y anaranjados no deseados, dejando el cabello con un tono frío y radiante. Su fórmula es lo suficientemente suave para uso frecuente, evitando el daño y la resequedad del cabello. Este shampoo es ideal para personas con ca...",
        "codigo_barras": "7702045339833",
        "precio_base": "4.7",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/739389/53380_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Calypso Anticaspa 830 ml",
        "descripcion": "Mantén tu cabello limpio y libre de caspa con el shampoo anticaspa Calypso 2 en 1. Su fórmula combinada limpia profundamente, eliminando impurezas y controlando la aparición de escamas, mientras acondiciona el cabello dejándolo suave y manejable. Ideal para uso diario, ayuda a equilibrar el cuero cabelludo, previniendo irritaciones y dejando una sensación de frescura duradera. Perfecto para todo tipo de cabello, ofrece comodidad y eficacia en un solo paso, combinando limpieza y cuidado e...",
        "codigo_barras": "7406171015318",
        "precio_base": "2.69",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/637445/86773_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Sedal Restauracion Instan 845ml",
        "descripcion": "Shampoo Sedal Restauraci Instan 845 ml línea avanzada de cuidado capilar diseñada para transformar, proteger y embellecer todo tipo de cabello desde la raíz hasta las puntas. Sus fórmulas de alta eficacia limpian con suavidad, nutren profundamente y reparan la fibra capilar, devolviendo el brillo natural, la suavidad y la vitalidad perdida. Ideal tanto para el mantenimiento diario como para proteger el color y mantener la estructura de cabellos procesados, garantizando un aspecto radiant...",
        "codigo_barras": "7506306209558",
        "precio_base": "6.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/888943/M-5_walmartsv_jekHFrsIDs_119018_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Bellepon Control Caida 440ml",
        "descripcion": "Shampoo Bellepon Control Caída 440 ml línea avanzada de cuidado capilar diseñada para transformar, proteger y embellecer todo tipo de cabello desde la raíz hasta las puntas. Sus fórmulas de alta eficacia limpian con suavidad, nutren profundamente y reparan la fibra capilar, devolviendo el brillo natural, la suavidad y la vitalidad perdida. Ideal tanto para el mantenimiento diario como para proteger el color y mantener la estructura de cabellos procesados, garantizando un aspecto radiante...",
        "codigo_barras": "7411002199822",
        "precio_base": "4.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/873282/shampoo-bellepon-control-caida-440-ml-7411002199822.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Fructis Post Quimica -650ml",
        "descripcion": "Shampoo Fructis Post Química 650 ml producto capilar de calidad, ideal para el cuidado, hidratación y estilizado diario de tu cabello. Su fórmula especializada nutre intensamente, repara las zonas dañadas y sella la cutícula para retener la humedad y el color por más tiempo. Perfecto para mantener un cabello fuerte, visiblemente más sano y protegido frente a procesos de alisado o coloración, brindando un resultado de salón con la practicidad que necesitas en tu rutina del hogar.",
        "codigo_barras": "7509552910100",
        "precio_base": "8.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/859832/shampoo-fructis-borrador-de-dano-650-ml-7509552910100.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo Bob Esponja 3en1 300ml",
        "descripcion": "Shampoo Bob Esponja 3en1 300 ml línea avanzada de cuidado capilar diseñada para transformar, proteger y embellecer todo tipo de cabello desde la raíz hasta las puntas. Sus fórmulas de alta eficacia limpian con suavidad, nutren profundamente y reparan la fibra capilar, devolviendo el brillo natural, la suavidad y la vitalidad perdida. Ideal tanto para el mantenimiento diario como para proteger el color y mantener la estructura de cabellos procesados, garantizando un aspecto radiante, mane...",
        "codigo_barras": "7804915529167",
        "precio_base": "6.05",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/735756/101962_01.jpg"
    },
    {
        "categoria": "Cuidado Personal",
        "nombre": "Shampoo 3En1 Dragon Ball 300Ml",
        "descripcion": "El shampoo 3 en 1 Dragon Ball Z combina limpieza, hidratación y cuidado del cabello en un solo producto, ideal para niños y adolescentes fanáticos de la saga. Su fórmula suave limpia el cabello y cuero cabelludo sin resecar, mientras deja un aroma divertido y fresco. Además, actúa como acondicionador, facilitando el desenredado y manteniendo el cabello suave y manejable. Su presentación de 300 ml es práctica para uso diario y viajes, ofreciendo un producto completo que combina higiene, c...",
        "codigo_barras": "7757462000521",
        "precio_base": "6.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/653903/98715_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Ultraklin Fuerza Intensa 1.8Kg",
        "descripcion": "Detergente en polvo Ultraklin. Con fórmula de fuerza intensa, ideal para eliminar manchas difíciles y dar frescura a la ropa. Excelente rendimiento en lavados. En su presentación de 2000 g Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7406171011723",
        "precio_base": "2.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/464208/54710_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente En Polvo Suli Natural 9000gr",
        "descripcion": "Detergente en polvo Suli Natural de 9000 g es un producto de limpieza para ropa en gran volumen, especialmente útil para establecimientos comerciales, lavanderías o familias numerosas que realizan lavados en cantidad. Formulado con ingredientes naturales que permiten remover eficazmente la suciedad acumulada en las prendas de vestir. Su presentación en polvo facilita el almacenamiento y tiene una larga vida útil cuando se guarda en lugar seco. La fórmula se disuelve en agua fría o tibia,...",
        "codigo_barras": "7441078262397",
        "precio_base": "8.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/811830/detergente-en-polvo-suli-natural-9000-gr-7441078262397.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Mas Bebé líquido - 4650 ml",
        "descripcion": "Detergente líquido para bebé de MAS bebé, especialmente formulado para cuidar la ropa delicada de los pequeños. Su fórmula suave ayuda a prevenir irritaciones en la piel sensible de los bebés, dejando las prendas frescas y limpias. Presentación de 4650 ml, ideal para uso prolongado. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualiz...",
        "codigo_barras": "7501199416120",
        "precio_base": "13.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/570402/90187_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Liquido Woolite Tld 1800 ml",
        "descripcion": "Detergente líquido Woolite Todo Los Dias, ideal para una limpieza efectiva y delicada de todo tipo de ropa, protegiendo las fibras y colores, su exclusiva formula triple protección protege las fibras de tu ropa previniendo la formación de motas, el estiramiento y encogimiento de tus prendas. Presentación de 1800 ml Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante p...",
        "codigo_barras": "7702626218885",
        "precio_base": "9.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/766942/63393_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Liquido Mas Color - 7 L",
        "descripcion": "Detergente líquido Mas Color, ideal para mantener la ropa de colores vibrantes y eliminar manchas difíciles. Su fórmula avanzada protege las fibras de los tejidos y proporciona una fragancia duradera en cada lavado. Presentación en envase de 7lt.",
        "codigo_barras": "7406425000473",
        "precio_base": "15.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/857396/detergente-mas-color-7-lt-7406425000473.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente En Polvo Suli Natural 2500gr",
        "descripcion": "Detergente en polvo Suli Natural de 2500 g, formulado para lavar ropa de manera efectiva con ingredientes naturales. Está diseñado para remover la suciedad y las manchas de las prendas de vestir mediante su fórmula concentrada en polvo que se disuelve en agua. Permite que los componentes actúen sobre las fibras de la tela eliminando contaminantes. Es adecuado para usar en diferentes tipos de lavadoras, tanto automáticas como semiautomáticas, adaptándose a diversas temperaturas de agua. P...",
        "codigo_barras": "7441078262373",
        "precio_base": "2.7",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/903376/M-5_walmartsv_NadfQrMWXI_109966_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Ultraklin Fuerza Solar -1.8 kg",
        "descripcion": "El detergente en polvo Ultraklin Fuerza Vital de 1.8 kg es ideal para lavar la ropa, proporcionando una limpieza profunda y cuidando las telas. Especialmente formulado para eliminar manchas difíciles y ofrecer frescura duradera. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7406171010580",
        "precio_base": "2.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/711140/54706_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Líquido MAS Color - 830 ml",
        "descripcion": "¿Te preocupa el cuidado del color y la integridad de tu ropa a la hora de lavar? MAS el detergente con fórmula única que brinda colores vivos hasta 5X más. Manteniendo las fibras de tu ropa como nuevas.",
        "codigo_barras": "7501199413280",
        "precio_base": "2.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/642620/46511_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente En Polvo Suli Natural 500gr",
        "descripcion": "Detergente en polvo Suli Natural de 500 g, diseñado para lavar ropa con efectividad utilizando ingredientes naturales que actúan sobre la suciedad y manchas presentes en las prendas. El polvo se disuelve fácilmente en agua, permitiendo que la fórmula se distribuya uniformemente durante el ciclo de lavado. Esta presentación de menor tamaño es práctica para aquellos que desean probar el producto o que tienen espacios limitados de almacenamiento en el hogar. Funciona correctamente en lavado...",
        "codigo_barras": "7441078262359",
        "precio_base": "0.57",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/826273/detergente-en-polvo-suli-natural-500-gr-7441078262359.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Ultraklin, Fuerza Natural -9000 g",
        "descripcion": "El detergente en polvo Ultraklin multiusos fuerza natural de 9 kg es una opción rendidora para hogares que requieren un producto de limpieza para lavado frecuente y en mayores cantidades. Su formato resulta conveniente para atender varias cargas de ropa y mantener abastecida la zona de lavandería por más tiempo. Puede utilizarse dentro de la rutina diaria para apoyar el lavado de prendas y textiles del hogar, ofreciendo practicidad en cada uso. Es ideal para familias o espacios donde se ...",
        "codigo_barras": "7401006100115",
        "precio_base": "9.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/464674/45846_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Mas Color liquido - 1.83 L",
        "descripcion": "Detergente líquido Mas Color para bebé, de 1.83 L. Formula delicada para la piel sensible de los bebés, removiendo eficientemente las manchas más difíciles. Ideal para prendas de bebé y ropa de cama, ofreciendo una limpieza profunda y un aroma suave. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7501199416137",
        "precio_base": "5.55",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/946888/M-5_walmartsv_TJzjglRGZN_50050_5.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Polanco Manzana - 1800 ml",
        "descripcion": "Detergente Líquido Polanco 4 en 1 , Limpieza Profunda, Antibacterial*, Aromatiza, Protege colores. Detergente líquido. Fragancia Manzana. PH nivelado.Diseñado para la limpieza de prendas con fuertes contenidos de mugre y grasa, consiguiendo más cuidado y protección de los tejidos y sus colores, gracias a sus componentes especiales hacen que el producto sea de baja agresividad.Desarrollado para minimizar el daño de la piel. Recomendado para el lavado de ropa en general ya sea blanca o de ...",
        "codigo_barras": "7401164701407",
        "precio_base": "24.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/594366/73566_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente FAB advance - 1.65 kg",
        "descripcion": "El detergente en polvo Fab advance de 1.65 kg es una opción pensada para la limpieza de ropa en la rutina diaria del hogar. Su formato en polvo permite dosificar según la cantidad de prendas y el nivel de suciedad, facilitando su uso tanto en lavados frecuentes como en cargas de mayor volumen. Su presentación brinda un rendimiento conveniente para varias jornadas de lavado, lo que lo hace práctico para mantener siempre disponible en el área de limpieza. Es una alternativa funcional para ...",
        "codigo_barras": "7401001689141",
        "precio_base": "3.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/546518/93078_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Swift Liquido Doypack - 1.9 L",
        "descripcion": "El Detergente Líquido Swift Original está formulado para ofrecer una limpieza efectiva y eficiente en tus prendas. Su fórmula avanzada combate la suciedad y las manchas difíciles, manteniendo la ropa limpia y fresca. Con su presentación de 1.9 litros, es ideal para hogares que buscan un detergente confiable y de gran rendimiento. El Detergente Líquido Swift Original es una opción excelente para quienes buscan un detergente eficaz que limpie profundamente y deje la ropa con un aroma fresc...",
        "codigo_barras": "7401001681206",
        "precio_base": "3.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/860916/detergente-swift-liquido-doypack-1900-ml-7401001681206.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente líquido Swift antibacterial - 4.5 L",
        "descripcion": "Detergente líquido Swift Original en presentación de 4500 ml, ideal para eliminar manchas difíciles y dejar la ropa impecable, con un aroma agradable y duradero. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7406171022279",
        "precio_base": "8.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/841216/detergente-liquido-swift-antibacterial-4-5-l-7406171022279.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente líquido Persil Universal - 6.64 L",
        "descripcion": "El detergente líquido Persil Universal en su presentación de 6.64 L ofrece un formato de gran capacidad pensado para hogares donde el lavado de ropa se realiza con frecuencia. Su consistencia líquida facilita dosificar el producto según el tamaño de la carga y las indicaciones del envase, permitiendo incorporarlo a diferentes jornadas de lavandería. Persil presenta una alternativa conveniente para prendas y textiles compatibles de uso cotidiano, con una cantidad amplia que ayuda a reduci...",
        "codigo_barras": "7406425000374",
        "precio_base": "21.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/905073/M-5_walmartsv_UIZzACsqED_4186159_5.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Liq Swift Bicarbna Oxi 1 9l",
        "descripcion": "Detergente Liq Swift Bicarb 1900ml el aliado indispensable para tu rutina de aseo, diseñado para ofrecer una limpieza profunda, efectiva y de alto rendimiento. Su fórmula avanzada actúa con total rapidez para remover la suciedad, la grasa o las manchas difíciles, devolviendo la frescura y la pureza original a cada superficie o tejido. Una alternativa sumamente versátil y confiable que garantiza un ambiente impecable y agradable para toda tu familia.",
        "codigo_barras": "7401001692820",
        "precio_base": "3.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/867174/detergente-liq-swift-bicarbna-oxi-1-9-lt-7401001692820.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Swift Liquido Original - 17 L",
        "descripcion": "Detergente Líquido Swift Original de 18L: Poder de Limpieza Duradero El Detergente Líquido Swift Original de 18L ofrece un poder de limpieza duradero para una amplia variedad de cargas de ropa. Elimina las manchas y deja tus prendas impecables.",
        "codigo_barras": "7401001678060",
        "precio_base": "28.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/834572/detergente-swift-liquido-original-17-l-7401001678060.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente en Polvo Ultraklin Fuerza Extrema -4500g",
        "descripcion": "Detergente en polvo Ultraklin Fuerza Extrema, ideal para eliminar manchas difíciles y mantener la ropa limpia y fresca. Fórmula concentrada que rinde más y ofrece una limpieza profunda en cada lavado. Presentación de 4500 gramos para más usos.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7406171026840",
        "precio_base": "6.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/809701/detergente-en-polvo-ultraklin-fuerza-extrema-4500-g-7406171026840.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Persil Liquido Universal - 830 ml",
        "descripcion": "El detergente líquido Persil Universal en presentación de 830 ml es una opción versátil y eficaz para el lavado de ropa de todo tipo de tejidos y colores. Su fórmula equilibrada elimina manchas difíciles y suciedad profunda, cuidando las fibras y manteniendo la calidad de las prendas. Ideal para uso en lavadoras automáticas o lavado manual, proporciona una limpieza eficiente y suave, preservando la frescura y suavidad de la ropa. Deja un aroma agradable y duradero, asegurando resultados ...",
        "codigo_barras": "7501199413433",
        "precio_base": "3.65",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/853362/detergente-persil-liquido-universal-830-ml-7501199413433.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Polvo Ariel Revitacolor - 4 kg",
        "descripcion": "Descubre el Poder Bio degradable* del detergente Ariel! El jabón en polvo para ropa Ariel Revitacolor te ofrece una limpieza profunda a la primera. Su fórmula, ahora con bio espuma inteligente*, remueve manchas, combate los malos olores y cuida las fibras de tu ropa, Ariel es el detergente en polvo ideal para tu ropa blanca y de color. Ahora con polvo ultra fino de rápida disolución es el aliado ideal para evitar manchas de jabón en la ropa, ¿qué esperas para probarlo? Disfruta de tus pr...",
        "codigo_barras": "7500435216111",
        "precio_base": "13.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/934736/detergente-polvo-ariel-revitacolor-4-kg-7500435216111.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente 123 líquido limón - 8.3 L",
        "descripcion": "Detergente 123 Líquido limón Multiusos -8.3 L es la solución perfecta para la limpieza profunda y efectiva de tu hogar. Su fórmula concentrada con extracto natural de limón elimina grasa, suciedad y manchas difíciles en distintas superficies, dejando un aroma fresco y duradero que refresca cualquier ambiente. Ideal para pisos, baños, cocinas y más, este detergente multiusos garantiza higiene y brillo con un solo producto. Su presentación en gran volumen ofrece un excelente rendimiento pa...",
        "codigo_barras": "7406425000206",
        "precio_base": "19.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/948136/M-5_walmartsv_QYsgdrhXHZ_93436_5.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Detergente Líquido Ariel Revitacolor - 1 L",
        "descripcion": "¿Buscas un detergente líquido concentrado que te de una Limpieza a la Primera en Colores? Prueba el detergente Ariel Revitacolor, su increíble poder 3 en 1 remueve manchas*, cuida tu ropa' y perfuma, dándote una limpieza a la primera en colores y convirtiéndolo en tu aliado ideal para esas manchas del día a día como las de grasa y percudido. Gracias a la fórmula concentrada del detergente líquido Ariel, menos de una tapita de jabón líquido ropa es suficiente para limpiar profundamente la...",
        "codigo_barras": "7500435234221",
        "precio_base": "9.7",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/935568/detergente-liquido-ariel-revitacolor-1-l-7500435234221.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Regular 450 ml",
        "descripcion": "Cloro Regular 450 ml Este producto de limpieza es una opción de excelente calidad, ideal para quienes buscan mantener un hogar impecable, fresco y completamente libre de impurezas de manera práctica y sencilla. Su fórmula especializada ha sido desarrollada con componentes de alto rendimiento que actúan eficazmente contra la suciedad acumulada, garantizando un cuidado óptimo de tus espacios, superficies o tejidos sin dañarlos.",
        "codigo_barras": "0785381018249",
        "precio_base": "0.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/921191/M-5_walmartsv_OTBmWSzGAG_89330_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Gv Limpiador Todo Proposito Cloro 946Ml",
        "descripcion": "Limpiador multiusos Great Value de 946 ml con cloro para limpiar y desinfectar superficies del hogar. Este producto de todo propósito contiene cloro, componente que elimina bacterias, virus y microorganismos en diferentes áreas. Es apropiado para cocinas, baños, pisos y superficies que requieran desinfección profunda. El cloro actúa como agente blanqueador y desinfectante simultáneamente. Para usar, diluya en agua fría en proporción recomendada según el nivel de suciedad o contaminación....",
        "codigo_barras": "0681131596633",
        "precio_base": "3.68",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/807056/gv-limpiador-todo-proposito-cloro-946-ml-0681131596633.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Magia Blanca - 1 L",
        "descripcion": "El cloro Magia Blanca es ideal para desinfección y limpieza profunda del hogar. Su presentación de 1000 ml es perfecta para múltiples superficies, eliminando bacterias y hongos eficientemente. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401002002093",
        "precio_base": "1.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/809205/cloro-magia-blanca-1-l-7401002002093.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Acticolor, Fuerza Natural -1890 ml",
        "descripcion": "Cloro Acticolor, Fuerza Natural -1890ml: Desinfección Natural Experimenta una desinfección natural con el Cloro Acticolor de Fuerza Natural en envase de 1890ml. Su fórmula potente elimina gérmenes de forma efectiva, priorizando ingredientes de origen natural.",
        "codigo_barras": "7406171011754",
        "precio_base": "1.47",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/376031/Cloro-Acticlor-Original-1890ml-1-25808.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Blanco Sol - 3785 ml",
        "descripcion": "Cloro Blanco Sol 3785 ml es un producto especializado para la higiene y el cuidado del hogar, desarrollado con altos estándares de calidad que aseguran una acción eficiente y un rendimiento excepcional. Su uso contribuye a mantener los espacios impecables, organizados y con una agradable sensación de frescura y bienestar. Diseñado para adaptarse a las necesidades de mantenimiento de la casa, brinda una protección confiable, resultados uniformes y una practicidad única para el cuidado del...",
        "codigo_barras": "7415000521821",
        "precio_base": "2.59",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/903397/M-5_walmartsv_GmDvpYhkzR_43953_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Great Value Bt 9460 Ml",
        "descripcion": "El cloro Great Value de 9460ml es ideal para la limpieza y desinfección del hogar. Su formulación asegura la eliminación de gérmenes y bacterias en múltiples superficies, brindando una limpieza profunda y eficaz. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7441078235001",
        "precio_base": "6.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/883005/cloro-great-value-bt-9460-ml-7441078235001.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Acticolor original - 3.7 L",
        "descripcion": "Cloro Acticolor original - 3.7 L: Poder Desinfectante para tu Hogar Descubre el poder desinfectante del Cloro Acticolor en su presentación original de 3785ml. Mantén tu hogar libre de gérmenes y bacterias, asegurando un ambiente limpio y saludable.",
        "codigo_barras": "7401001666036",
        "precio_base": "2.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/808683/cloro-acticolor-original-3-7-l-7401001666036.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Acticlor Original - 5 L",
        "descripcion": "El Cloro Acticlor es un producto líquido que se utiliza para el tratamiento de agua potable, destinado a la eliminación de organismos patógenos, tales como bacterias, virus y hongos. Contiene cloro activo en concentraciones que permiten su uso en el tratamiento de agua potable",
        "codigo_barras": "7406171024549",
        "precio_base": "3.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/870970/cloro-acticolor-original-5000-ml-7406171024549.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Acticlor Gel - 500 ml",
        "descripcion": "El cloro en gel Acticlor es un potente limpiador ideal para desinfectar y eliminar manchas en superficies del hogar. Su fórmula en gel permite una mayor adherencia y acción prolongada, ideal para baños y cocinas. Perfecto para mantener la higiene y limpieza en tu hogar. - 500ml Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401001678374",
        "precio_base": "2.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/898905/M-5_walmartsv_uQGyvGnejZ_51618_5.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Gel Magia B 3785 ml",
        "descripcion": "Mantén tu piscina cristalina y lista para disfrutar con el Cloro Magia Blanca en Gel, en una presentación conveniente de 3785 ml. Este poderoso desinfectante garantiza una desinfección eficaz, eliminando bacterias y manteniendo el agua de tu piscina en condiciones óptimas. El Cloro Magia Blanca en Gel es fácil de aplicar, ofreciendo una distribución uniforme para asegurar una limpieza efectiva. Su presentación en gel facilita su uso y permite una aplicación precisa para lograr un equilib...",
        "codigo_barras": "0785381025223",
        "precio_base": "4.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/742561/83140_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Magia Blanca Populino - 200 ml",
        "descripcion": "Cloro Magia Blanca Populino es ideal para la limpieza profunda del hogar. Su fórmula avanzada elimina gérmenes y bacterias, dejando las superficies desinfectadas y libres de olores. Perfecto para uso en baños, cocinas y áreas comunes - 200 ml.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7506195163702",
        "precio_base": "0.24",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/394516/Cloro-Magia-Blanca-Populino-200Ml-1-15406.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Magia Blanca Caneca - 10 L",
        "descripcion": "Cloro Magia Blanca en presentación de caneca de 10 litros. Perfecto para la limpieza del hogar, desinfección y eliminación de manchas. Idóneo para uso prolongado gracias a su cantidad. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "0785381009971",
        "precio_base": "7.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/742496/45384_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Magia Blanca Regular - 1.895 L",
        "descripcion": "El cloro Magia Blanca de 1895 ml es una opción práctica para la limpieza y desinfección de superficies en el hogar, ayudando a mantener espacios más higiénicos en la rutina diaria. Resulta útil en baños, pisos, cocinas y áreas de uso frecuente donde se requiere una limpieza más profunda. Su presentación ofrece una cantidad conveniente para distintas tareas domésticas, facilitando su uso en labores continuas de mantenimiento. Es una alternativa funcional para quienes buscan reforzar la li...",
        "codigo_barras": "0785381010519",
        "precio_base": "1.9",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/742505/81205_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Magia Blanca, Limón - 3785 ml",
        "descripcion": "El cloro Magia Blanca con aroma a campos de limón es ideal para limpiar y desinfectar cualquier superficie del hogar, proporcionando una fragancia fresca. Su presentación en galón de 3.785 L, ofrece una excelente relación calidad-precio para las tareas de limpieza más exigentes. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7401002002161",
        "precio_base": "3.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/762858/43549_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Great Value Bt 3785 Ml Galon",
        "descripcion": "Cloro Great Value en presentación original de 3.785ml. Ideal para la limpieza profunda del hogar, elimina eficazmente gérmenes y bacterias, dejando las superficies higiénicas y desinfectadas. Perfecto para baños, cocinas y áreas comunes. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7441078231140",
        "precio_base": "3.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/882994/cloro-great-value-bt-3785-ml-galon-7441078231140.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Great Value botella - 1893 ml",
        "descripcion": "Cloro Great Value regular en presentación de medio galón con 1,892 ml. Este es el formato más grande disponible, recomendado para hogares con alto consumo de cloro o uso frecuente en desinfección. Mantiene la fórmula clásica sin aromas adicionales, siendo versátil para múltiples tareas de limpieza del hogar. El volumen proporciona una cantidad significativa que dura varias semanas de uso regular. Se debe diluir en agua según las instrucciones para obtener la concentración correcta para c...",
        "codigo_barras": "7441078230709",
        "precio_base": "1.83",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/882976/cloro-great-value-botella-1893-ml-7441078230709.webp"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Magia Blanca En Gel 500 ml",
        "descripcion": "El Cloro Magia Blanca en gel de 500 ml es un producto diseñado para la limpieza y desinfección de superficies en el hogar, ofreciendo una aplicación más controlada gracias a su consistencia. Su fórmula permite adherirse mejor a las superficies, facilitando la eliminación de suciedad y bacterias. Es ideal para uso en baños, cocinas y áreas de alto contacto, contribuyendo a mantener la higiene. Su presentación facilita su uso en tareas diarias. Es una opción funcional para quienes buscan u...",
        "codigo_barras": "0785381006864",
        "precio_base": "1.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/737410/45376_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Gv Limpiad Multi C Cloro Repuest 1890Ml",
        "descripcion": "Limpiador multiusos Great Value de 1890 ml con cloro, ofreciendo volumen considerable de solución concentrada para limpieza general del hogar. Este limpiador está formulado para actuar en múltiples superficies y tipos de suciedad, proporcionando poder desinfectante gracias a su contenido de cloro. Es versátil y puede utilizarse en pisos, paredes, superficies de cocina, baños, azulejos y otras áreas donde se requiera limpieza profunda. La fórmula con cloro ayuda a eliminar gérmenes, bacte...",
        "codigo_barras": "0078742093352",
        "precio_base": "5.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/745248/99366_01.jpg"
    },
    {
        "categoria": "Limpieza del Hogar",
        "nombre": "Cloro Magia Blanca Campos De Limón -  1 L",
        "descripcion": "Cloro Magia Blanca Campos De Limón - 1 L el aliado indispensable para tu rutina de aseo, diseñado para ofrecer una limpieza profunda, efectiva y de alto rendimiento. Su fórmula avanzada actúa con total rapidez para remover la suciedad, la grasa o las manchas difíciles, devolviendo la frescura y la pureza original a cada superficie o tejido. Una alternativa sumamente versátil y confiable que garantiza un ambiente impecable y agradable para toda tu familia.",
        "codigo_barras": "7401002002178",
        "precio_base": "1.3",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/737423/43550_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo De La Granja Naranja 1890 ml 2Pack",
        "descripcion": "El pack de 2 unidades de Jugo de La Granja de Naranja, con un total de 1890 ml por botella, es la opción ideal para disfrutar del auténtico sabor cítrico y refrescante de la naranja en cualquier momento del día. Elaborado con jugos seleccionados, ofrece un equilibrio perfecto entre dulzura y frescura natural, conservando el sabor característico de la fruta. Su presentación en pack permite compartir fácilmente en familia, reuniones o eventos, garantizando comodidad y frescura en cada porc...",
        "codigo_barras": "2319373822392",
        "precio_base": "4.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/592973/49924_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Sula Naranja Mandarina Pet 473 ml",
        "descripcion": "El Jugo Sula Naranja Mandarina Pet de 473 ml combina el sabor cítrico de la naranja con el toque dulce y suave de la mandarina, ofreciendo una bebida refrescante y agradable al paladar. Además, su sabor equilibrado crea una experiencia revitalizante, perfecta para acompañar comidas o disfrutar sola en cualquier momento del día. Esta bebida destaca por su frescura natural y versatilidad, siendo ideal para quienes buscan una opción frutal que combine dulzura y acidez de manera armoniosa en...",
        "codigo_barras": "7421000846895",
        "precio_base": "0.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/381061/Jugo-Sula-Naranja-Mandarina-Pet-473-Ml-1-12770.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo De Naranja Y Zanahoria Sula 1750 ml",
        "descripcion": "Jugo de Naranja y Zanahoria sin pulpa, marca Sula. Ideal para disfrutar en cualquier momento del día. Viene en presentación de 1750ml, perfecta para compartir en familia.Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7421000846499",
        "precio_base": "3.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/579450/52819_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Jumex fresa banano lata -335 ml",
        "descripcion": "El Jugo Jumex sabor Fresa y Banano en presentación de 335 ml es la combinación perfecta de frutas para disfrutar de un sabor refrescante y natural. Elaborado con ingredientes de alta calidad, captura la dulzura de la fresa y la suavidad del banano, ofreciendo una experiencia frutal intensa en cada sorbo. Su envase práctico de 335 ml es ideal para llevarlo a la escuela, la oficina o cualquier actividad al aire libre. Jumex Fresa y Banano brinda frescura, sabor auténtico y nutrición, convi...",
        "codigo_barras": "7501013103281",
        "precio_base": "0.7",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/832019/jugo-jumex-sabor-fresa-banano-355-ml-7501013103281.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Sula Naranja Sin Pulpa 473 ml",
        "descripcion": "Jugo Sula Naranja Sin Pulpa 473 ml la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7421000844723",
        "precio_base": "0.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/960633/M-5_walmartsv_HNuolWVenJ_52816_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Sula Naranja Sin Pulpa 946 ml",
        "descripcion": "El jugo Sula de naranja sin pulpa de 946 ml es una opción práctica para disfrutar una bebida cítrica y refrescante en distintos momentos del día. Su sabor a naranja aporta una nota clásica y agradable que lo hace ideal para acompañar desayunos, meriendas, almuerzos o pausas dentro de la rutina familiar. Al ser sin pulpa, ofrece una textura más ligera y uniforme, adecuada para quienes prefieren bebidas suaves y fáciles de servir. Puede disfrutarse bien frío para resaltar mejor su perfil f...",
        "codigo_barras": "7421000811312",
        "precio_base": "2.35",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/234650/Jugo-Sula-Naranja-Sin-Pulpa-946Ml-1-10680.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Dr Juice Narajan Zanahoria 350 ml",
        "descripcion": "Jugo Dr Juice Narajan Zanahoria 350 ml la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7410030701526",
        "precio_base": "2.1",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/963012/M-5_walmartsv_iHWrUdrAua_48190_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Néctar Kerns Manzana - 1 L",
        "descripcion": "Los néctares Kern´s, son deliciosas bebidas de frutas, que contienen Vitamina C, y no tienen preservantes ni colorantes artificiales. Producto pulposo sin fermentar, destinado al consumo directo mezclando toda la parte comestible de la fruta en buen estado y madura, con adición de agua y con o sin adición de azúcares o miel y aditivos alimentarios permitidos. Se asocia con una marca de tradición y buena calidad, la cual proyecta valores de Jovialidad, Frescura, Saludable, confiable. Por ...",
        "codigo_barras": "0088313589771",
        "precio_base": "1.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/857566/nectar-kerns-manzana-1-l-0088313589771.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Great Value De Vegetales - 1.89 L",
        "descripcion": "El jugo 100% vegetal de gran valor es una bebida picante y sabrosa que satisface tus antojos salados. Esta combinación de jugos de tomate, zanahoria, apio, remolacha, lechuga, berros, espinacas y perejil ofrece un sabor excelente por sí sola y especialmente cuando se sirve con hielo. También sirve como base excelente para un Bloody Mary clásico y agrega sabor sin esfuerzo a una amplia variedad de platos principales, guarniciones y salsas. Este jugo es una buena fuente de calcio, hierro, ...",
        "codigo_barras": "0078742062037",
        "precio_base": "4.25",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/755625/47259_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Del Valle Mandarina - 500 ml",
        "descripcion": "Jugo Del Valle Mandarina 500 ml la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7411001806370",
        "precio_base": "0.5",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/858250/jugo-del-valle-mandarina-500-ml-7411001806370.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo De La Granja 12 Pack 2820 Ml",
        "descripcion": "Jugo De La Granja 12 Pack 2820 Ml",
        "codigo_barras": "7410030131262",
        "precio_base": "6.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/942786/M-5_walmartsv_QKPQrLPYzN_126015_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Del Valle Citrus - 1.5 L",
        "descripcion": "Jugo Del Valle Citrus - 1.5 L la opción ideal para refrescarte, mantenerte hidratado y disfrutar de un delicioso perfil de sabor en cualquier momento del día. Destaca por su empaque práctico y conveniente, siendo el acompañamiento perfecto para tus comidas, paseos o reuniones sociales con amigos y familia. Una alternativa sumamente versátil que aporta esa sensación de frescura inmediata que buscas para saciar tu sed o compartir en una ocasión especial.",
        "codigo_barras": "7411001805601",
        "precio_base": "1.0",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/761862/98714_01.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo Jumex Uva Prisma - 960 ml",
        "descripcion": "Jugo Jumex, Tetra Uva de 960 ml es la opción perfecta para disfrutar del auténtico sabor de la uva en cada sorbo. Su presentación es ideal para compartir en familia, acompañar comidas o tener siempre a mano una bebida deliciosa y refrescante. Con un sabor natural y dulce, Jugo Jumex ofrece una experiencia placentera que encanta a grandes y chicos. Elaborado con ingredientes de calidad, garantiza frescura y sabor en cada porción combinando conveniencia, calidad y sabor, convirtiéndose en ...",
        "codigo_barras": "7501013105506",
        "precio_base": "1.58",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/821523/jugo-jumex-uva-prisma-960-ml-7501013105506.jpg"
    },
    {
        "categoria": "Bebidas y Refrescos",
        "nombre": "Jugo V8 Campbells Mango Melocoton 473 ml",
        "descripcion": "Jugo V8 Campbell’s mango melocotón en presentación de 473 ml ofrece una mezcla deliciosa que combina la dulzura tropical del mango con el sabor suave y jugoso del melocotón. Esta fusión de frutas crea una bebida refrescante y naturalmente afrutada, perfecta para disfrutar en cualquier momento del día. Su práctico envase individual permite llevarlo fácilmente a la oficina, a la escuela o consumirlo en casa. Con una textura ligera y un equilibrio de sabores, este jugo se distingue por brin...",
        "codigo_barras": "0081537154633",
        "precio_base": "1.2",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/381074/Jugo-V8-Campbells-Mango-Melocoton-473Ml-1-23896.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Delmy Morolique - 200 g",
        "descripcion": "Queso Delmy Morolique - 200 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "7412900002085",
        "precio_base": "2.85",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/274651/Queso-Delmy-Morolique-200Gr-1-12739.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Crema Petacones - 228 g",
        "descripcion": "Queso crema Petacones es un queso untable de consistencia suave y sabor natural, ideal para untar y preparar deliciosas recetas, snacks y panes. Empaque de 226 g. Información del producto: La información de este producto es proporcionada por fabricantes y distribuidores. Te recomendamos verificar las especificaciones con el fabricante para obtener detalles más actualizados.",
        "codigo_barras": "7412900125036",
        "precio_base": "2.4",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/604650/54866_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "President Queso Gouda Lonchas 150 g",
        "descripcion": "President Queso Gouda Lonchas 150 g",
        "codigo_barras": "8718444725220",
        "precio_base": "3.75",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/929858/M-5_walmartsv_vgDCiyaPqQ_4145181_5.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Crem Queso G Baquero Trufa 125gr",
        "descripcion": "Crem Queso g Baquero Trufa 125 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "8412289006703",
        "precio_base": "3.8",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/669006/101807_01.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Petacones ranchero - 340 g",
        "descripcion": "El queso Petacones ranchero de 340 g es una alternativa práctica para complementar comidas tradicionales y preparaciones cotidianas con una textura firme y sabor característico. Puede servirse en desayunos, acompañamientos, antojitos, tortillas, frijoles, platillos típicos o utilizarse en recetas calientes y frías según la ocasión. Su presentación de 340 g ofrece una cantidad conveniente para varias porciones en el hogar, facilitando el almacenamiento y el uso diario. Es ideal para quienes bu...",
        "codigo_barras": "7412900100569",
        "precio_base": "6.95",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/320471/Queso-Semiduro-Madurado-Marca-Petacones-Ranchero-Picosito-340g-1-25826.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso President Emmental - 220 g",
        "descripcion": "President Queso Emmental Plaqueta 220gr",
        "codigo_barras": "3228022930205",
        "precio_base": "6.45",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/877751/president-queso-emmental-220-g-3228022930205.jpg"
    },
    {
        "categoria": "Lácteos y Huevos",
        "nombre": "Queso Delmy Morolique - 400 g",
        "descripcion": "Queso Delmy Morolique - 400 g desarrollado bajo altos estándares de producción láctea para ofrecer una solución consistente, fresca y de excelente rendimiento en el hogar. Su textura ideal y empaque práctico están pensados para facilitar su uso, garantizando la suavidad, el balance y el sabor característico que buscas en un producto de su categoría. Una elección inteligente para quienes buscan optimizar su despensa fría con un artículo confiable y nutritivo.",
        "codigo_barras": "7412900002078",
        "precio_base": "5.6",
        "imagen_url": "https://walmartsv.vteximg.com.br/arquivos/ids/962690/M-5_walmartsv_jRLMMQsgik_52792_01.jpg"
    }
]

def poblar_500() -> None:
    print("=== FASE 1: Asegurando catálogo base de 109 productos ===")
    p100.poblar()

    print("\n=== FASE 2: Cargando catálogo extendido (hasta 500+ productos) ===")
    BATCH_SIZE = 50
    total_nuevos = len(PRODUCTOS_ADICIONALES)
    creados = 0
    actualizados = 0
    inventario_creado = 0

    with SessionLocal() as db:
        categorias_map = {
            c.nombre: c.id_categoria for c in db.scalars(select(m.Categoria)).all()
        }
        sucursales_ids = [
            s.id_sucursal for s in db.scalars(select(m.Sucursal).where(m.Sucursal.activa.is_(True))).all()
        ]

    for i in range(0, total_nuevos, BATCH_SIZE):
        lote = PRODUCTOS_ADICIONALES[i : i + BATCH_SIZE]
        with SessionLocal() as db:
            for p_data in lote:
                cat_id = categorias_map.get(p_data["categoria"])
                if not cat_id:
                    continue

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
                    producto.id_categoria = cat_id
                    producto.descripcion = p_data["descripcion"]
                    producto.precio_base = D(p_data["precio_base"])
                    producto.imagen_url = p_data["imagen_url"]
                    producto.activo = True
                    actualizados += 1
                else:
                    producto = m.Producto(
                        id_categoria=cat_id,
                        codigo_barras=p_data["codigo_barras"],
                        nombre=p_data["nombre"],
                        descripcion=p_data["descripcion"],
                        precio_base=D(p_data["precio_base"]),
                        imagen_url=p_data["imagen_url"],
                        activo=True,
                    )
                    db.add(producto)
                    db.flush()
                    creados += 1

                for suc_id in sucursales_ids:
                    inv = db.scalar(
                        select(m.Inventario).where(
                            m.Inventario.id_sucursal == suc_id,
                            m.Inventario.id_producto == producto.id_producto,
                        )
                    )
                    if not inv:
                        db.add(
                            m.Inventario(
                                id_sucursal=suc_id,
                                id_producto=producto.id_producto,
                                stock_disponible=50,
                            )
                        )
                        inventario_creado += 1
                    elif inv.stock_disponible < 10:
                        inv.stock_disponible = 50

            db.commit()
            db.expunge_all()
        gc.collect()
        print(f"  Lote procesado: {min(i + BATCH_SIZE, total_nuevos)} / {total_nuevos} productos...")

    with SessionLocal() as db:
        total_final = len(db.scalars(select(m.Producto)).all())
        sin_img = db.scalars(
            select(m.Producto).where(
                (m.Producto.imagen_url.is_(None)) | (m.Producto.imagen_url == "")
            )
        ).all()

    print("\n=== RESUMEN FINAL DEL CATÁLOGO EXTENDIDO ===")
    print(f"  - Nuevos productos agregados: {creados}")
    print(f"  - Productos adicionales actualizados: {actualizados}")
    print(f"  - Registros de inventario creados: {inventario_creado}")
    print(f"  - TOTAL PRODUCTOS EN BASE DE DATOS: {total_final}")
    if sin_img:
        print(f"  [ALERTA] Productos sin imagen: {len(sin_img)}")
    else:
        print(f"  [OK] 100% de productos ({total_final}) tienen imagen asignada (0 faltantes).")


if __name__ == "__main__":
    poblar_500()
