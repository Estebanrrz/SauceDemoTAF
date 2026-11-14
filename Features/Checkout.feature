Feature: Checkout
  Como usuario de saucedemo quiero que el checkout valide mis datos y sea consistente

  Background: Usuario esta logeado
    Given El Usuario Abre saucedemo login page
    And   Digita user "standard_user" y password "secret_sauce"
    And Clickea en el boton de login

  @OOS-04 @product-decision
  Scenario: Un codigo postal con formato invalido se acepta (comportamiento actual)
    Given El usuario esta en la pagina "checkout paso uno" con un producto en el carro
    When El Usuario completa nombre "FirstName" apellido "LastName" y codigo postal "not-a-zip!!"
    And El Usuario Clickea en Continue
    Then El usuario esta en el overview del checkout


  @OOS-20
  Scenario: Con todos los campos vacios solo se muestra el primer error
    Given El usuario esta en la pagina "checkout paso uno" con un producto en el carro
    When El Usuario no completa ningun dato del checkout
    And El Usuario Clickea en Continue
    Then El checkout muestra el error "First Name is required"
    And El checkout muestra un unico error

  @OOS-21
  Scenario: Los valores digitados se conservan despues de un error de validacion
    Given El usuario esta en la pagina "checkout paso uno" con un producto en el carro
    When El Usuario completa solo nombre "FirstName" y apellido "LastName"
    And El Usuario Clickea en Continue
    Then El checkout muestra el error "Postal Code is required"
    And Los campos del checkout conservan nombre "FirstName" y apellido "LastName"


  @OOS-23
  Scenario: Despues de una orden los botones vuelven a Add to cart y una segunda orden funciona
    Given El usuario esta en la pagina "checkout completo" con un producto en el carro
    When Usuario abre el Menu
    And El Usuario Clickea en All Items del menu
    Then Todos los botones de productos dicen "Add to cart"
    And El Carro de compras no muestra contador
    When El Usuario Adiciona productos al carro de compras:
      | product               |
      | Sauce Labs Bike Light |
    And El usuario Clickea en el Carro de Compras
    And El Usuario Clickea en checkout
    And El Usuario Digita "FirstName" "LastName" "Zipcode"
    And El Usuario Clickea en Continue
    And El Usuario Clickea en Finish
    Then Thank you for your order  aparece en la pagina
