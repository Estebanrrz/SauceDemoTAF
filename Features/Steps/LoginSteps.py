# Steps for Login
from behave import *
from selenium.common.exceptions import NoAlertPresentException

from PageObjects.InventoryPage import *
from Utilities.testData import TestData


@step('El Usuario Abre saucedemo login page')
def AbrirPaginaLogin(context):
    url: str = context.url
    context.driver.get(url)


@step('Digita user "{user}" y password "{password}"')
def DigitarUsuarioContrasena(context, user, password):
    context.loginPage.setUserName(user)
    context.loginPage.setPassword(password)


@step('Inicia sesion como "{user}"')
def IniciarSesionComo(context, user):
    # Password comes from Data/users.json, so features never carry credentials
    context.loginPage.setUserName(user)
    context.loginPage.setPassword(TestData.password(user))
    context.loginPage.clickLoginButton()
    context.InventoryPage = InventoryPage(context.driver)


@step('Clickea en el boton de login')
def ClickeaLoginButton(context):
    context.loginPage.clickLoginButton()
    context.InventoryPage = InventoryPage(context.driver)


@step('El usuario esta logeado')
def ElUsuarioEstaLogeado(context):
    url = context.driver.current_url
    assert "inventory" in url, "El Usuario no esta logeado"


@then('Se muestra el mensaje de error "{message}"')
def SeMuestraMensajeDeError(context, message):
    actual = context.loginPage.GetErrorMessage()
    assert message in actual, f"Error esperado '{message}', real '{actual}'"


@then('El usuario permanece en la pagina de login')
def PermaneceEnLogin(context):
    assert context.driver.current_url == context.url, "El usuario salio de la pagina de login"


@then('El campo de usuario conserva "{user}"')
def CampoUsuarioConservaValor(context, user):
    assert context.loginPage.getUserNameValue() == user


@then('El campo de password esta vacio')
def CampoPasswordVacio(context):
    assert context.loginPage.getPasswordValue() == "", "El password no se limpio"


@then('El texto digitado se muestra como texto y no se ejecuta')
def TextoNoSeEjecuta(context):
    try:
        alert = context.driver.switch_to.alert
        alert.dismiss()
        raise AssertionError("Se ejecuto codigo: aparecio un alert")
    except NoAlertPresentException:
        pass
    assert context.driver.execute_script("return window.__xss === undefined"), "Se ejecuto el script digitado"
