from .models import Order

COUPONS = {
    "SAVE10": 0.10,
    "SAVE25": 0.25,
}

TAX_RATE = 0.16


def calc_total(order: Order) -> float:
    """Subtotal minus coupon discount, plus tax, rounded to cents."""
    subtotal = sum(item.subtotal() for item in order.items)
    discount = COUPONS.get(order.coupon, 0) if order.coupon else 0
    # BUG: discount is applied as a flat amount instead of a percentage.
    discounted = subtotal - discount
    return round(discounted * (1 + TAX_RATE), 2)


def bulk_discount(quantity: int) -> float:
    """Fraction off for buying many of one item."""
    if quantity >= 100:
        return 0.15
    if quantity >= 20:
        return 0.05
    return 0.0
