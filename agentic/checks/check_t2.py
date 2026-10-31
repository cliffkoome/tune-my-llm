from shop.inventory import Inventory
from shop.models import Product


def test_search_by_tag():
    inv = Inventory()
    inv.add(Product("B", "b", 1, 1, ["x", "y"]))
    inv.add(Product("A", "a", 1, 1, ["x"]))
    inv.add(Product("C", "c", 1, 1, ["z"]))
    assert [p.sku for p in inv.search("x")] == ["A", "B"]
    assert inv.search("missing") == []
