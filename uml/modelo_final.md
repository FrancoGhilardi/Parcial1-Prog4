# Diagrama de clases — Food Store

```mermaid
classDiagram
    class Exportable {
        <<Protocol>>
        +exportar() str
    }
    class Producto {
        <<abstract>>
        #_nombre str
        #_precio_base float
        #_stock_cantidad float
        #_habilitado bool
        #_unidad_venta UnidadMedida
        #_clasificaciones list~ProductoCategoria~
        +nombre str
        +precio_base float
        +unidad_venta UnidadMedida
        +disponible bool
        +precio_publicado str
        +precio_final(cantidad float)* float
        +habilitar() None
        +deshabilitar() None
        +clasificar_en(categoria Categoria, es_principal bool) None
        +categorias() tuple~ProductoCategoria~
        +categoria_principal() Categoria
        +exportar() str
    }
    class ProductoSimple {
        +precio_final(cantidad float) float
    }
    class ProductoPorPeso {
        +precio_final(cantidad float) float
    }
    class ProductoCombo {
        #_componentes list~Producto~
        #_descuento float
        +componentes() tuple~Producto~
        +precio_final(cantidad float) float
    }
    class ProductoDestacado {
        #_producto Producto
        #_orden_vidriera int
        +producto Producto
        +orden_vidriera int
    }
    class ProductoCategoria {
        #_categoria Categoria
        #_es_principal bool
        +categoria Categoria
        +es_principal bool
        #_marcar_principal(valor bool) None
    }
    class Categoria {
        #_nombre str
        #_descripcion str
        +nombre str
        +descripcion str
    }
    class UnidadMedida {
        <<frozen dataclass>>
        +nombre str
        +simbolo str
        +tipo str
    }
    class FichaPuntoDeVenta {
        <<libreria externa>>
        +exportar() str
    }

    Producto <|-- ProductoSimple
    Producto <|-- ProductoPorPeso
    Producto <|-- ProductoCombo
    Producto "1" *-- "1..*" ProductoCategoria : composición
    ProductoCombo "1" o-- "2..*" Producto : agregación
    Producto "0..*" --> "0..1" UnidadMedida : asociación
    ProductoCategoria "0..*" --> "1" Categoria
    ProductoDestacado "0..*" --> "1" Producto : asociación
    Producto ..|> Exportable : conformidad estructural
    FichaPuntoDeVenta ..|> Exportable : conformidad estructural
```

## ProductoDestacado: asociación, no herencia

`ProductoDestacado` no hereda de `Producto`. Destacar un producto es un rol
promocional temporal (entra y sale de la vidriera según convenga), no una
forma distinta de vender: no define ninguna regla propia de `precio_final`.
Modelarlo como herencia obligaría a decidir qué precio tendría un destacado
o a crear una subclase destacada por cada tipo de venta (simple, por peso,
combo), multiplicando clases sin necesidad.

Con la asociación `ProductoDestacado "0..*" --> "1" Producto`, cualquier
producto del catálogo puede destacarse agregando una instancia de
`ProductoDestacado` que lo referencia y guarda su `orden_vidriera`, sin tocar
la jerarquía de ventas.

**Costo de la restricción.** Como un destacado no es un `Producto`, no
responde a `precio_final()` ni cumple `Exportable`: para calcular o exportar
se usa `destacado.producto`. La vidriera es una colección aparte que se
mantiene junto al catálogo, y el modelo no impide órdenes repetidos ni que
un mismo producto se destaque dos veces. Se acepta ese costo a cambio de no
duplicar la jerarquía de ventas en variantes "destacadas".
