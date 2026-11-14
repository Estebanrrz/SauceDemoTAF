Feature: Catalogo de productos
  Como usuario de saucedemo quiero ver los productos con su precio correcto

  Background: Usuario esta logeado con credenciales de la capa de datos
    Given El Usuario Abre saucedemo login page
    And Inicia sesion como "standard_user"

  @catalog
  Scenario: El inventario muestra el catalogo completo con sus precios
    Then El inventario muestra el catalogo de Data/products.json
