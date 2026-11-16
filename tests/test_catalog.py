# Catalog scenario
from Utilities.testData import TestData


class TestCatalog:
    def test_inventory_shows_the_catalog_with_prices(self, logged_in, pages):
        """El inventario muestra el catalogo completo con sus precios (Data/products.json)"""
        actual = pages.inventory.GetCatalog()
        expected = TestData.products()
        assert actual == expected, f'Expected catalog {expected}, got {actual}'
