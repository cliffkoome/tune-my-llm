import importlib
import pkgutil
from pathlib import Path

import shop.legacy


def test_every_normalize_lowercases():
    for m in pkgutil.iter_modules(shop.legacy.__path__):
        mod = importlib.import_module(f"shop.legacy.{m.name}")
        fn = getattr(mod, f"normalize_{m.name}_code")
        assert fn("  AbC ") == "abc", m.name


def test_doc_lists_every_module():
    doc = Path("docs/LEGACY.md").read_text().lower()
    for m in pkgutil.iter_modules(shop.legacy.__path__):
        assert m.name in doc, m.name
