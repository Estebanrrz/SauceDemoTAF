Feature: Ordenar productos
  Como usuario de saucedemo quiero ordenar los productos sin afectar mi carro

  Background: Usuario esta logeado
    Given El Usuario Abre saucedemo login page
    And   Digita user "standard_user" y password "secret_sauce"
    And Clickea en el boton de login


  @OOS-12
  Scenario: Precios iguales mantienen un orden estable por nombre
    When El Usuario ordena los productos por "Price (low to high)"
    Then Los productos estan ordenados por "Price (low to high)"
    And Los productos con el mismo precio se mantienen en orden por nombre

  @OOS-13
  Scenario Outline: Ordenar nunca cambia el contenido del carro
    When El Usuario Adiciona productos al carro de compras:
      | product               |
      | Sauce Labs Backpack   |
      | Sauce Labs Bike Light |
    And El Usuario ordena los productos por "<option>"
    Then El Contador del Carro de compras es '2'
    When El usuario Clickea en el Carro de Compras
    Then El carro de compras lista los productos en este orden:
      | product               |
      | Sauce Labs Backpack   |
      | Sauce Labs Bike Light |
    Examples:
      | option              |
      | Name (Z to A)       |
      | Price (low to high) |
      | Price (high to low) |
      | Name (A to Z)       |
