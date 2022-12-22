#Hooks
from selenium import webdriver
from PageObjects.LoginPage import *
from Utilities.readProperties import *


# before scenario
def before_scenario(context, scenario):
    context.driver = webdriver.Chrome(executable_path='../../Drivers/chromedriver.exe')
    context.driver.implicitly_wait(3)
    context.driver.maximize_window()
    context.loginPage = LoginPage(context.driver)
    context.url = ReadConfig.getApplicationUrl()


# After Scenario
def after_scenario(context, scenario):
    context.driver.close()
