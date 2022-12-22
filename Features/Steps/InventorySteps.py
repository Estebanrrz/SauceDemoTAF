# Steps for Inventory
from behave import *

from PageObjects.ShoppingCartPage import *


@when('Usuario abre el Menu')
def UsuarioAbreBurguerMenu(context):
    context.InventoryPage.OpenBurguerMenu()


@when('Usuario Clickea Logout')
def UsuarioClickeaLogout(context):
    context.InventoryPage.ClickLogout()


@then('Usuario Esta Deslogeado')
def UsuarioEstaDeslogeado(context):
    url = context.driver.current_url
    assert "https://www.saucedemo.com/" == url, "El usuario no esta  deslogeado"


@when(u'El Usuario Adiciona productos al carro de compras')
def AdicionarItemsCarroCompras(context):
    for row in context.table:
        context.InventoryPage.AddtoCartItem(row['product'])


@when(u'El usuario Clickea en el Carro de Compras')
def UsuarioClickeaEnElCarroDeCompras(context):
    context.InventoryPage.ClickShoppingCartButton()
    context.ShoppingCartPage = ShoppingCartPage(context.driver)


@then(u'El Contador del Carro de compras es {count}')
def VerificaContadorEnEIconoDelCarroDeCompras(context, count):
    assert context.InventoryPage.GetCounterShoppincart() == count.strip(
        '\''), "Contador en el carrito de compras no es el esperado"
