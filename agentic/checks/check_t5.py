import pytest

from shop.inventory import Inventory
from shop.models import Product
from shop.orders import OrderService


def test_cancel_restocks_and_removes():
    inv = Inventory()
    inv.add(Product("A", "a", 1.0, 10))
    svc = OrderService(inv)
    svc.place("o1", "c", {"A": 4})
    svc.cancel("o1")
    assert inv.get("A").stock == 10
    assert "o1" not in svc.orders


def test_cancel_unknown():
    with pytest.raises(KeyError):
        OrderService(Inventory()).cancel("nope")
