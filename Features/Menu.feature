Feature: Menu lateral, logout y sesion
  Como usuario de saucedemo quiero usar el menu lateral desde cualquier pagina

  Background: Usuario esta logeado
    Given El Usuario Abre saucedemo login page
    And   Digita user "standard_user" y password "secret_sauce"
    And Clickea en el boton de login

  @OOS-08
  Scenario Outline: Logout desde cualquier pagina
    Given El usuario esta en la pagina "<page>" con un producto en el carro
    When Usuario abre el Menu
    And Usuario Clickea Logout
    Then Usuario Esta Deslogeado
    Examples:
      | page              |
      | productos         |
      | carrito           |
      | checkout paso uno |
      | checkout overview |
      | checkout completo |

  @OOS-09
  Scenario: All Items lleva a la pagina de productos desde el carro
    Given El usuario esta en la pagina "carrito" con un producto en el carro
    When Usuario abre el Menu
    And El Usuario Clickea en All Items del menu
    Then El usuario esta en la pagina de productos

  @OOS-09
  Scenario: Close Menu cierra el menu sin cambiar de pagina
    When Usuario abre el Menu
    And El Usuario cierra el menu
    Then El menu esta cerrado
    And El usuario esta en la pagina de productos

  @OOS-10
  Scenario: Una segunda pestana comparte la sesion y el carro
    When El Usuario Adiciona productos al carro de compras:
      | product             |
      | Sauce Labs Backpack |
    And El Usuario abre una nueva pestana en la pagina de productos
    Then El usuario esta en la pagina de productos
    And El Contador del Carro de compras es '1'
