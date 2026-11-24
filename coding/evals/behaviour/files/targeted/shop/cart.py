class Cart:
    def __init__(self):
        self._lines = []

    def add(self, name, price, qty=1):
        self._lines.append((name, price, qty))

    def total(self):
        return round(sum(price for _, price, _ in self._lines), 2)
