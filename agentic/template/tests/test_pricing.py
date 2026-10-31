from shop.models import LineItem, Order, Product
from shop.pricing import bulk_discount, calc_total


def order(coupon=None):
    return Order("o", "c", [LineItem(Product("X", "X", 10.0), 2)], coupon)


def test_total_without_coupon():
    assert calc_total(order()) == 23.2


def test_total_with_percentage_coupon():
    # 20.00 minus 10% = 18.00, plus 16% tax = 20.88
    assert calc_total(order("SAVE10")) == 20.88


def test_bulk_discount():
    assert bulk_discount(1) == 0
    assert bulk_discount(20) == 0.05
    assert bulk_discount(100) == 0.15
