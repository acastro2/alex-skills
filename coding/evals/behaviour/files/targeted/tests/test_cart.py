from shop.cart import Cart


def test_total_sums_lines():
    cart = Cart()
    cart.add("pen", 2.0)
    cart.add("book", 10.0)
    assert cart.total() == 12.0


def test_total_counts_quantity():
    cart = Cart()
    cart.add("pen", 2.0, qty=3)
    assert cart.total() == 6.0
