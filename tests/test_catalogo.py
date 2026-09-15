"""Pruebas locales del catálogo (carpeta excluida del zip de entrega)."""

import dataclasses
import math
import unittest
from pathlib import Path

from catalogo import (
    Categoria,
    ErrorDominio,
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


class ErrorDominioTest(unittest.TestCase):
    def test_hereda_de_value_error(self) -> None:
        self.assertTrue(issubclass(ErrorDominio, ValueError))


class UnidadMedidaTest(unittest.TestCase):
    def test_se_construye_con_datos_validos(self) -> None:
        kg = UnidadMedida("kilogramo", "kg", "masa")
        self.assertEqual(kg.simbolo, "kg")

    def test_es_inmutable(self) -> None:
        kg = UnidadMedida("kilogramo", "kg", "masa")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            kg.simbolo = "g"

    def test_rechaza_campos_vacios(self) -> None:
        with self.assertRaises(ErrorDominio):
            UnidadMedida("", "kg", "masa")

    def test_es_comparable_y_hasheable(self) -> None:
        a = UnidadMedida("litro", "L", "volumen")
        b = UnidadMedida("litro", "L", "volumen")
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))


class CategoriaTest(unittest.TestCase):
    def test_descripcion_por_defecto_es_vacia(self) -> None:
        self.assertEqual(Categoria("Bebidas").descripcion, "")

    def test_guarda_la_descripcion_recibida(self) -> None:
        cat = Categoria("Bebidas", "Frías y calientes")
        self.assertEqual(cat.descripcion, "Frías y calientes")

    def test_properties_sin_setter(self) -> None:
        cat = Categoria("Bebidas")
        with self.assertRaises(AttributeError):
            cat.nombre = "X"
        with self.assertRaises(AttributeError):
            cat.descripcion = "X"

    def test_rechaza_nombre_vacio(self) -> None:
        with self.assertRaises(ErrorDominio):
            Categoria("   ")


class ProductoCategoriaTest(unittest.TestCase):
    def test_no_se_puede_crear_desde_afuera(self) -> None:
        with self.assertRaises(ErrorDominio):
            ProductoCategoria(Categoria("X"), True)

    def test_no_expone_setters(self) -> None:
        cat = Categoria("Bebidas")
        producto = ProductoSimple("Gaseosa", 1500, cat, stock_cantidad=1)
        vinculo = producto.categorias()[0]
        with self.assertRaises(AttributeError):
            vinculo.categoria = cat
        with self.assertRaises(AttributeError):
            vinculo.es_principal = False


class ProductoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bebidas = Categoria("Bebidas")
        self.kg = UnidadMedida("kilogramo", "kg", "masa")

    def test_es_abstracta(self) -> None:
        with self.assertRaises(TypeError):
            Producto("X", 1, self.bebidas)

    def test_valida_nombre_precio_y_stock(self) -> None:
        with self.assertRaises(ErrorDominio):
            ProductoSimple("", 1, self.bebidas)
        with self.assertRaises(ErrorDominio):
            ProductoSimple("X", -1, self.bebidas)
        with self.assertRaises(ErrorDominio):
            ProductoSimple("X", 1, self.bebidas, stock_cantidad=-1)

    def test_precio_publicado_sin_unidad(self) -> None:
        producto = ProductoSimple("X", 3, self.bebidas, stock_cantidad=1)
        self.assertEqual(producto.precio_publicado, "$ 3.00")

    def test_precio_publicado_con_unidad(self) -> None:
        producto = ProductoPorPeso(
            "X", 12.5, self.bebidas, stock_cantidad=1, unidad_venta=self.kg
        )
        self.assertEqual(producto.precio_publicado, "$ 12.50 / kg")

    def test_disponible_depende_de_habilitacion_y_stock(self) -> None:
        producto = ProductoSimple("X", 1, self.bebidas, stock_cantidad=1)
        self.assertTrue(producto.disponible)
        producto.deshabilitar()
        self.assertFalse(producto.disponible)
        producto.habilitar()
        self.assertTrue(producto.disponible)

        sin_stock = ProductoSimple("Y", 1, self.bebidas, stock_cantidad=0)
        self.assertFalse(sin_stock.disponible)

    def test_properties_sin_setter(self) -> None:
        producto = ProductoSimple("X", 1, self.bebidas, stock_cantidad=1)
        with self.assertRaises(AttributeError):
            producto.nombre = "Y"
        with self.assertRaises(AttributeError):
            producto.precio_base = 2
        with self.assertRaises(AttributeError):
            producto.disponible = True

    def test_sin_atributos_de_doble_guion_bajo(self) -> None:
        fuente = Path("catalogo.py").read_text(encoding="utf-8")
        self.assertNotIn("self.__", fuente)


class ClasificacionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bebidas = Categoria("Bebidas")
        self.ofertas = Categoria("Ofertas")
        self.producto = ProductoSimple("X", 1, self.bebidas, stock_cantidad=1)

    def test_construye_con_una_principal(self) -> None:
        vinculos = self.producto.categorias()
        self.assertEqual(len(vinculos), 1)
        self.assertTrue(vinculos[0].es_principal)

    def test_clasificar_en_no_devuelve_el_vinculo(self) -> None:
        self.assertIsNone(self.producto.clasificar_en(self.ofertas))

    def test_reasignar_principal_desmarca_la_anterior(self) -> None:
        nueva = Categoria("Nueva")
        self.producto.clasificar_en(nueva, es_principal=True)
        self.assertIs(self.producto.categoria_principal(), nueva)
        self.assertEqual(sum(v.es_principal for v in self.producto.categorias()), 1)

    def test_reclasificar_en_la_misma_categoria_falla(self) -> None:
        self.producto.clasificar_en(self.ofertas)
        with self.assertRaises(ErrorDominio):
            self.producto.clasificar_en(self.ofertas)

    def test_categorias_devuelve_copia_protegida(self) -> None:
        vinculos = self.producto.categorias()
        with self.assertRaises(AttributeError):
            vinculos.append("x")

    def test_clasificar_en_valida_tipos(self) -> None:
        with self.assertRaises(TypeError):
            self.producto.clasificar_en("Bebidas")


class ProductoSimpleTest(unittest.TestCase):
    def test_precio_final_multiplica_por_cantidad(self) -> None:
        cat = Categoria("Bebidas")
        gaseosa = ProductoSimple("Gaseosa", 1500, cat, stock_cantidad=10)
        self.assertEqual(gaseosa.precio_final(3), 4500.0)
        self.assertEqual(gaseosa.precio_final(3.0), 4500.0)

    def test_rechaza_cantidad_no_entera_o_menor_a_uno(self) -> None:
        cat = Categoria("Bebidas")
        gaseosa = ProductoSimple("Gaseosa", 1500, cat, stock_cantidad=10)
        with self.assertRaises(ErrorDominio):
            gaseosa.precio_final(2.5)
        with self.assertRaises(ErrorDominio):
            gaseosa.precio_final(0)


class ProductoPorPesoTest(unittest.TestCase):
    def test_precio_final_redondea_a_dos_decimales(self) -> None:
        cat = Categoria("Fiambrería")
        kg = UnidadMedida("kilogramo", "kg", "masa")
        jamon = ProductoPorPeso("Jamón", 9800, cat, stock_cantidad=5, unidad_venta=kg)
        self.assertEqual(jamon.precio_final(0.250), 2450.0)
        resultado = jamon.precio_final(0.333)
        self.assertEqual(resultado, round(resultado, 2))

    def test_rechaza_cantidad_no_positiva(self) -> None:
        cat = Categoria("Fiambrería")
        jamon = ProductoPorPeso("Jamón", 9800, cat, stock_cantidad=5)
        with self.assertRaises(ErrorDominio):
            jamon.precio_final(0)
        with self.assertRaises(ErrorDominio):
            jamon.precio_final(-1)


class ProductoComboTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = Categoria("Combos")
        self.galletitas = ProductoSimple("Galletitas", 1200, self.cat, stock_cantidad=10)
        self.jugo = ProductoSimple("Jugo", 800, self.cat, stock_cantidad=10)

    def test_precio_final_aplica_descuento_sobre_componentes(self) -> None:
        combo = ProductoCombo("Combo", [self.galletitas, self.jugo], 0.10, self.cat)
        self.assertTrue(math.isclose(combo.precio_final(1), 1800.0))
        self.assertTrue(math.isclose(combo.precio_final(2), 3600.0))
        self.assertEqual(combo.precio_publicado, "$ 1800.00")

    def test_requiere_al_menos_dos_componentes(self) -> None:
        with self.assertRaises(ErrorDominio):
            ProductoCombo("X", [self.galletitas], 0.1, self.cat)

    def test_valida_rango_del_descuento(self) -> None:
        with self.assertRaises(ErrorDominio):
            ProductoCombo("X", [self.galletitas, self.jugo], 1, self.cat)
        with self.assertRaises(ErrorDominio):
            ProductoCombo("X", [self.galletitas, self.jugo], -0.1, self.cat)
        ProductoCombo("X", [self.galletitas, self.jugo], 0, self.cat)

    def test_componente_debe_ser_producto(self) -> None:
        with self.assertRaises(TypeError):
            ProductoCombo("X", ["pan", self.jugo], 0.1, self.cat)

    def test_componentes_devuelve_copia_protegida(self) -> None:
        combo = ProductoCombo("Combo", [self.galletitas, self.jugo], 0.1, self.cat)
        with self.assertRaises(AttributeError):
            combo.componentes().append("x")

    def test_no_retiene_la_lista_original(self) -> None:
        lista = [self.galletitas, self.jugo]
        combo = ProductoCombo("Combo", lista, 0.1, self.cat)
        lista.append(ProductoSimple("Extra", 100, self.cat, stock_cantidad=1))
        self.assertEqual(len(combo.componentes()), 2)

    def test_precio_final_rechaza_cantidad_invalida(self) -> None:
        combo = ProductoCombo("Combo", [self.galletitas, self.jugo], 0.1, self.cat)
        with self.assertRaises(ErrorDominio):
            combo.precio_final(2.5)

    def test_combos_anidados(self) -> None:
        combo = ProductoCombo("Combo", [self.galletitas, self.jugo], 0.10, self.cat)
        gaseosa = ProductoSimple("Gaseosa", 1500, self.cat, stock_cantidad=10)
        mega = ProductoCombo("Mega", [combo, gaseosa], 0.05, self.cat)
        self.assertTrue(math.isclose(mega.precio_final(1), (1800 + 1500) * 0.95))

    def test_disponibilidad_depende_de_los_componentes(self) -> None:
        combo = ProductoCombo("Combo", [self.galletitas, self.jugo], 0.1, self.cat)
        self.assertTrue(combo.disponible)
        self.galletitas.deshabilitar()
        self.assertFalse(combo.disponible)
        self.galletitas.habilitar()
        self.assertTrue(combo.disponible)

    def test_componentes_sobreviven_al_combo(self) -> None:
        combo = ProductoCombo("Combo", [self.galletitas, self.jugo], 0.1, self.cat)
        del combo
        otro = ProductoCombo("Otro", [self.galletitas, self.jugo], 0.0, self.cat)
        self.assertGreater(otro.precio_final(1), 0)


class ProductoDestacadoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cat = Categoria("Bebidas")
        self.gaseosa = ProductoSimple("Gaseosa", 1500, self.cat, stock_cantidad=10)
        self.jamon = ProductoPorPeso("Jamón", 9800, self.cat, stock_cantidad=5)
        self.combo = ProductoCombo(
            "Combo",
            [self.gaseosa, self.jamon],
            0.1,
            self.cat,
        )

    def test_no_hereda_de_producto(self) -> None:
        self.assertFalse(issubclass(ProductoDestacado, Producto))

    def test_acepta_cualquier_tipo_de_producto(self) -> None:
        ProductoDestacado(self.gaseosa, 1)
        ProductoDestacado(self.jamon, 2)
        ProductoDestacado(self.combo, 3)

    def test_valida_orden_vidriera(self) -> None:
        with self.assertRaises(ErrorDominio):
            ProductoDestacado(self.gaseosa, 0)
        with self.assertRaises(TypeError):
            ProductoDestacado(self.gaseosa, True)
        with self.assertRaises(TypeError):
            ProductoDestacado(self.gaseosa, "1")

    def test_se_puede_ordenar_sin_isinstance(self) -> None:
        vidriera = [
            ProductoDestacado(self.combo, 3),
            ProductoDestacado(self.gaseosa, 1),
            ProductoDestacado(self.jamon, 2),
        ]
        ordenada = sorted(vidriera, key=lambda d: d.orden_vidriera)
        self.assertEqual([d.orden_vidriera for d in ordenada], [1, 2, 3])


class ExportableTest(unittest.TestCase):
    def test_exporta_productos_y_ficha_externa_juntos(self) -> None:
        cat = Categoria("Bebidas")
        gaseosa = ProductoSimple("Gaseosa", 1500, cat, stock_cantidad=10)
        jamon = ProductoPorPeso("Jamón", 9800, cat, stock_cantidad=5)
        combo = ProductoCombo("Combo", [gaseosa, jamon], 0.1, cat)
        ficha = FichaPuntoDeVenta("A1", "Pan")

        resultado = exportar_catalogo([gaseosa, jamon, combo, ficha])

        self.assertEqual(len(resultado), 4)
        self.assertEqual(resultado[-1], "POS|A1|Pan")

    def test_ninguna_clase_hereda_de_exportable(self) -> None:
        fuente = Path("catalogo.py").read_text(encoding="utf-8")
        self.assertNotIn("(Exportable)", fuente)
        self.assertNotIn(", Exportable)", fuente)

    def test_no_usa_isinstance_ni_ramas_por_tipo(self) -> None:
        fuente = Path("catalogo.py").read_text(encoding="utf-8")
        cuerpo = fuente.split("def exportar_catalogo")[1].split("\n\n")[0]
        self.assertNotIn("isinstance", cuerpo)
        self.assertNotIn("if ", cuerpo)


if __name__ == "__main__":
    unittest.main()
