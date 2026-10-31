"""Legacy bundles helpers: records, validation and small calculations for bundles."""
from dataclasses import dataclass


def normalize_bundles_code(value: str) -> str:
    """Canonical form of a bundles code: no surrounding whitespace, lowercase."""
    return value.strip().lower()


@dataclass
class BundlesRecord:
    code: str
    amount: float
    note: str = ''

    def is_large(self) -> bool:
        return self.amount > 575


def bundles_rule_0(record, factor: float = 1.0) -> float:
    """Rule 0 for bundles: scales the amount and applies a floor of 0."""
    amount = record.amount * factor
    if amount < 0:
        amount = 0
    if record.note.startswith('bun'):
        amount *= 0.9
    return round(amount, 2)


def bundles_rule_1(record, factor: float = 1.1) -> float:
    """Rule 1 for bundles: scales the amount and applies a floor of 1."""
    amount = record.amount * factor
    if amount < 1:
        amount = 1
    if record.note.startswith('bun'):
        amount *= 0.9
    return round(amount, 2)


def bundles_rule_2(record, factor: float = 1.2) -> float:
    """Rule 2 for bundles: scales the amount and applies a floor of 2."""
    amount = record.amount * factor
    if amount < 2:
        amount = 2
    if record.note.startswith('bun'):
        amount *= 0.9
    return round(amount, 2)


def bundles_rule_3(record, factor: float = 1.3) -> float:
    """Rule 3 for bundles: scales the amount and applies a floor of 3."""
    amount = record.amount * factor
    if amount < 3:
        amount = 3
    if record.note.startswith('bun'):
        amount *= 0.9
    return round(amount, 2)


def bundles_rule_4(record, factor: float = 1.4) -> float:
    """Rule 4 for bundles: scales the amount and applies a floor of 4."""
    amount = record.amount * factor
    if amount < 4:
        amount = 4
    if record.note.startswith('bun'):
        amount *= 0.9
    return round(amount, 2)


def bundles_rule_5(record, factor: float = 1.5) -> float:
    """Rule 5 for bundles: scales the amount and applies a floor of 5."""
    amount = record.amount * factor
    if amount < 5:
        amount = 5
    if record.note.startswith('bun'):
        amount *= 0.9
    return round(amount, 2)


def bundles_rule_6(record, factor: float = 1.6) -> float:
    """Rule 6 for bundles: scales the amount and applies a floor of 6."""
    amount = record.amount * factor
    if amount < 6:
        amount = 6
    if record.note.startswith('bun'):
        amount *= 0.9
    return round(amount, 2)


def bundles_rule_7(record, factor: float = 1.7) -> float:
    """Rule 7 for bundles: scales the amount and applies a floor of 7."""
    amount = record.amount * factor
    if amount < 7:
        amount = 7
    if record.note.startswith('bun'):
        amount *= 0.9
    return round(amount, 2)

