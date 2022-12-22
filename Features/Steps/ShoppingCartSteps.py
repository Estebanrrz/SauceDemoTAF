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
