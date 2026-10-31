import sys

from .inventory import Inventory
from .models import Product
from .orders import OrderService
from .report import revenue_by_customer


def demo_service() -> OrderService:
    inv = Inventory()
    inv.add(Product("A1", "Apple", 0.5, 100, ["fruit"]))
    inv.add(Product("B2", "Bread", 2.0, 20, ["bakery"]))
    inv.add(Product("C3", "Cheese", 7.5, 3, ["dairy"]))
    svc = OrderService(inv)
    svc.place("o1", "alice", {"A1": 10, "B2": 1})
    svc.place("o2", "bob", {"C3": 1}, coupon="SAVE10")
    svc.place("o3", "alice", {"B2": 2})
    return svc


def main(argv: list[str]) -> int:
    if argv[1:] == ["report"]:
        for customer, total in sorted(revenue_by_customer(demo_service()).items()):
            print(f"{customer}: {total:.2f}")
        return 0
    print("usage: python -m shop.cli report")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
