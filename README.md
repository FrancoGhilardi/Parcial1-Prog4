# Food Store — Catálogo

Modelo de dominio en Python puro (sin dependencias externas) para el catálogo
de un comercio que vende productos por pieza, por peso y en combos armados a
partir de productos ya existentes. Incluye clasificación en categorías,
unidad de venta opcional, destacados de vidriera y exportación al sistema de
caja de un tercero.

## Requisitos

- Python 3.12 o superior. No hace falta instalar nada más: todo el proyecto
  usa solo la biblioteca estándar.

## Cómo ejecutar

```bash
python main.py
```

Corre una demo que arma un catálogo de ejemplo, clasifica productos,
calcula precios finales, muestra el efecto de deshabilitar y habilitar
sobre la disponibilidad, arma una vidriera de destacados y exporta todo
junto con una ficha del sistema de caja externo. Al final deja a la vista
las decisiones de diseño: composición (el vínculo de categoría solo nace
dentro del producto), agregación (los componentes sobreviven al combo y se
reagrupan) y falla temprana (la clase abstracta no se puede construir).

## Cómo correr las pruebas

```bash
python -m unittest discover -s tests -v
```

## Estructura

```
catalogo.py           # dominio completo del catálogo
libreria_externa.py   # provista por el sistema de caja de un tercero, no se modifica
main.py               # demo ejecutable
uml/modelo_final.md    # diagrama de clases
tests/                 # pruebas locales (no forma parte de la entrega)
```

## Decisiones de diseño

**Excepciones.** `ErrorDominio` hereda de `ValueError` para las reglas de
negocio (nombre vacío, precio negativo, cantidad inválida, etc.). Un
argumento que no es del tipo declarado en la firma lanza `TypeError` en
cambio: son dos problemas distintos y conviene distinguirlos.

**`ProductoDestacado` no hereda de `Producto`.** Destacar un producto es un
estado promocional temporal, no una forma distinta de vender: no define
ninguna regla propia de precio. Modelarlo con herencia obligaría a decidir
qué precio tendría un destacado, o a crear una subclase destacada por cada
tipo de venta. En cambio, `ProductoDestacado` referencia al producto que
destaca (`producto`) y guarda su posición en la vidriera
(`orden_vidriera`), así que cualquier producto del catálogo —simple, por
peso o combo— puede destacarse sin tocar la jerarquía de ventas.

El costo de esta decisión es aceptado a conciencia: un destacado no *es* un
producto, así que no se le puede pedir `precio_final()` ni pasarlo a
`exportar_catalogo()`; para eso se usa `destacado.producto`. La vidriera es
una colección aparte de `ProductoDestacado` que hay que mantener junto al
catálogo, y el modelo no impide que dos destacados compartan el mismo
orden ni que un producto se destaque dos veces (ordenar y depurar la
vidriera queda del lado de quien la arma). A cambio, la jerarquía de venta
queda intacta y no hay que duplicar subclases.

**Precio de un combo.** Se calcula una sola vez, al construir el combo, a
partir de la suma de sus componentes con el descuento ya aplicado. Como los
componentes no tienen setter de precio y el descuento se fija al crear el
combo, ese valor nunca puede quedar desactualizado.

**Stock del combo.** No tiene stock propio: un combo está disponible cuando
está habilitado y todos sus componentes también lo están. Esto evita llevar
un conteo de stock separado del que ya tienen los productos que lo forman.

**Vínculo producto-categoría.** `ProductoCategoria` solo puede crearse desde
el producto que clasifica (usa una credencial interna del módulo); el código
que arma el catálogo nunca lo instancia a mano ni lo reemplaza, solo agrega
clasificaciones con `clasificar_en()`. Esto garantiza que un producto tenga
siempre exactamente una clasificación principal.

**Exportación al punto de venta.** El contrato `Exportable` se define como
`Protocol` en lugar de una clase abstracta, porque una de las clases que
debe cumplirlo (`FichaPuntoDeVenta`) pertenece a un sistema de terceros que
no se puede modificar. Ninguna clase declara heredar de `Exportable`: la
conformidad es estructural, alcanza con tener el método `exportar()`.
