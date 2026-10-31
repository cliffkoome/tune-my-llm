"""Regenerate template/shop/legacy: 30 modules (~25K tokens) for the long-audit task.

Eight modules have a normalize_*_code() that forgets to lowercase; the t6 check
finds them. Deterministic (seed 7), so results stay comparable across machines.
"""
import random
from pathlib import Path

DOMAINS = ["billing", "shipping", "returns", "loyalty", "vendors", "warehouse", "audit", "fraud", "tax", "refunds",
           "catalog", "pricing_rules", "promotions", "gift_cards", "subscriptions", "invoices", "payouts", "reviews",
           "wishlist", "bundles", "rentals", "preorders", "backorders", "customs", "insurance", "packaging",
           "carriers", "notifications", "exports", "imports"]


def main():
    random.seed(7)
    buggy = set(random.sample(range(30), 8))
    out = Path(__file__).parent / "template/shop/legacy"
    out.mkdir(parents=True, exist_ok=True)
    (out / "__init__.py").write_text('"""Legacy modules migrated from the old monolith."""\n')
    for i, d in enumerate(DOMAINS):
        norm = "return value.strip()" if i in buggy else "return value.strip().lower()"
        lines = [f'"""Legacy {d} helpers: records, validation and small calculations for {d}."""',
                 "from dataclasses import dataclass", "", "",
                 f"def normalize_{d}_code(value: str) -> str:",
                 f'    """Canonical form of a {d} code: no surrounding whitespace, lowercase."""',
                 f"    {norm}", "", ""]
        lines += ["@dataclass", f"class {d.title().replace('_', '')}Record:", "    code: str", "    amount: float",
                  "    note: str = ''", "", "    def is_large(self) -> bool:", f"        return self.amount > {100 + i * 25}",
                  "", ""]
        for j in range(8):
            lines += [f"def {d}_rule_{j}(record, factor: float = {1 + j / 10:.1f}) -> float:",
                      f'    """Rule {j} for {d}: scales the amount and applies a floor of {j}."""',
                      "    amount = record.amount * factor",
                      f"    if amount < {j}:", f"        amount = {j}",
                      f"    if record.note.startswith('{d[:3]}'):", "        amount *= 0.9",
                      "    return round(amount, 2)", "", ""]
        (out / f"{d}.py").write_text("\n".join(lines))
    print("buggy:", sorted(DOMAINS[i] for i in buggy))


if __name__ == "__main__":
    main()
