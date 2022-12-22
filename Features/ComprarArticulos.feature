Feature: Comprar uno o varios articulos
  Como usuario de saucedemo , quiero poder comprar uno o varios articulos

  Background: Usuario esta logeado
    Given El Usuario Abre saucedemo login page
    And   Digita user "standard_user" y password "secret_sauce"
    And Clickea en el boton de login

  Scenario: Compra Simple de un producto en saucedemo
    When El Usuario Adiciona productos al carro de compras:
    | product |
    | Sauce Labs Backpack |
    | Sauce Labs Bike Light |
    And El usuario Clickea en el Carro de Compras
    And El Usuario Clickea en checkout
    And El Usuario Digita "FirstName" "LastName" "Zipcode"
    And El Usuario Clickea en Continue
    And El Usuario Clickea en Finish
    Then Thank you for your order  aparece en la pagina


    Scenario: Verificar Numero en el carro de Compras
    When El Usuario Adiciona productos al carro de compras:
    | product |
    | Sauce Labs Backpack |
    | Sauce Labs Bike Light |
    Then El Contador del Carro de compras es '2'

    Scenario: Verificar el Total
    When El Usuario Adiciona productos al carro de compras:
    | product |
    | Sauce Labs Backpack |
    | Sauce Labs Bike Light |
    And El usuario Clickea en el Carro de Compras
    And El Usuario Clickea en checkout
    And El Usuario Digita "FirstName" "LastName" "Zipcode"
    And El Usuario Clickea en Continue
    And El Total es  'Total: $43.18'



