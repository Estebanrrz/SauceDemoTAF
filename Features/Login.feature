Feature: Login Usuario
  Como usuario de saucedemo quiero poder logearme y deslogearme de la pagina


  Background: Inicializar la prueba
  Given El Usuario Abre saucedemo login page


  Scenario Outline: Usuario se Logea
    When Digita user "<username>" y password "secret_sauce"
    And Clickea en el boton de login
    Then El usuario esta logeado
    Examples:
      | username |
      | standard_user|
      | problem_user |

  Scenario Outline: Usuario se deslogea
    When Digita user "<username>" y password "secret_sauce"
    And Clickea en el boton de login
    And El usuario esta logeado
    And Usuario abre el Menu
    And Usuario Clickea Logout
    Then Usuario Esta Deslogeado
    Examples:
      | username |
      | standard_user|
      | problem_user |