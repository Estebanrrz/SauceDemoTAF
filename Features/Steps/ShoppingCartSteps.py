# Steps for Shoppingcart
from behave import *
from PageObjects.CheckOutStepOnePage import *
from PageObjects.CheckoutCompletePage import CheckoutCompletePage
from PageObjects.OverviewPage import OverviewPage


@when('El Usuario Clickea en checkout')
def ClickOnCheckOut(context):
    context.ShoppingCartPage.ClickButtonCheckout()
    context.CheckOutStepOnePage = CheckOutStepOnePage(context.driver)


@when(u'El Usuario Digita {firstName} {lastName} {zipcode}')
def UsuarioDigitaFirstNameLastNameZipCode(context, firstName, lastName, zipcode):
    context.CheckOutStepOnePage.SetValueOnFirstName(firstName)
    context.CheckOutStepOnePage.SetValueOnLastName(lastName)
    context.CheckOutStepOnePage.SetValueOnZipCode(zipcode)


@then(u'Thank you for your order  aparece en la pagina')
def ThankYouApareceEnlaPagina(context):
    assert context.CheckoutCompletePage.ThankYouForYourOrderIsDisplayed() is True


@when('El Usuario Clickea en Continue')
def ClickOnContinue(context):
    context.CheckOutStepOnePage.ClickOnContinueButton()
    context.OverviewPage = OverviewPage(context.driver)


@when('El Usuario Clickea en Finish')
def ClickOnCheckContinue(context):
    context.OverviewPage.ClickFinishButton()
    context.CheckoutCompletePage = CheckoutCompletePage(context.driver)


@when(u'El Total es  {total}')
def VerifyTotalInOverview(context, total):
    assert context.OverviewPage.GetTotal() == total.strip('\''), "El total no es el esperado"


# ---- Cart ----
@when(u'El usuario Clickea en Continue Shopping')
def ClickContinueShopping(context):
    context.ShoppingCartPage.ClickContinueShopping()


@then(u'El carro de compras lista los productos en este orden')
@then(u'El carro de compras lista los productos en este orden:')
def CarroListaEnOrden(context):
    expected = [row['product'] for row in context.table]
    actual = context.ShoppingCartPage.GetItemNames()
    assert actual == expected, f"Esperado {expected}, real {actual}"


@then(u'El carro de compras esta vacio')
def CarroVacio(context):
    assert context.ShoppingCartPage.GetItemNames() == [], "El carro no esta vacio"


# ---- Checkout step one ----
@when(u'El Usuario completa solo nombre "{firstName}" y apellido "{lastName}"')
def CompletaNombreYApellido(context, firstName, lastName):
    context.CheckOutStepOnePage.SetValueOnFirstName(firstName)
    context.CheckOutStepOnePage.SetValueOnLastName(lastName)


@when(u'El Usuario completa nombre "{firstName}" apellido "{lastName}" y codigo postal "{zipcode}"')
def CompletaTodosLosDatos(context, firstName, lastName, zipcode):
    context.CheckOutStepOnePage.SetValueOnFirstName(firstName)
    context.CheckOutStepOnePage.SetValueOnLastName(lastName)
    context.CheckOutStepOnePage.SetValueOnZipCode(zipcode)


@when(u'El Usuario completa solo apellido "{lastName}" y codigo postal "{zipcode}"')
def CompletaApellidoYCodigo(context, lastName, zipcode):
    context.CheckOutStepOnePage.SetValueOnLastName(lastName)
    context.CheckOutStepOnePage.SetValueOnZipCode(zipcode)


@when(u'El Usuario no completa ningun dato del checkout')
def NoCompletaNada(context):
    pass


@when(u'El Usuario abre directamente la pagina del overview')
def AbrirOverviewDirecto(context):
    context.driver.get(context.url + "checkout-step-two.html")


@then(u'Los campos del checkout conservan nombre "{firstName}" y apellido "{lastName}"')
def CamposConservanValores(context, firstName, lastName):
    first, last, _ = context.CheckOutStepOnePage.GetFieldValues()
    assert (first, last) == (firstName, lastName), f"Valores: {first!r}, {last!r}"


@then(u'El checkout muestra el error "{message}"')
def CheckoutMuestraError(context, message):
    actual = context.CheckOutStepOnePage.GetErrorMessage()
    assert message in actual, f"Error esperado '{message}', real '{actual}'"


@then(u'El checkout muestra un unico error')
def CheckoutUnicoError(context):
    context.CheckOutStepOnePage.GetErrorMessage()  # waits for it
    assert len(context.CheckOutStepOnePage.find_elements_by_Xpath('//*[@data-test="error"]')) == 1


@then(u'El usuario esta en el paso uno del checkout')
def EstaEnCheckoutUno(context):
    assert "checkout-step-one.html" in context.driver.current_url, context.driver.current_url


@then(u'El usuario esta en el overview del checkout')
def EstaEnOverview(context):
    assert "checkout-step-two.html" in context.driver.current_url, context.driver.current_url


@then(u'El usuario esta en el carro de compras')
def EstaEnCarro(context):
    assert "cart.html" in context.driver.current_url, context.driver.current_url


# ---- Finish twice (OOS-24) ----
@when(u'El Usuario regresa con el boton atras del navegador')
def BotonAtras(context):
    context.driver.back()
    context.OverviewPage = OverviewPage(context.driver)


@then(u'El segundo Finish no crea otra orden y el carro muestra un error')
def SegundoFinishRechazado(context):
    assert "cart.html" in context.driver.current_url, \
        f"Se esperaba volver al carro, URL real: {context.driver.current_url}"
    assert context.ShoppingCartPage.GetErrorMessage(), "El carro no muestra el error de carro vacio"
