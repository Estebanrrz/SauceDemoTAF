# Steps for Login
from behave import *
from selenium import webdriver
from PageObjects.LoginPage import *
from PageObjects.InventoryPage import *


@step('El Usuario Abre saucedemo login page')
def AbrirPaginaLogin(context):
    url: str = context.url
    context.driver.get(url)


@step('Digita user "{user}" y password "{password}"')
def DigitarUsuarioContrasena(context, user, password):
    context.loginPage.setUserName(user)
    context.loginPage.setPassword(password)


@step('Clickea en el boton de login')
def ClickeaLoginButton(context):
    context.loginPage.clickLoginButton()
    context.InventoryPage = InventoryPage(context.driver)


@step('El usuario esta logeado')
def ElUsuarioEstaLogeado(context):
    url = context.driver.current_url
    assert "inventory" in url, "El Usuario no esta logeado"
