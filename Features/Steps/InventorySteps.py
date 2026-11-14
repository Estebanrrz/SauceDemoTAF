# Steps for Inventory
from behave import *
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from PageObjects.ShoppingCartPage import *

SORT_KEY = {
    'Name (A to Z)': (lambda names, prices: names == sorted(names)),
    'Name (Z to A)': (lambda names, prices: names == sorted(names, reverse=True)),
    'Price (low to high)': (lambda names, prices: prices == sorted(prices)),
    'Price (high to low)': (lambda names, prices: prices == sorted(prices, reverse=True)),
}


@when('Usuario abre el Menu')
def UsuarioAbreBurguerMenu(context):
    context.Menu.Open()


@when('Usuario Clickea Logout')
def UsuarioClickeaLogout(context):
    context.Menu.ClickLogout()


@then('Usuario Esta Deslogeado')
def UsuarioEstaDeslogeado(context):
    try:
        WebDriverWait(context.driver, 10).until(EC.url_to_be(context.url))
    except TimeoutException:
        raise AssertionError(f"El usuario no esta deslogeado, URL actual: {context.driver.current_url}")


@when(u'El Usuario Adiciona productos al carro de compras')
@when(u'El Usuario Adiciona productos al carro de compras:')  # behave >= 1.3 keeps the trailing colon
def AdicionarItemsCarroCompras(context):
    for row in context.table:
        context.InventoryPage.AddtoCartItem(row['product'])


@when(u'El Usuario remueve el producto "{product}"')
def RemoverProducto(context, product):
    assert context.InventoryPage.GetItemButtonText(product) == "Remove", "El producto no estaba en el carro"
    context.InventoryPage.AddtoCartItem(product)  # the same button toggles Add/Remove


@when(u'El Usuario adiciona todos los productos')
def AdicionarTodosLosProductos(context):
    context.added = context.InventoryPage.ClickAllButtonsWithText("Add to cart")
    assert context.added > 0, "No habia productos para adicionar"


@when(u'El Usuario remueve todos los productos desde el inventario')
def RemoverTodosLosProductos(context):
    context.InventoryPage.ClickAllButtonsWithText("Remove")


@when(u'El usuario Clickea en el Carro de Compras')
def UsuarioClickeaEnElCarroDeCompras(context):
    context.InventoryPage.ClickShoppingCartButton()
    context.ShoppingCartPage = ShoppingCartPage(context.driver)


@when(u'El Usuario ordena los productos por "{option}"')
def OrdenarProductos(context, option):
    context.InventoryPage.SortBy(option)


@then(u'El Contador del Carro de compras es {count}')
def VerificaContadorEnEIconoDelCarroDeCompras(context, count):
    assert context.InventoryPage.GetCounterShoppincart() == count.strip(
        '\''), "Contador en el carrito de compras no es el esperado"


@then(u'El Carro de compras no muestra contador')
def CarroSinContador(context):
    assert not context.InventoryPage.IsCartBadgeDisplayed(), "El contador del carro sigue visible"


@then(u'Los productos estan ordenados por "{option}"')
def ProductosOrdenados(context, option):
    names = context.InventoryPage.GetItemNames()
    prices = context.InventoryPage.GetItemPrices()
    assert SORT_KEY[option](names, prices), f"Orden inesperado para {option}: {list(zip(names, prices))}"


@then(u'Los productos con el mismo precio se mantienen en orden por nombre')
def MismoPrecioOrdenPorNombre(context):
    pairs = list(zip(context.InventoryPage.GetItemPrices(), context.InventoryPage.GetItemNames()))
    assert pairs == sorted(pairs, key=lambda p: p[0]) and \
           all(a[1] <= b[1] for a, b in zip(pairs, pairs[1:]) if a[0] == b[0]), \
        f"Orden inestable entre precios iguales: {pairs}"


@then(u'Todos los botones de productos dicen "{text}"')
def TodosLosBotonesDicen(context, text):
    texts = context.InventoryPage.GetButtonTexts()
    assert texts and all(t == text for t in texts), f"Botones: {texts}"


@then(u'El inventario muestra el catalogo de Data/products.json')
def InventarioMuestraElCatalogo(context):
    from Utilities.testData import TestData
    actual = context.InventoryPage.GetCatalog()
    assert actual == TestData.products(), f"Catalogo esperado {TestData.products()}, real {actual}"


@then(u'El usuario esta en la pagina de productos')
def EstaEnProductos(context):
    assert "inventory.html" in context.driver.current_url, "No esta en la pagina de productos"
    assert context.InventoryPage.GetItemNames(), "La pagina de productos no lista productos"


@then(u'El producto "{product}" muestra el boton "{text}"')
def ProductoMuestraBoton(context, product, text):
    assert context.InventoryPage.GetItemButtonText(product) == text
