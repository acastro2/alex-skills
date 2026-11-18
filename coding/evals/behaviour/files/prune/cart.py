class Cart:
    def __init__(self):
        self._items = []

    def add(self, name, price):
        self._items.append((name, price))

    def total(self, discount=0.0):
        subtotal = sum(price for _, price in self._items)
        return round(subtotal * (1 - discount), 2)
