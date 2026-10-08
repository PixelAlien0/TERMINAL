"""
seed_ph_catalog.py
Loads 30 authentic Philippine Supermarket FMCG goods into products.json
with verified GS1 480-series barcodes and real shelf prices.
"""
import os
import sys

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR) if os.path.basename(_CURRENT_DIR) in ("src", "core", ".system") else _CURRENT_DIR
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pos_core
from ph_catalog_master import REAL_PH_SUPERMARKET_CATALOG

def main():
    print("=" * 60)
    print("  SEEDING AUTHENTIC PHILIPPINE SUPERMARKET MASTER CATALOG")
    print("=" * 60)
    
    pos_core.save_products(REAL_PH_SUPERMARKET_CATALOG)
    print(f"\n[OK] Loaded {len(REAL_PH_SUPERMARKET_CATALOG)} authentic retail products into products.json.")
    print("Real-world GS1 barcodes (Lucky Me, Jack 'n Jill, San Miguel, etc.) are now live!\n")
    
    for p in REAL_PH_SUPERMARKET_CATALOG:
        print(f"  #{p['id']:<3} | Barcode: {p['barcode']:<14} | PHP {p['price']:>6.2f} | {p['name']}")

    print("\nRestart server or refresh web browser to see the updated inventory.")

if __name__ == "__main__":
    main()
