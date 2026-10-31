from .inventory import Inventory
from .models import LineItem, Order
from .pricing import calc_total


class OrderService:
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self.orders: dict[str, Order] = {}

    def place(self, order_id: str, customer: str, lines: dict[str, int], coupon=None) -> Order:
        items = []
        for sku, qty in lines.items():
            self.inventory.take(sku, qty)
            items.append(LineItem(self.inventory.get(sku), qty))
        order = Order(order_id, customer, items, coupon)
        self.orders[order_id] = order
        return order

    def total(self, order_id: str) -> float:
        return calc_total(self.orders[order_id])
