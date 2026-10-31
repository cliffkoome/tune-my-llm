from dataclasses import dataclass, field


@dataclass
class Product:
    sku: str
    name: str
    price: float
    stock: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class LineItem:
    product: Product
    quantity: int

    def subtotal(self) -> float:
        return self.product.price * self.quantity


@dataclass
class Order:
    order_id: str
    customer: str
    items: list[LineItem] = field(default_factory=list)
    coupon: str | None = None
