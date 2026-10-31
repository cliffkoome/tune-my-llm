from .models import Product


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self):
        self._products: dict[str, Product] = {}

    def add(self, product: Product) -> None:
        if product.sku in self._products:
            raise ValueError(f"duplicate sku {product.sku}")
        self._products[product.sku] = product

    def get(self, sku: str) -> Product:
        return self._products[sku]

    def restock(self, sku: str, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._products[sku].stock += amount

    def take(self, sku: str, amount: int) -> None:
        product = self._products[sku]
        if product.stock < amount:
            raise OutOfStock(sku)
        product.stock -= amount

    def all(self) -> list[Product]:
        return list(self._products.values())
