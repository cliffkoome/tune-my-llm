import pytest

from shop.inventory import Inventory, OutOfStock
from shop.models import Product


def make():
    inv = Inventory()
    inv.add(Product("A1", "Apple", 0.5, 10))
    return inv


def test_take_reduces_stock():
    inv = make()
    inv.take("A1", 3)
    assert inv.get("A1").stock == 7


def test_take_too_many():
    with pytest.raises(OutOfStock):
        make().take("A1", 11)


def test_duplicate_sku():
    with pytest.raises(ValueError):
        make().add(Product("A1", "Apple", 0.5))
