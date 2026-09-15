"""Demo ejecutable del catálogo de Food Store.

Ejecutar con:  python main.py
"""

from catalogo import (
    Categoria,
    ErrorDominio,
    Exportable,
    Producto,
    ProductoCategoria,
    ProductoCombo,
    ProductoDestacado,
    ProductoPorPeso,
    ProductoSimple,
    UnidadMedida,
    exportar_catalogo,
)
from libreria_externa import FichaPuntoDeVenta


def crear_categorias() -> dict[str, Categoria]:
    """Arma las categorías base del menú."""
    return {
        "bebidas": Categoria("Bebidas", "Gaseosas, jugos y aguas"),
        "fiambreria": Categoria("Fiambrería"),
        "combos": Categoria("Combos"),
        "ofertas": Categoria("Ofertas"),
    }


def crear_unidades() -> dict[str, UnidadMedida]:
    """Arma las unidades de venta del catálogo."""
    return {
        "kg": UnidadMedida("kilogramo", "kg", "masa"),
        "unidad": UnidadMedida("unidad", "u", "unidad"),
    }


def crear_productos(
    categorias: dict[str, Categoria], unidades: dict[str, UnidadMedida]
) -> dict[str, Producto]:
    """Arma productos por pieza, por peso y un combo.

    Gaseosa y jamón son los componentes del combo; jugo, agua, queso y el
    propio combo son productos sueltos del catálogo.
    """
    gaseosa = ProductoSimple(
        "Gaseosa 1.5L",
        1500.0,
        categorias["bebidas"],
        stock_cantidad=24,
        unidad_venta=unidades["unidad"],
    )
    jugo = ProductoSimple(
        "Jugo de naranja", 900.0, categorias["bebidas"], stock_cantidad=15
    )
    agua = ProductoSimple(
        "Agua mineral",
        700.0,
        categorias["bebidas"],
        unidad_venta=unidades["unidad"],
    )
    jamon = ProductoPorPeso(
        "Jamón cocido",
        9800.0,
        categorias["fiambreria"],
        stock_cantidad=8.0,
        unidad_venta=unidades["kg"],
    )
    queso = ProductoPorPeso(
        "Queso cremoso",
        7200.0,
        categorias["fiambreria"],
        stock_cantidad=5.5,
        unidad_venta=unidades["kg"],
    )
    combo = ProductoCombo(
        "Combo picada",
        [gaseosa, jamon],
        0.10,
        categorias["combos"],
    )
    return {
        "gaseosa": gaseosa,
        "jugo": jugo,
        "agua": agua,
        "jamon": jamon,
        "queso": queso,
        "combo": combo,
    }


def clasificar_productos(
    productos: dict[str, Producto], categorias: dict[str, Categoria]
) -> None:
    """Suma clasificaciones adicionales a algunos productos.

    El vínculo lo fabrica el propio producto: acá nunca se instancia
    ``ProductoCategoria`` a mano, solo se pide la clasificación.
    """
    productos["jugo"].clasificar_en(categorias["ofertas"])
    productos["combo"].clasificar_en(categorias["ofertas"], es_principal=True)


def mostrar_catalogo(productos: dict[str, Producto]) -> None:
    """Lista nombre, precio publicado, categoría principal y disponibilidad."""
    print("--- Catálogo ---")
    for producto in productos.values():
        print(
            f"{producto.nombre:<16} {producto.precio_publicado:<16} "
            f"{producto.categoria_principal().nombre:<11} "
            f"disponible={producto.disponible}"
        )


def calcular_precios(productos: dict[str, Producto]) -> None:
    """Calcula precios finales con cantidades distintas.

    Cada producto aplica su propia regla: el bucle no pregunta de qué
    subclase es cada uno.
    """
    pedidos: list[tuple[Producto, float]] = [
        (productos["gaseosa"], 3),
        (productos["agua"], 6.0),
        (productos["jamon"], 0.250),
        (productos["queso"], 1.5),
        (productos["combo"], 2),
    ]
    print("--- Precios finales ---")
    for producto, cantidad in pedidos:
        precio = producto.precio_final(cantidad)
        print(f"{producto.nombre:<16} cantidad={cantidad:<6} $ {precio:.2f}")


def demostrar_habilitacion(productos: dict[str, Producto]) -> None:
    """Muestra el efecto de deshabilitar y habilitar sobre ``disponible``."""
    print("--- Habilitación: efecto sobre disponible ---")
    jamon = productos["jamon"]
    combo = productos["combo"]
    agua = productos["agua"]

    def estado(momento: str) -> None:
        print(
            f"{momento:<22} {jamon.nombre}={jamon.disponible}, "
            f"{combo.nombre}={combo.disponible}"
        )

    estado("Inicial:")
    jamon.deshabilitar()
    estado("Jamón deshabilitado:")
    jamon.habilitar()
    estado("Jamón habilitado:")
    print(
        f"{agua.nombre} está habilitada pero sin stock: "
        f"disponible={agua.disponible}"
    )


def mostrar_vidriera(productos: dict[str, Producto]) -> None:
    """Arma la vidriera: cualquier tipo de producto puede destacarse."""
    vidriera = [
        ProductoDestacado(productos["queso"], 2),
        ProductoDestacado(productos["combo"], 1),
        ProductoDestacado(productos["gaseosa"], 3),
    ]
    print("--- Vidriera ---")
    for destacado in sorted(vidriera, key=lambda d: d.orden_vidriera):
        producto = destacado.producto
        print(
            f"{destacado.orden_vidriera}. {producto.nombre} "
            f"({producto.precio_publicado})"
        )


def exportar_al_punto_de_venta(productos: dict[str, Producto]) -> None:
    """Exporta productos propios y una ficha externa en una sola operación."""
    ficha = FichaPuntoDeVenta("A1", "Descuento apertura")
    items: list[Exportable] = [*productos.values(), ficha]
    print("--- Exportación al punto de venta ---")
    for linea in exportar_catalogo(items):
        print(linea)


def demostrar_composicion(
    productos: dict[str, Producto], categorias: dict[str, Categoria]
) -> None:
    """El vínculo de clasificación solo existe dentro del producto dueño."""
    print("--- Composición: ProductoCategoria nace dentro del producto ---")
    combo = productos["combo"]
    agua = productos["agua"]

    try:
        ProductoCategoria(categorias["bebidas"], True)
    except ErrorDominio as error:
        print(f"Construirlo desde afuera: {error}")

    resultado = agua.clasificar_en(  # type: ignore[func-returns-value]
        categorias["ofertas"]
    )
    print(f"clasificar_en() no devuelve el vínculo: {resultado}")

    vinculos = combo.categorias()
    detalle = ", ".join(
        f"{v.categoria.nombre}(principal={v.es_principal})" for v in vinculos
    )
    print(f"Vínculos del combo: {detalle}")
    try:
        vinculos.append(vinculos[0])  # type: ignore[attr-defined]
    except AttributeError:
        print("categorias() es una tupla: no se pueden agregar vínculos")
    try:
        vinculos[0].es_principal = True  # type: ignore[misc]
    except AttributeError:
        print("es_principal no tiene setter: no se puede reasignar")
    print(f"Principal del combo: {combo.categoria_principal().nombre}")


def demostrar_agregacion(
    productos: dict[str, Producto], categorias: dict[str, Categoria]
) -> None:
    """Los componentes sobreviven al combo y se pueden reagrupar.

    Retira el combo del catálogo (``productos`` queda sin él) y vuelve a
    usar la gaseosa y el jamón, que eran sus componentes.
    """
    print("--- Agregación: los componentes sobreviven al combo ---")
    combo = productos.pop("combo")
    nombre_combo = combo.nombre
    del combo
    componentes = [productos["gaseosa"], productos["jamon"]]
    print(f"'{nombre_combo}' fue retirado. Sus componentes siguen vigentes:")
    for componente in componentes:
        print(
            f"  {componente.nombre}: {componente.precio_publicado}, "
            f"disponible={componente.disponible}"
        )
    otro_combo = ProductoCombo(
        "Combo verano", componentes, 0.05, categorias["combos"]
    )
    print(
        f"Reagrupados en '{otro_combo.nombre}': "
        f"{otro_combo.precio_publicado}"
    )


def demostrar_falla_temprana(categorias: dict[str, Categoria]) -> None:
    """La clase abstracta y una subclase incompleta fallan al construir."""
    print("--- Falla temprana: clase abstracta incompleta ---")

    class ProductoSinRegla(Producto):
        pass

    try:
        Producto("X", 1.0, categorias["ofertas"])  # type: ignore[abstract]
    except TypeError as error:
        print(f"Producto: {error}")
    try:
        ProductoSinRegla(  # type: ignore[abstract]
            "X", 1.0, categorias["ofertas"]
        )
    except TypeError as error:
        print(f"ProductoSinRegla: {error}")


def main() -> None:
    categorias = crear_categorias()
    unidades = crear_unidades()
    productos = crear_productos(categorias, unidades)
    clasificar_productos(productos, categorias)

    mostrar_catalogo(productos)
    calcular_precios(productos)
    demostrar_habilitacion(productos)
    mostrar_vidriera(productos)
    exportar_al_punto_de_venta(productos)
    demostrar_composicion(productos, categorias)
    demostrar_agregacion(productos, categorias)
    demostrar_falla_temprana(categorias)


if __name__ == "__main__":
    main()
