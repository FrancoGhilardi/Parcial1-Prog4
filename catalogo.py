"""Dominio del catálogo de Food Store.

Modela productos vendibles por pieza, por peso y en combo, su clasificación
en categorías, la unidad de venta, el rol promocional de destacado y el
contrato de exportación hacia el sistema de caja de un tercero.

Este módulo no hace persistencia ni I/O: el catálogo vive en memoria mientras
dura la ejecución.
"""

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, Protocol, override

__all__ = [
    "ErrorDominio",
    "UnidadMedida",
    "Categoria",
    "ProductoCategoria",
    "Producto",
    "ProductoSimple",
    "ProductoPorPeso",
    "ProductoCombo",
    "ProductoDestacado",
    "Exportable",
    "exportar_catalogo",
]


class ErrorDominio(ValueError):
    """Se lanza cuando se viola una regla de negocio del catálogo.

    Hereda de ``ValueError`` para que el código que ya atrapa ``ValueError``
    siga funcionando sin cambios.
    """


def _validar_texto_no_vacio(valor: object, campo: str) -> str:
    """Valida que ``valor`` sea ``str`` con contenido y lo devuelve limpio."""
    if not isinstance(valor, str):
        raise TypeError(
            f"{campo} debe ser str, se recibió {type(valor).__name__}."
        )
    texto = valor.strip()
    if not texto:
        raise ErrorDominio(f"{campo} no puede estar vacío.")
    return texto


def _validar_numero(valor: object, campo: str) -> float:
    """Valida número finito; ``bool`` no cuenta aunque sea subclase de int."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise TypeError(
            f"{campo} debe ser numérico, se recibió {type(valor).__name__}."
        )
    if not math.isfinite(valor):
        raise ErrorDominio(f"{campo} debe ser un número finito.")
    return float(valor)


def _validar_no_negativo(valor: object, campo: str) -> float:
    """Valida un número finito mayor o igual a cero (precio base, stock)."""
    numero = _validar_numero(valor, campo)
    if numero < 0:
        raise ErrorDominio(f"{campo} no puede ser negativo.")
    return numero


def _validar_cantidad_entera(cantidad: object) -> float:
    """Valida cantidad entera >= 1 (acepta ``3.0``, rechaza ``2.5``)."""
    numero = _validar_numero(cantidad, "cantidad")
    if not numero.is_integer() or numero < 1:
        raise ErrorDominio(
            "cantidad debe ser un valor entero mayor o igual a 1."
        )
    return numero


def _validar_cantidad_positiva(cantidad: object) -> float:
    """Valida una cantidad mayor a cero que admite decimales."""
    numero = _validar_numero(cantidad, "cantidad")
    if numero <= 0:
        raise ErrorDominio("cantidad debe ser mayor a 0.")
    return numero


@dataclass(frozen=True)
class UnidadMedida:
    """Unidad en la que se vende un producto (kilogramo, gramo, litro, unidad).

    Es un objeto de valor inmutable: no cambia una vez creado y puede
    compartirse entre varios productos.

    Attributes:
        nombre: Nombre legible, por ejemplo ``"kilogramo"``.
        simbolo: Símbolo que se muestra en el precio publicado, por
            ejemplo ``"kg"``.
        tipo: Dato descriptivo (``"masa"``, ``"volumen"``, ``"unidad"``).
            Ninguna regla del catálogo lo consulta; es solo informativo.
    """

    nombre: str
    simbolo: str
    tipo: str

    def __post_init__(self) -> None:
        """Valida que los tres campos sean textos no vacíos.

        Raises:
            TypeError: Si algún campo no es ``str``.
            ErrorDominio: Si algún campo está vacío.
        """
        for campo in ("nombre", "simbolo", "tipo"):
            _validar_texto_no_vacio(getattr(self, campo), campo)


class Categoria:
    """Agrupa productos del catálogo (Bebidas, Gaseosas, Fiambrería).

    Es la entidad a la que apunta cada vínculo de clasificación y existe con
    independencia de los productos que agrupa.
    """

    def __init__(self, nombre: str, descripcion: str = "") -> None:
        """Crea una categoría.

        Args:
            nombre: Nombre visible en el menú. No puede estar vacío.
            descripcion: Texto libre de catálogo; cadena vacía por defecto.

        Raises:
            TypeError: Si ``nombre`` o ``descripcion`` no son ``str``.
            ErrorDominio: Si ``nombre`` está vacío.
        """
        self._nombre = _validar_texto_no_vacio(nombre, "nombre")
        if not isinstance(descripcion, str):
            raise TypeError("descripcion debe ser str.")
        self._descripcion = descripcion

    @property
    def nombre(self) -> str:
        """Nombre de la categoría."""
        return self._nombre

    @property
    def descripcion(self) -> str:
        """Descripción de catálogo."""
        return self._descripcion

    def __repr__(self) -> str:
        return f"Categoria(nombre={self._nombre!r})"


# Token privado del módulo: solo Producto puede fabricar vínculos de
# clasificación.
_TOKEN_VINCULO: Final[object] = object()


class ProductoCategoria:
    """Vínculo de clasificación entre un producto y una categoría.

    Es la parte de una composición: solo tiene sentido dentro del producto que
    lo fabrica al clasificarse. El código cliente nunca lo instancia ni lo
    reemplaza, solo lo lee a través de ``Producto.categorias()``.

    Attributes:
        _categoria: Categoría a la que apunta el vínculo.
        _es_principal: Indica si es la clasificación principal del producto.
    """

    def __init__(
        self, categoria: Categoria, es_principal: bool, token: object = None
    ) -> None:
        """Crea el vínculo. Uso exclusivo del producto dueño.

        Args:
            categoria: Categoría clasificadora.
            es_principal: Si la clasificación es la principal.
            token: Credencial interna del módulo.

        Raises:
            ErrorDominio: Si se intenta crear fuera del producto dueño.
        """
        if token is not _TOKEN_VINCULO:
            raise ErrorDominio(
                "ProductoCategoria solo puede crearse desde el producto "
                "que clasifica."
            )
        self._categoria = categoria
        self._es_principal = es_principal

    @property
    def categoria(self) -> Categoria:
        """Categoría del vínculo."""
        return self._categoria

    @property
    def es_principal(self) -> bool:
        """``True`` si es la clasificación principal."""
        return self._es_principal

    def _marcar_principal(self, valor: bool) -> None:
        """Cambia la marca de principal. Solo lo invoca el producto dueño.

        Args:
            valor: Nuevo estado de la marca.
        """
        self._es_principal = valor

    def __repr__(self) -> str:
        return (
            f"ProductoCategoria({self._categoria.nombre!r}, "
            f"es_principal={self._es_principal})"
        )


class Producto(ABC):
    """Producto abstracto del catálogo de Food Store.

    Cada producto conoce sus categorías y opcionalmente una unidad de
    venta que existe por su cuenta. En todo momento tiene exactamente
    una clasificación principal.

    Attributes:
        _nombre: Nombre no vacío.
        _precio_base: Precio base, mayor o igual a cero.
        _stock_cantidad: Existencias, mayor o igual a cero.
        _habilitado: Si el producto está habilitado para la venta.
        _unidad_venta: Unidad de venta o ``None``.
        _clasificaciones: Vínculos de clasificación (la lista nunca se expone).
    """

    def __init__(
        self,
        nombre: str,
        precio_base: float,
        categoria_principal: Categoria,
        *,
        stock_cantidad: float = 0.0,
        unidad_venta: UnidadMedida | None = None,
    ) -> None:
        """Crea el producto validando el dominio y su clasificación principal.

        Args:
            nombre: Nombre del producto. No puede estar vacío.
            precio_base: Precio base, mayor o igual a cero.
            categoria_principal: Categoría que determina dónde aparece en
                el menú.
            stock_cantidad: Existencias iniciales, mayor o igual a cero.
            unidad_venta: Unidad de venta opcional.

        Raises:
            TypeError: Si algún argumento no es del tipo declarado.
            ErrorDominio: Si se viola una regla de dominio.
        """
        self._nombre = _validar_texto_no_vacio(nombre, "nombre")
        self._precio_base = _validar_no_negativo(precio_base, "precio_base")
        self._stock_cantidad = _validar_no_negativo(
            stock_cantidad, "stock_cantidad"
        )
        es_unidad = isinstance(unidad_venta, UnidadMedida)
        if unidad_venta is not None and not es_unidad:
            raise TypeError("unidad_venta debe ser UnidadMedida o None.")
        self._unidad_venta = unidad_venta
        self._habilitado = True
        self._clasificaciones: list[ProductoCategoria] = []
        self.clasificar_en(categoria_principal, es_principal=True)

    @property
    def nombre(self) -> str:
        """Nombre del producto."""
        return self._nombre

    @property
    def precio_base(self) -> float:
        """Precio base."""
        return self._precio_base

    @property
    def unidad_venta(self) -> UnidadMedida | None:
        """Unidad de venta asociada, o ``None`` si el producto no tiene."""
        return self._unidad_venta

    @property
    def disponible(self) -> bool:
        """``True`` solo si está habilitado y hay stock."""
        return self._habilitado and self._hay_stock()

    @property
    def precio_publicado(self) -> str:
        """Precio formateado para mostrar al cliente.

        ``"$ 12.50 / kg"`` con unidad de venta, ``"$ 3.00"`` sin ella.
        """
        texto = f"$ {self.precio_base:.2f}"
        if self._unidad_venta is None:
            return texto
        return f"{texto} / {self._unidad_venta.simbolo}"

    def habilitar(self) -> None:
        """Habilita el producto para la venta."""
        self._habilitado = True

    def deshabilitar(self) -> None:
        """Deshabilita el producto para la venta."""
        self._habilitado = False

    def _hay_stock(self) -> bool:
        """Determina si hay existencias para vender.

        Returns:
            ``True`` si el stock propio es mayor que cero.
        """
        return self._stock_cantidad > 0

    @abstractmethod
    def precio_final(self, cantidad: float) -> float:
        """Calcula el precio final para ``cantidad``.

        Cada subclase define su regla.

        Args:
            cantidad: Cantidad a vender; su validación depende de la subclase.

        Returns:
            Precio final como ``float``.
        """

    def clasificar_en(
        self, categoria: Categoria, es_principal: bool = False
    ) -> None:
        """Agrega una clasificación fabricando internamente el vínculo.

        Si ``es_principal`` es ``True``, la clasificación principal anterior
        pasa a ``es_principal=False``: el producto garantiza que en todo
        momento hay exactamente una principal.

        Args:
            categoria: Categoría en la que se clasifica.
            es_principal: Si la nueva clasificación pasa a ser la principal.

        Raises:
            TypeError: Si ``categoria`` no es ``Categoria`` o
                ``es_principal`` no es ``bool``.
            ErrorDominio: Si el producto ya está clasificado en esa categoría.
        """
        if not isinstance(categoria, Categoria):
            raise TypeError("categoria debe ser una Categoria.")
        if not isinstance(es_principal, bool):
            raise TypeError("es_principal debe ser bool.")
        if any(v.categoria is categoria for v in self._clasificaciones):
            raise ErrorDominio(
                f"{self._nombre!r} ya está clasificado en "
                f"{categoria.nombre!r}."
            )

        nuevo = ProductoCategoria(categoria, es_principal, _TOKEN_VINCULO)
        if es_principal:
            for vinculo in self._clasificaciones:
                vinculo._marcar_principal(False)
        self._clasificaciones.append(nuevo)

    def categorias(self) -> tuple[ProductoCategoria, ...]:
        """Devuelve los vínculos de clasificación.

        Returns:
            Tupla construida a partir de la lista interna: copia e inmutable.
        """
        return tuple(self._clasificaciones)

    def categoria_principal(self) -> Categoria:
        """Devuelve la categoría principal.

        Returns:
            La categoría del único vínculo con ``es_principal=True``.
        """
        return next(
            v.categoria for v in self._clasificaciones if v.es_principal
        )

    def exportar(self) -> str:
        """Serializa el producto para el sistema de caja.

        Returns:
            Cadena con el formato
            ``"PROD|<nombre>|<precio_publicado>|<categoría principal>"``.
        """
        return (
            f"PROD|{self._nombre}|{self.precio_publicado}|"
            f"{self.categoria_principal().nombre}"
        )


class ProductoSimple(Producto):
    """Producto que se vende por pieza (una botella, un paquete)."""

    @override
    def precio_final(self, cantidad: float) -> float:
        """Calcula ``precio_base × cantidad``.

        Args:
            cantidad: Valor entero mayor o igual a 1 (3 y 3.0 válidos; 2.5 no).

        Returns:
            Precio final sin redondear.

        Raises:
            TypeError: Si ``cantidad`` no es numérica.
            ErrorDominio: Si ``cantidad`` no es entera o es menor a 1.
        """
        return self.precio_base * _validar_cantidad_entera(cantidad)


class ProductoPorPeso(Producto):
    """Producto que se vende por peso (fiambres, verdura).

    El precio base se expresa por unidad de masa y la cantidad admite
    decimales.
    """

    @override
    def precio_final(self, cantidad: float) -> float:
        """Calcula ``precio_base × cantidad`` redondeado a 2 decimales.

        Args:
            cantidad: Valor mayor a 0; admite decimales (0.250 es válido).

        Returns:
            Precio final redondeado a 2 decimales.

        Raises:
            TypeError: Si ``cantidad`` no es numérica.
            ErrorDominio: Si ``cantidad`` es menor o igual a 0.
        """
        cantidad_valida = _validar_cantidad_positiva(cantidad)
        return round(self.precio_base * cantidad_valida, 2)


class ProductoCombo(Producto):
    """Producto que agrupa de 2 a N productos ya construidos, con descuento.

    Los componentes se reciben ya construidos: existen antes del combo, lo
    sobreviven y pueden reagruparse en otros combos. Un componente puede ser,
    a su vez, otro combo.

    Attributes:
        _componentes: Lista interna de productos agregados (nunca se expone).
        _descuento: Proporción en ``[0, 1)`` fijada al construir.
    """

    MINIMO_COMPONENTES: Final[int] = 2

    def __init__(
        self,
        nombre: str,
        componentes: Iterable[Producto],
        descuento: float,
        categoria_principal: Categoria,
        *,
        unidad_venta: UnidadMedida | None = None,
    ) -> None:
        """Crea el combo validando componentes y descuento.

        El precio base se deriva de la suma de los componentes al momento de
        construir, ya descontada: así ``precio_publicado`` siempre refleja el
        precio real del combo, sin quedar desactualizado.

        Args:
            nombre: Nombre del combo.
            componentes: Productos ya construidos (al menos 2).
            descuento: Proporción en ``[0, 1)``; se fija al construir.
            categoria_principal: Categoría principal del combo.
            unidad_venta: Unidad de venta opcional.

        Raises:
            TypeError: Si algún componente no es ``Producto``.
            ErrorDominio: Si hay menos de 2 componentes o el descuento está
                fuera de ``[0, 1)``.
        """
        lista = list(componentes)
        for componente in lista:
            if not isinstance(componente, Producto):
                raise TypeError(
                    "Cada componente del combo debe ser un Producto."
                )
        if len(lista) < self.MINIMO_COMPONENTES:
            raise ErrorDominio("Un combo necesita al menos 2 componentes.")
        valor_descuento = _validar_numero(descuento, "descuento")
        if not 0 <= valor_descuento < 1:
            raise ErrorDominio(
                "El descuento debe ser mayor o igual a 0 y menor a 1."
            )

        precio_unitario = self._subtotal(lista) * (1 - valor_descuento)
        super().__init__(
            nombre,
            precio_unitario,
            categoria_principal,
            stock_cantidad=0.0,
            unidad_venta=unidad_venta,
        )
        self._componentes = lista
        self._descuento = valor_descuento

    @staticmethod
    def _subtotal(componentes: Iterable[Producto]) -> float:
        """Suma ``precio_final(1)`` de cada componente.

        Args:
            componentes: Productos a sumar.

        Returns:
            Suma de los precios unitarios finales.
        """
        return sum(componente.precio_final(1) for componente in componentes)

    def componentes(self) -> tuple[Producto, ...]:
        """Devuelve los componentes del combo.

        Returns:
            Tupla construida a partir de la lista interna: copia e inmutable.
        """
        return tuple(self._componentes)

    @override
    def precio_final(self, cantidad: float) -> float:
        """Calcula el precio final del combo.

        Suma ``precio_final(1)`` de cada componente, aplica
        ``(1 − descuento)`` y multiplica por ``cantidad``.

        Args:
            cantidad: Valor entero mayor o igual a 1.

        Returns:
            Precio final sin redondear.

        Raises:
            TypeError: Si ``cantidad`` no es numérica.
            ErrorDominio: Si ``cantidad`` no es entera o es menor a 1.
        """
        unidades = _validar_cantidad_entera(cantidad)
        subtotal = self._subtotal(self._componentes)
        return subtotal * (1 - self._descuento) * unidades

    @override
    def _hay_stock(self) -> bool:
        """El combo no tiene stock propio: depende de sus componentes.

        Returns:
            ``True`` si todos sus componentes están disponibles.
        """
        return all(componente.disponible for componente in self._componentes)


class ProductoDestacado:
    """Rol promocional de un producto en la vidriera.

    "Destacado" no describe una forma nueva de vender: no tiene una regla de
    precio propia y es un estado temporal, no una condición permanente desde
    la construcción. Por eso no hereda de ``Producto`` sino que lo referencia:
    cualquier producto del catálogo puede destacarse sin necesidad de duplicar
    la jerarquía de ventas en variantes "destacadas".

    Attributes:
        _producto: Producto promocionado; existe con independencia del
            destacado.
        _orden_vidriera: Posición de aparición en la vidriera, entero
            mayor o igual a 1.
    """

    def __init__(self, producto: Producto, orden_vidriera: int) -> None:
        """Destaca un producto en una posición de la vidriera.

        Args:
            producto: Producto a destacar.
            orden_vidriera: Posición en la vidriera (1 = primero).

        Raises:
            TypeError: Si ``producto`` no es ``Producto`` u
                ``orden_vidriera`` no es ``int``.
            ErrorDominio: Si ``orden_vidriera`` es menor a 1.
        """
        if not isinstance(producto, Producto):
            raise TypeError("producto debe ser un Producto.")
        es_entero = isinstance(orden_vidriera, int)
        if isinstance(orden_vidriera, bool) or not es_entero:
            raise TypeError("orden_vidriera debe ser int.")
        if orden_vidriera < 1:
            raise ErrorDominio("orden_vidriera debe ser mayor o igual a 1.")
        self._producto = producto
        self._orden_vidriera = orden_vidriera

    @property
    def producto(self) -> Producto:
        """Producto destacado."""
        return self._producto

    @property
    def orden_vidriera(self) -> int:
        """Orden de aparición en la vidriera."""
        return self._orden_vidriera

    def __repr__(self) -> str:
        return (
            f"ProductoDestacado({self._producto.nombre!r}, "
            f"orden={self._orden_vidriera})"
        )


class Exportable(Protocol):
    """Contrato estructural de todo lo que puede enviarse al sistema de caja.

    Se resuelve como ``Protocol`` porque ``FichaPuntoDeVenta`` pertenece a un
    tercero, no se puede modificar y no hereda de nada del catálogo: la
    conformidad se da por tener el método, no por declararlo. Ninguna clase
    del dominio hereda de ``Exportable``.
    """

    def exportar(self) -> str:
        """Devuelve la representación textual del objeto."""
        ...


def exportar_catalogo(items: list[Exportable]) -> list[str]:
    """Exporta en una sola operación productos propios y fichas externas.

    Resuelve por duck typing: no usa ``isinstance``.

    Args:
        items: Objetos que cumplen estructuralmente ``Exportable``.

    Returns:
        Una cadena exportada por cada ítem, en el mismo orden.
    """
    return [item.exportar() for item in items]
