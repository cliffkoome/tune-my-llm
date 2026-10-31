from .orders import OrderService
from .pricing import calc_total


def revenue_by_customer(service: OrderService) -> dict[str, float]:
    revenue: dict[str, float] = {}
    for order in service.orders.values():
        revenue[order.customer] += calc_total(order)
    return revenue


def low_stock(service: OrderService, threshold: int = 5) -> list[str]:
    return sorted(p.sku for p in service.inventory.all() if p.stock < threshold)
