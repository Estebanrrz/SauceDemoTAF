# Steps for navigation, menu and session
from behave import *
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait

from PageObjects.CheckOutStepOnePage import CheckOutStepOnePage
from PageObjects.CheckoutCompletePage import CheckoutCompletePage
from PageObjects.OverviewPage import OverviewPage
from PageObjects.ShoppingCartPage import ShoppingCartPage

from Utilities.testData import TestData

PRODUCT = TestData.productNames()[0]


@given(u'El usuario esta en la pagina "{page}" con un producto en el carro')
def NavegarAPagina(context, page):
    """Walk the real UI up to the requested page (no URL shortcuts)."""
    context.InventoryPage.AddtoCartItem(PRODUCT)
    if page == "productos":
        return
    context.InventoryPage.ClickShoppingCartButton()
    context.ShoppingCartPage = ShoppingCartPage(context.driver)
    if page == "carrito":
        return
    context.ShoppingCartPage.ClickButtonCheckout()
    context.CheckOutStepOnePage = CheckOutStepOnePage(context.driver)
    if page == "checkout paso uno":
        return
    customer = TestData.customer()
    context.CheckOutStepOnePage.SetValueOnFirstName(customer['firstName'])
    context.CheckOutStepOnePage.SetValueOnLastName(customer['lastName'])
    context.CheckOutStepOnePage.SetValueOnZipCode(customer['postalCode'])
    context.CheckOutStepOnePage.ClickOnContinueButton()
    context.OverviewPage = OverviewPage(context.driver)
    if page == "checkout overview":
        return
    context.OverviewPage.ClickFinishButton()
    context.CheckoutCompletePage = CheckoutCompletePage(context.driver)
    assert page == "checkout completo", f"Pagina desconocida: {page}"


@when(u'El Usuario Clickea en All Items del menu')
def ClickAllItems(context):
    context.Menu.ClickAllItems()


@when(u'El Usuario cierra el menu')
def CerrarMenu(context):
    context.Menu.Close()


@then(u'El menu esta cerrado')
def MenuCerrado(context):
    # The menu closes with a CSS transition: poll instead of reading the state once.
    try:
        WebDriverWait(context.driver, 10).until(lambda d: context.Menu.IsOpen() is False)
    except TimeoutException:
        raise AssertionError("El menu sigue abierto")


@when(u'El Usuario recarga la pagina')
def Recargar(context):
    context.driver.refresh()


@when(u'El Usuario abre la url relativa "{path}"')
def AbrirUrlRelativa(context, path):
    context.driver.get(context.url + path)


@when(u'El Usuario abre una nueva pestana en la pagina de productos')
def NuevaPestana(context):
    context.driver.switch_to.new_window('tab')
    context.driver.get(context.url + "inventory.html")
