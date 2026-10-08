import json
import os
import threading
from datetime import datetime

# -------------------------------------------------------------
# Configuration & File Paths
# -------------------------------------------------------------
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(_CURRENT_DIR) in ("src", "core", ".system", "internal"):
    BASE_DIR = os.path.dirname(_CURRENT_DIR)
else:
    BASE_DIR = _CURRENT_DIR
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.json")
TRANSACTIONS_FILE = os.path.join(BASE_DIR, "transactions.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
RECEIPT_FILE = os.path.join(BASE_DIR, "receipt.txt")

DEFAULT_SETTINGS = {
    "tax_enabled": True,
    "tax_rate": 12.00,
    "tax_name": "VAT (12%)",
    "store_name": "METRO POINT OF SALE",
    "branch": "Terminal 01 - Manila BGC",
    "address": "100 Retail Boulevard, BGC, Taguig",
    "phone": "+63 (02) 8123-4567",
    "currency_symbol": "₱"
}

DEFAULT_PRODUCTS = [
    {
        "id": 101,
        "name": "Espresso",
        "category": "Beverages",
        "barcode": "8901001",
        "price": 2.50,
        "stock": 50,
        "available_modifiers": [
            {"name": "Extra Shot", "price": 0.75},
            {"name": "Decaf", "price": 0.00}
        ]
    },
    {
        "id": 102,
        "name": "Latte",
        "category": "Beverages",
        "barcode": "8901002",
        "price": 3.75,
        "stock": 40,
        "available_modifiers": [
            {"name": "Oat Milk", "price": 0.60},
            {"name": "Vanilla Syrup", "price": 0.50},
            {"name": "Extra Shot", "price": 0.75}
        ]
    },
    {
        "id": 103,
        "name": "Cappuccino",
        "category": "Beverages",
        "barcode": "8901003",
        "price": 3.50,
        "stock": 35,
        "available_modifiers": [
            {"name": "Almond Milk", "price": 0.60},
            {"name": "Cinnamon", "price": 0.00},
            {"name": "Extra Shot", "price": 0.75}
        ]
    },
    {
        "id": 104,
        "name": "Ham & Cheese Croissant",
        "category": "Bakery",
        "barcode": "8901004",
        "price": 4.50,
        "stock": 25,
        "available_modifiers": [
            {"name": "Warmed Up", "price": 0.00},
            {"name": "Extra Cheese", "price": 0.75}
        ]
    },
    {
        "id": 105,
        "name": "Blueberry Muffin",
        "category": "Bakery",
        "barcode": "8901005",
        "price": 2.75,
        "stock": 30,
        "available_modifiers": [
            {"name": "Warmed Up", "price": 0.00}
        ]
    },
    {
        "id": 106,
        "name": "Bottled Water",
        "category": "Beverages",
        "barcode": "8901006",
        "price": 1.50,
        "stock": 60,
        "available_modifiers": []
    },
    {
        "id": 107,
        "name": "Apple",
        "category": "Fresh",
        "barcode": "8901007",
        "price": 1.00,
        "stock": 50,
        "available_modifiers": []
    }
]

CATEGORY_KEYWORDS = {
    "Beverages": ("coffee", "espresso", "latte", "cappuccino", "tea", "water", "drink", "juice", "beer", "pilsen", "beverage"),
    "Bakery & Pastries": ("muffin", "croissant", "sandwich", "bread", "cake", "cookie", "ensaymada", "pandesal", "pastry"),
    "Rice Meals": ("silog", "tapa", "tocino", "adobo", "inasal", "lechon", "rice", "bowl", "meal"),
    "Snacks & Desserts": ("halo-halo", "flan", "turon", "cassava", "chips", "snack", "dessert"),
    "Fresh Produce": ("mango", "banana", "apple", "papaya", "fruit", "salad", "fresh", "produce"),
}

_db_lock = threading.Lock()


# -------------------------------------------------------------
# JSON File Persistence Helpers
# -------------------------------------------------------------
def _read_json(filepath, default):
    """Safely load JSON data from a file, returning default if missing or invalid."""
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(filepath, data):
    """Atomically write JSON data to file using a temporary file replacement."""
    temp_file = f"{filepath}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    os.replace(temp_file, filepath)


# -------------------------------------------------------------
# Settings Management
# -------------------------------------------------------------
def load_settings():
    """Load store and tax settings, creating defaults if not yet present."""
    with _db_lock:
        if not os.path.exists(SETTINGS_FILE):
            _write_json(SETTINGS_FILE, DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)
        return _read_json(SETTINGS_FILE, dict(DEFAULT_SETTINGS))


def save_settings_unlocked(settings):
    """Internal helper to save settings without acquiring the lock."""
    _write_json(SETTINGS_FILE, settings)


def update_settings(updates):
    """Update configurable settings such as tax rate, store name, or currency."""
    with _db_lock:
        settings = _read_json(SETTINGS_FILE, dict(DEFAULT_SETTINGS))

        if "tax_enabled" in updates:
            settings["tax_enabled"] = bool(updates["tax_enabled"])

        if "tax_rate" in updates:
            try:
                rate = float(updates["tax_rate"])
                if rate < 0:
                    raise ValueError("Tax rate cannot be negative.")
                settings["tax_rate"] = round(rate, 2)
            except (ValueError, TypeError):
                raise ValueError("Tax rate must be a valid number.")

        for str_field in ("tax_name", "store_name", "branch", "phone", "currency_symbol"):
            if str_field in updates and str(updates[str_field]).strip():
                settings[str_field] = str(updates[str_field]).strip()

        _write_json(SETTINGS_FILE, settings)
        return settings


# -------------------------------------------------------------
# Product Catalog Operations
# -------------------------------------------------------------
def get_default_modifiers(category):
    """Return common modifiers based on product category."""
    cat = (category or "").lower()
    if "beverage" in cat:
        return [
            {"name": "Extra Shot", "price": 0.75},
            {"name": "Oat Milk", "price": 0.60},
            {"name": "Decaf", "price": 0.00}
        ]
    if "bakery" in cat:
        return [{"name": "Warmed Up", "price": 0.00}]
    return []


def infer_category(name):
    """Guess appropriate category name based on item keywords."""
    lower_name = (name or "").lower()
    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower_name for kw in keywords):
            return cat_name
    return "General"


def _normalize_products(products):
    """Ensure all products possess barcode, category, and modifier fields."""
    modified = False
    for p in products:
        if "category" not in p:
            p["category"] = infer_category(p.get("name", ""))
            modified = True
        if not p.get("barcode"):
            p["barcode"] = f"890{p.get('id', 100)}"
            modified = True
        if "available_modifiers" not in p:
            p["available_modifiers"] = get_default_modifiers(p.get("category", ""))
            modified = True
    return modified


def load_products():
    """Load product catalog from JSON, populating seed data on first run."""
    with _db_lock:
        if not os.path.exists(PRODUCTS_FILE):
            _write_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
            return list(DEFAULT_PRODUCTS)

        products = _read_json(PRODUCTS_FILE, [])
        if _normalize_products(products):
            _write_json(PRODUCTS_FILE, products)
        return products


def save_products_unlocked(products):
    """Internal helper to save product catalog without acquiring the lock."""
    _write_json(PRODUCTS_FILE, products)


def save_products(products):
    """Thread-safe save for product catalog."""
    with _db_lock:
        save_products_unlocked(products)


def find_product_by_barcode(code, auto_scrape=True):
    """Find a product matching barcode, SKU, or ID (exact, case-insensitive, or auto-scrapes retail master catalog)."""
    if code is None:
        return None
    code_str = str(code).strip()
    if not code_str:
        return None

    code_lower = code_str.lower()
    products = load_products()

    # 1. Exact match on barcode or ID
    for p in products:
        bc = str(p.get("barcode", "")).strip()
        pid = str(p.get("id", "")).strip()
        if bc == code_str or pid == code_str:
            return p

    # 2. Case-insensitive match
    for p in products:
        bc = str(p.get("barcode", "")).strip().lower()
        pid = str(p.get("id", "")).strip().lower()
        if bc == code_lower or pid == code_lower:
            return p

    # 3. Flexible numeric match (handles leading zeroes or partial scans)
    code_clean = code_str.lstrip("0")
    for p in products:
        bc = str(p.get("barcode", "")).strip()
        pid = str(p.get("id", "")).strip()
        if (bc and bc.lstrip("0") == code_clean) or (pid and pid.lstrip("0") == code_clean):
            return p
        if bc and len(code_str) >= 4 and (code_str.endswith(bc) or bc.endswith(code_str)):
            return p

    # 4. Live Master Catalog Online Scraper (Auto-discovers real retail packaging)
    if auto_scrape and len(code_str) >= 6 and code_str.isdigit():
        try:
            import ph_catalog_master
            meta = ph_catalog_master.scrape_barcode_metadata(code_str)
            if meta and meta.get("name"):
                est_price = ph_catalog_master.estimate_retail_price(meta["name"], meta.get("category", ""))
                new_item = add_product(
                    name=meta["name"],
                    price=est_price,
                    stock=50,
                    category=meta.get("category", "Supermarket Goods"),
                    barcode=code_str
                )
                return new_item
        except Exception:
            pass

    return None


def add_product(name, price, stock, category=None, barcode=None, modifiers=None, icon=None):
    """Add a new product with auto-incremented ID and generated barcode."""
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Product name is required.")

    try:
        numeric_price = round(float(price), 2)
        numeric_stock = int(stock)
    except (ValueError, TypeError):
        raise ValueError("Price must be a valid number and stock must be an integer.")

    if numeric_price < 0 or numeric_stock < 0:
        raise ValueError("Price and stock cannot be negative.")

    chosen_category = (category.strip().capitalize() if category else infer_category(clean_name))

    with _db_lock:
        products = _read_json(PRODUCTS_FILE, [])
        new_id = (max((p.get("id", 0) for p in products), default=100) + 1)
        item_barcode = str(barcode).strip() if barcode else f"890{new_id}"
        item_modifiers = modifiers if modifiers is not None else get_default_modifiers(chosen_category)

        new_item = {
            "id": new_id,
            "name": clean_name,
            "category": chosen_category,
            "barcode": item_barcode,
            "price": numeric_price,
            "stock": numeric_stock,
            "available_modifiers": item_modifiers
        }
        if icon:
            new_item["icon"] = str(icon).strip()

        products.append(new_item)
        _write_json(PRODUCTS_FILE, products)
        return new_item


def update_product(product_id, updates):
    """Update fields (price, stock, name, barcode, modifiers) for a single product."""
    with _db_lock:
        products = _read_json(PRODUCTS_FILE, [])
        target = next((p for p in products if p["id"] == product_id), None)
        if not target:
            raise ValueError(f"Product ID {product_id} not found.")

        if "name" in updates and str(updates["name"]).strip():
            target["name"] = str(updates["name"]).strip()
        if "category" in updates and str(updates["category"]).strip():
            target["category"] = str(updates["category"]).strip()
        if "barcode" in updates and str(updates["barcode"]).strip():
            target["barcode"] = str(updates["barcode"]).strip()
        if "icon" in updates:
            target["icon"] = str(updates["icon"]).strip()

        if "price" in updates:
            val = round(float(updates["price"]), 2)
            if val < 0:
                raise ValueError("Price cannot be negative.")
            target["price"] = val

        if "stock" in updates:
            val = int(updates["stock"])
            if val < 0:
                raise ValueError("Stock cannot be negative.")
            target["stock"] = val

        if "available_modifiers" in updates and isinstance(updates["available_modifiers"], list):
            target["available_modifiers"] = updates["available_modifiers"]

        _write_json(PRODUCTS_FILE, products)
        return target


def delete_product(product_id):
    """Delete a product by ID, returning True on success or False if not found."""
    with _db_lock:
        products = _read_json(PRODUCTS_FILE, [])
        initial_count = len(products)
        products = [p for p in products if p["id"] != product_id]

        if len(products) == initial_count:
            return False

        _write_json(PRODUCTS_FILE, products)
        return True


# -------------------------------------------------------------
# Transaction Ledger & Checkout Flow
# -------------------------------------------------------------
def load_transactions():
    """Load list of completed sales transactions."""
    with _db_lock:
        return _read_json(TRANSACTIONS_FILE, [])


def save_transaction(tx):
    """Append a completed transaction to the ledger file."""
    with _db_lock:
        transactions = _read_json(TRANSACTIONS_FILE, [])
        transactions.append(tx)
        _write_json(TRANSACTIONS_FILE, transactions)


def _prepare_cart_items(cart_items, product_map):
    """Validate requested items against current stock and compute line totals."""
    detailed_cart = []
    subtotal = 0.0

    for item in cart_items:
        pid = item.get("id")
        qty = int(item.get("qty", 0))

        if pid not in product_map:
            raise ValueError(f"Product ID {pid} does not exist.")
        if qty <= 0:
            raise ValueError(f"Quantity for product ID {pid} must be positive.")

        prod = product_map[pid]
        if qty > prod["stock"]:
            raise ValueError(f"Insufficient stock for '{prod['name']}'. Requested: {qty}, Available: {prod['stock']}.")

        # Clean modifiers and sum extra costs
        cleaned_mods = []
        mod_cost = 0.0
        for m in item.get("modifiers", []):
            m_name = str(m.get("name", "")).strip()
            m_price = round(float(m.get("price", 0.0)), 2)
            mod_cost += m_price
            cleaned_mods.append({"name": m_name, "price": m_price})

        unit_price = round(prod["price"] + mod_cost, 2)
        line_total = round(unit_price * qty, 2)
        subtotal = round(subtotal + line_total, 2)

        detailed_cart.append({
            "id": prod["id"],
            "name": prod["name"],
            "base_price": prod["price"],
            "unit_price": unit_price,
            "qty": qty,
            "modifiers": cleaned_mods,
            "notes": str(item.get("notes", "")).strip(),
            "total": line_total
        })

    return detailed_cart, subtotal


def process_checkout(cart_items, cash_received, cashier="Terminal 01"):
    """
    Validate inventory, compute tax, deduct stock, persist record, and return receipt.
    cart_items: list of dicts with keys 'id', 'qty', optional 'modifiers', and optional 'notes'.
    """
    if not cart_items:
        raise ValueError("Cart is empty.")

    try:
        tendered = round(float(cash_received), 2)
    except (ValueError, TypeError):
        raise ValueError("Invalid cash received amount.")

    settings = load_settings()

    with _db_lock:
        products = _read_json(PRODUCTS_FILE, None)
        if products is None:
            raise ValueError("Inventory not initialized.")

        product_map = {p["id"]: p for p in products}
        detailed_cart, subtotal = _prepare_cart_items(cart_items, product_map)

        # Tax calculations
        tax_enabled = settings.get("tax_enabled", True)
        tax_rate = float(settings.get("tax_rate", 12.00)) if tax_enabled else 0.0
        tax_amount = round(subtotal * (tax_rate / 100), 2) if tax_enabled else 0.0
        total_due = round(subtotal + tax_amount, 2)

        curr = settings.get("currency_symbol", "₱")
        if tendered < total_due:
            raise ValueError(f"Insufficient funds. Total due is {curr}{total_due:.2f}, but received {curr}{tendered:.2f}.")

        change = round(tendered - total_due, 2)

        # Deduct sold stock
        for item in detailed_cart:
            product_map[item["id"]]["stock"] -= item["qty"]

        _write_json(PRODUCTS_FILE, products)

    # Generate transaction identifiers and receipt
    now = datetime.now()
    tx_id = f"TX-{now.strftime('%Y%m%d%H%M%S')}-{detailed_cart[0]['id']}"
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    receipt_text = format_thermal_receipt(
        tx_id, timestamp_str, detailed_cart, subtotal, tax_rate, tax_amount,
        total_due, tendered, change, settings, cashier=cashier
    )

    try:
        with open(RECEIPT_FILE, "w", encoding="utf-8") as f:
            f.write(receipt_text)
    except OSError:
        pass

    record = {
        "id": tx_id,
        "timestamp": timestamp_str,
        "cashier": cashier,
        "items": detailed_cart,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total_due": total_due,
        "payment": tendered,
        "change": change,
        "receipt_text": receipt_text
    }

    save_transaction(record)
    return record


# -------------------------------------------------------------
# Thermal Receipt Formatter
# -------------------------------------------------------------
def format_thermal_receipt(tx_id, timestamp_str, items, subtotal, tax_rate, tax_amount, total_due, payment, change, settings, cashier="Terminal 01"):
    """Format an 80mm monospace receipt text block."""
    width = 42
    sym = settings.get("currency_symbol", "₱")

    lines = [
        "=" * width,
        settings.get("store_name", "METRO POINT OF SALE").center(width),
        settings.get("branch", "Terminal 01").center(width),
        settings.get("phone", "").center(width),
        "=" * width,
        f"Receipt ID: {tx_id}",
        f"Date/Time:  {timestamp_str}",
        f"Cashier:    {cashier}",
        "-" * width,
        f"{'Item':<22}{'Qty':<5}{'Price':<7}{'Total':>8}",
        "-" * width,
    ]

    for item in items:
        name = item["name"][:20]
        qty = str(item["qty"])
        unit_p = f"{sym}{item['unit_price']:.2f}"
        line_tot = f"{sym}{item['total']:.2f}"
        lines.append(f"{name:<22}{qty:<5}{unit_p:<7}{line_tot:>8}")

        for mod in item.get("modifiers", []):
            mod_text = f"  + {mod['name']}"
            if mod.get("price", 0) > 0:
                mod_text += f" (+{sym}{mod['price']:.2f})"
            lines.append(f"{mod_text:<34}")

        if item.get("notes"):
            lines.append(f"  * Note: {item['notes']}"[:width])

    lines.extend([
        "-" * width,
        f"{'Subtotal:':<24}{f'{sym}{subtotal:.2f}':>18}"
    ])

    if tax_amount > 0:
        tax_label = f"{settings.get('tax_name', 'Sales Tax')} ({tax_rate:.2f}%):"
        lines.append(f"{tax_label:<24}{f'{sym}{tax_amount:.2f}':>18}")

    lines.extend([
        f"{'Total Due:':<24}{f'{sym}{total_due:.2f}':>18}",
        f"{'Cash Tendered:':<24}{f'{sym}{payment:.2f}':>18}",
        f"{'Change Given:':<24}{f'{sym}{change:.2f}':>18}",
        "=" * width,
        "Scan QR code below for digital copy".center(width),
        "=" * width
    ])
    return "\n".join(lines)


# -------------------------------------------------------------
# Store Analytics & Inventory Health
# -------------------------------------------------------------
def get_analytics():
    """Calculate revenue totals, ticket sizes, and stock warnings."""
    products = load_products()
    transactions = load_transactions()

    total_sales = round(sum(tx.get("total_due", tx.get("subtotal", 0.0)) for tx in transactions), 2)
    tx_count = len(transactions)
    avg_order = round(total_sales / tx_count, 2) if tx_count > 0 else 0.0

    low_stock = [p for p in products if p.get("stock", 0) <= 10]
    out_of_stock = [p for p in products if p.get("stock", 0) == 0]

    return {
        "total_revenue": total_sales,
        "transaction_count": tx_count,
        "average_ticket": avg_order,
        "total_sku_count": len(products),
        "low_stock_count": len(low_stock),
        "out_of_stock_count": len(out_of_stock),
        "low_stock_items": low_stock
    }
