# Cart scenarios


class TestCart:
    def test_oos14_add_all_products_then_remove_them(self, logged_in, pages):
        """OOS-14: adicionar los 6 productos y removerlos todos"""
        added = pages.inventory.ClickAllButtonsWithText('Add to cart')
        assert added > 0, 'There were no products to add'
        assert pages.inventory.GetCounterShoppincart() == '6', 'The cart counter is not the expected one'
        pages.inventory.ClickAllButtonsWithText('Remove')
        assert not pages.inventory.IsCartBadgeDisplayed(), 'The cart counter is still visible'
        pages.inventory.ClickShoppingCartButton()
        assert pages.cart.GetItemNames() == [], 'The cart is not empty'

    def test_oos15_cart_survives_a_reload(self, logged_in, pages, engine):
        """OOS-15: el carro sobrevive a recargar la pagina"""
        pages.inventory.AddtoCartItem('Sauce Labs Backpack')
        pages.inventory.AddtoCartItem('Sauce Labs Bike Light')
        engine.reload()
        assert pages.inventory.GetCounterShoppincart() == '2', 'The cart counter is not the expected one'
        assert pages.inventory.GetItemButtonText('Sauce Labs Backpack') == 'Remove'

    def test_oos16_cart_keeps_the_order_products_were_added(self, logged_in, pages):
        """OOS-16: el carro lista los productos en el orden en que se adicionaron"""
        added = ['Sauce Labs Onesie', 'Sauce Labs Backpack', 'Sauce Labs Bike Light']
        for product in added:
            pages.inventory.AddtoCartItem(product)
        pages.inventory.ClickShoppingCartButton()
        actual = pages.cart.GetItemNames()
        assert actual == added, f'Expected {added}, got {actual}'

    def test_oos17_continue_shopping_keeps_the_cart(self, logged_in, pages, engine):
        """OOS-17: Continue Shopping vuelve a productos con el carro sin cambios"""
        pages.inventory.AddtoCartItem('Sauce Labs Backpack')
        pages.inventory.ClickShoppingCartButton()
        pages.cart.ClickContinueShopping()
        engine.wait_until(lambda: 'inventory.html' in engine.current_url, 'Not on the products page',
                          label='check the products page is shown')
        assert pages.inventory.GetItemNames(), 'The products page lists no products'
        assert pages.inventory.GetCounterShoppincart() == '1', 'The cart counter is not the expected one'
        assert pages.inventory.GetItemButtonText('Sauce Labs Backpack') == 'Remove'

    # ---- new scenario ----
    def test_remove_a_product_from_the_cart_page(self, logged_in, pages):
        """Quitar un producto desde la pagina del carro: desaparece de la lista y baja el contador"""
        pages.inventory.AddtoCartItem('Sauce Labs Backpack')
        pages.inventory.AddtoCartItem('Sauce Labs Bike Light')
        pages.inventory.ClickShoppingCartButton()
        pages.cart.RemoveItem('Sauce Labs Backpack')
        actual = pages.cart.GetItemNames()
        assert actual == ['Sauce Labs Bike Light'], f'Unexpected cart content: {actual}'
        assert pages.inventory.GetCounterShoppincart() == '1', 'The cart counter is not the expected one'
