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

  @OOS-07 @security
  Scenario: Un script digitado en el usuario se muestra como texto y nunca se ejecuta
    When Digita user "<script>window.__xss=1</script>" y password "secret_sauce"
    And Clickea en el boton de login
    Then Se muestra el mensaje de error "Username and password do not match"
    And El texto digitado se muestra como texto y no se ejecuta
    And El campo de usuario conserva "<script>window.__xss=1</script>"


  @OOS-03 @product-decision
  Scenario: Password solo de espacios muestra "do not match" y no "Password is required" (comportamiento actual)
    When Digita user "standard_user" y password "   "
    And Clickea en el boton de login
    Then Se muestra el mensaje de error "Username and password do not match"
    And El usuario permanece en la pagina de login
