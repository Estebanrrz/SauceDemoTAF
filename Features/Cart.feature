Feature: Carro de compras
  Como usuario de saucedemo quiero que mi carro sea consistente

  Background: Usuario esta logeado
    Given El Usuario Abre saucedemo login page
    And   Digita user "standard_user" y password "secret_sauce"
    And Clickea en el boton de login

  @OOS-14
  Scenario: Adicionar los 6 productos y removerlos todos
    When El Usuario adiciona todos los productos
    Then El Contador del Carro de compras es '6'
    When El Usuario remueve todos los productos desde el inventario
    Then El Carro de compras no muestra contador
    When El usuario Clickea en el Carro de Compras
    Then El carro de compras esta vacio

  @OOS-15
  Scenario: El carro sobrevive a recargar la pagina
    When El Usuario Adiciona productos al carro de compras:
      | product               |
      | Sauce Labs Backpack   |
      | Sauce Labs Bike Light |
    And El Usuario recarga la pagina
    Then El Contador del Carro de compras es '2'
    And El producto "Sauce Labs Backpack" muestra el boton "Remove"

  @OOS-16
  Scenario: El carro lista los productos en el orden en que se adicionaron
    When El Usuario Adiciona productos al carro de compras:
      | product               |
      | Sauce Labs Onesie     |
      | Sauce Labs Backpack   |
      | Sauce Labs Bike Light |
    And El usuario Clickea en el Carro de Compras
    Then El carro de compras lista los productos en este orden:
      | product               |
      | Sauce Labs Onesie     |
      | Sauce Labs Backpack   |
      | Sauce Labs Bike Light |

  @OOS-17
  Scenario: Continue Shopping vuelve a productos con el carro sin cambios
    When El Usuario Adiciona productos al carro de compras:
      | product             |
      | Sauce Labs Backpack |
    And El usuario Clickea en el Carro de Compras
    And El usuario Clickea en Continue Shopping
    Then El usuario esta en la pagina de productos
    And El Contador del Carro de compras es '1'
    And El producto "Sauce Labs Backpack" muestra el boton "Remove"
