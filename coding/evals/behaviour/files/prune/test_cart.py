import os

from cart import Cart


def test_total_sums_items():
    cart = Cart()
    cart.add("book", 10.0)
    cart.add("pen", 2.5)
    assert cart.total() == 12.5


def test_add_stores_item():
    cart = Cart()
    cart.add("book", 10.0)
    assert len(cart._items) == 1


def test_discount_applies():
    cart = Cart()
    cart.add("book", 100.0)
    price = 100.0
    assert cart.total(discount=0.2) == price - price * 0.2


def test_legacy_pricing_module_is_gone():
    assert not os.path.exists("legacy_pricing.py")


def test_total_of_two_items():
    cart = Cart()
    cart.add("a", 1.0)
    cart.add("b", 2.0)
    assert cart.total() == 3.0
