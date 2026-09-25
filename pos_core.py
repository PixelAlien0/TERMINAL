import json
import os
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

_db_lock = threading.Lock()


# -------------------------------------------------------------
# Settings Management
# -------------------------------------------------------------
def load_settings():
    """Load store and tax settings."""
    with _db_lock:
        if not os.path.exists(SETTINGS_FILE):
            save_settings_unlocked(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)

        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            try:
                settings = json.load(file)
            except json.JSONDecodeError:
                settings = dict(DEFAULT_SETTINGS)
        return settings


def save_settings_unlocked(settings):
    temp_file = f"{SETTINGS_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4)
    os.replace(temp_file, SETTINGS_FILE)


def update_settings(updates):
    """Update configurable settings like tax rate and toggle."""
    with _db_lock:
        settings = dict(DEFAULT_SETTINGS)
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
                try:
                    settings = json.load(file)
                except json.JSONDecodeError:
                    pass

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
        if "tax_name" in updates and str(updates["tax_name"]).strip():
            settings["tax_name"] = str(updates["tax_name"]).strip()
        if "store_name" in updates and str(updates["store_name"]).strip():
            settings["store_name"] = str(updates["store_name"]).strip()
        if "branch" in updates and str(updates["branch"]).strip():
            settings["branch"] = str(updates["branch"]).strip()
        if "phone" in updates and str(updates["phone"]).strip():
            settings["phone"] = str(updates["phone"]).strip()
        if "currency_symbol" in updates and str(updates["currency_symbol"]).strip():
            settings["currency_symbol"] = str(updates["currency_symbol"]).strip()

        save_settings_unlocked(settings)
        return settings


# -------------------------------------------------------------
# Product Catalog Operations
# -------------------------------------------------------------
def load_products():
    """Load all products from JSON database, ensuring schema integrity."""
    with _db_lock:
        if not os.path.exists(PRODUCTS_FILE):
            default_products = [
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
            save_products_unlocked(default_products)
            return default_products

        with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
            try:
                products = json.load(file)
            except json.JSONDecodeError:
                products = []

        # Ensure barcode, categories, and modifiers exist for backward-compatibility
        updated = False
        for p in products:
            if "category" not in p:
                p["category"] = infer_category(p.get("name", ""))
                updated = True
            if "barcode" not in p or not p["barcode"]:
                p["barcode"] = f"890{p.get('id', 100)}"
                updated = True
            if "available_modifiers" not in p:
                p["available_modifiers"] = get_default_modifiers(p.get("category", ""))
                updated = True

        if updated:
            save_products_unlocked(products)

        return products


def get_default_modifiers(category):
    cat = (category or "").lower()
    if "beverage" in cat:
        return [
            {"name": "Extra Shot", "price": 0.75},
            {"name": "Oat Milk", "price": 0.60},
            {"name": "Decaf", "price": 0.00}
        ]
    if "bakery" in cat:
        return [
            {"name": "Warmed Up", "price": 0.00}
        ]
    return []


def infer_category(name):
    lower = name.lower()
    if any(k in lower for k in ["coffee", "espresso", "latte", "cappuccino", "tea", "water", "drink", "juice", "beer", "pilsen", "beverage"]):
        return "Beverages"
    if any(k in lower for k in ["muffin", "croissant", "sandwich", "bread", "cake", "cookie", "ensaymada", "pandesal", "pastry"]):
        return "Bakery & Pastries"
    if any(k in lower for k in ["silog", "tapa", "tocino", "adobo", "inasal", "lechon", "rice", "bowl", "meal"]):
        return "Rice Meals"
    if any(k in lower for k in ["halo-halo", "flan", "turon", "cassava", "chips", "snack", "dessert"]):
        return "Snacks & Desserts"
    if any(k in lower for k in ["mango", "banana", "apple", "papaya", "fruit", "salad", "fresh", "produce"]):
        return "Fresh Produce"
    return "General"


def save_products_unlocked(products):
    temp_file = f"{PRODUCTS_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(products, file, indent=4)
    os.replace(temp_file, PRODUCTS_FILE)


def save_products(products):
    with _db_lock:
        save_products_unlocked(products)


def find_product_by_barcode(code):
    """Lookup product by barcode or exact ID."""
    code_str = str(code).strip()
    products = load_products()
    for p in products:
        if str(p.get("barcode", "")).strip() == code_str or str(p.get("id")) == code_str:
            return p
    return None


def add_product(name, price, stock, category=None, barcode=None, modifiers=None, icon=None):
    """Add a new product with auto-incremented ID and barcode."""
    name = str(name).strip()
    if not name:
        raise ValueError("Product name is required.")

    try:
        price = round(float(price), 2)
        stock = int(stock)
    except (ValueError, TypeError):
        raise ValueError("Price must be a valid number and stock must be an integer.")

    if price < 0 or stock < 0:
        raise ValueError("Price and stock cannot be negative.")

    if not category:
        category = infer_category(name)

    with _db_lock:
        products = []
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
                try:
                    products = json.load(file)
                except json.JSONDecodeError:
                    products = []

        new_id = 101
        if products:
            existing_ids = [item.get("id", 0) for item in products]
            new_id = max(existing_ids) + 1

        if not barcode:
            barcode = f"890{new_id}"

        if modifiers is None:
            modifiers = get_default_modifiers(category)

        new_item = {
            "id": new_id,
            "name": name,
            "category": category.strip().capitalize(),
            "barcode": str(barcode).strip(),
            "price": price,
            "stock": stock,
            "available_modifiers": modifiers
        }
        if icon:
            new_item["icon"] = str(icon).strip()

        products.append(new_item)
        save_products_unlocked(products)
        return new_item


def update_product(product_id, updates):
    """Update stock, price, name, category, or barcode for a product."""
    with _db_lock:
        if not os.path.exists(PRODUCTS_FILE):
            raise ValueError("Product not found.")

        with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
            products = json.load(file)

        target = next((item for item in products if item["id"] == product_id), None)
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
            p = round(float(updates["price"]), 2)
            if p < 0:
                raise ValueError("Price cannot be negative.")
            target["price"] = p
        if "stock" in updates:
            s = int(updates["stock"])
            if s < 0:
                raise ValueError("Stock cannot be negative.")
            target["stock"] = s
        if "available_modifiers" in updates and isinstance(updates["available_modifiers"], list):
            target["available_modifiers"] = updates["available_modifiers"]

        save_products_unlocked(products)
        return target


def delete_product(product_id):
    """Delete a product by ID."""
    with _db_lock:
        if not os.path.exists(PRODUCTS_FILE):
            return False

        with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
            products = json.load(file)

        initial_len = len(products)
        products = [p for p in products if p["id"] != product_id]

        if len(products) == initial_len:
            return False

        save_products_unlocked(products)
        return True


# -------------------------------------------------------------
# Transaction Ledger & Checkout Flow
# -------------------------------------------------------------
def load_transactions():
    """Load sales transactions."""
    with _db_lock:
        if not os.path.exists(TRANSACTIONS_FILE):
            return []
        with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []


def save_transaction(tx):
    """Append a completed transaction."""
    with _db_lock:
        transactions = []
        if os.path.exists(TRANSACTIONS_FILE):
            with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as file:
                try:
                    transactions = json.load(file)
                except json.JSONDecodeError:
                    transactions = []

        transactions.append(tx)
        temp_file = f"{TRANSACTIONS_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(transactions, file, indent=4)
        os.replace(temp_file, TRANSACTIONS_FILE)


def process_checkout(cart_items, cash_received, cashier="Terminal 01"):
    """
    Validate stock, process modifiers, apply configurable tax, record transaction, and return receipt.
    cart_items: list of dicts with:
      - 'id': int
      - 'qty': int
      - 'modifiers': list of {'name': str, 'price': float} (optional)
      - 'notes': str (optional)
    """
    if not cart_items:
        raise ValueError("Cart is empty.")

    try:
        cash_received = round(float(cash_received), 2)
    except (ValueError, TypeError):
        raise ValueError("Invalid cash received amount.")

    settings = load_settings()

    with _db_lock:
        if not os.path.exists(PRODUCTS_FILE):
            raise ValueError("Inventory not initialized.")

        with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
            products = json.load(file)

        product_map = {p["id"]: p for p in products}

        detailed_cart = []
        subtotal = 0.0

        for item in cart_items:
            pid = item.get("id")
            qty = int(item.get("qty", 0))

            if pid not in product_map:
                raise ValueError(f"Product ID {pid} does not exist.")
            if qty <= 0:
                raise ValueError(f"Quantity for product ID {pid} must be positive.")

            p = product_map[pid]
            if qty > p["stock"]:
                raise ValueError(
                    f"Insufficient stock for '{p['name']}'. Requested: {qty}, Available: {p['stock']}."
                )

            # Process modifiers & extra charges
            mods = item.get("modifiers", [])
            modifier_unit_total = 0.0
            cleaned_modifiers = []
            for m in mods:
                m_name = str(m.get("name", "")).strip()
                m_price = round(float(m.get("price", 0.0)), 2)
                modifier_unit_total += m_price
                cleaned_modifiers.append({"name": m_name, "price": m_price})

            notes = str(item.get("notes", "")).strip()

            unit_price = round(p["price"] + modifier_unit_total, 2)
            item_total = round(unit_price * qty, 2)
            subtotal = round(subtotal + item_total, 2)

            detailed_cart.append({
                "id": p["id"],
                "name": p["name"],
                "base_price": p["price"],
                "unit_price": unit_price,
                "qty": qty,
                "modifiers": cleaned_modifiers,
                "notes": notes,
                "total": item_total
            })

        # Calculate Sales Tax
        tax_enabled = settings.get("tax_enabled", True)
        tax_rate = float(settings.get("tax_rate", 8.25)) if tax_enabled else 0.0
        tax_amount = round(subtotal * (tax_rate / 100), 2) if tax_enabled else 0.0
        total_due = round(subtotal + tax_amount, 2)

        sym = settings.get("currency_symbol", "₱")
        if cash_received < total_due:
            raise ValueError(
                f"Insufficient funds. Total due is {sym}{total_due:.2f} (inc. tax), but only received {sym}{cash_received:.2f}."
            )

        change = round(cash_received - total_due, 2)

        # Deduct inventory
        for item in detailed_cart:
            product_map[item["id"]]["stock"] -= item["qty"]

        save_products_unlocked(products)

    now = datetime.now()
    tx_id = f"TX-{now.strftime('%Y%m%d%H%M%S')}-{detailed_cart[0]['id']}"
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    receipt_text = format_thermal_receipt(
        tx_id, timestamp_str, detailed_cart, subtotal, tax_rate, tax_amount, total_due, cash_received, change, settings, cashier=cashier
    )

    try:
        with open(RECEIPT_FILE, "w", encoding="utf-8") as f:
            f.write(receipt_text)
    except Exception:
        pass

    transaction_record = {
        "id": tx_id,
        "timestamp": timestamp_str,
        "cashier": cashier,
        "items": detailed_cart,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total_due": total_due,
        "payment": cash_received,
        "change": change,
        "receipt_text": receipt_text
    }

    save_transaction(transaction_record)
    return transaction_record


def format_thermal_receipt(tx_id, timestamp_str, items, subtotal, tax_rate, tax_amount, total_due, payment, change, settings, cashier="Terminal 01"):
    """Generate clean fixed-width thermal receipt with itemized modifiers and tax."""
    w = 42
    lines = [
        "=" * w,
        settings.get("store_name", "METRO POINT OF SALE").center(w),
        settings.get("branch", "Terminal 01").center(w),
        settings.get("phone", "").center(w),
        "=" * w,
        f"Receipt ID: {tx_id}",
        f"Date/Time:  {timestamp_str}",
        f"Cashier:    {cashier}",
        "-" * w,
        f"{'Item':<22}{'Qty':<5}{'Price':<7}{'Total':>8}",
        "-" * w,
    ]

    sym = settings.get("currency_symbol", "₱")
    for item in items:
        name = item["name"][:20]
        qty = str(item["qty"])
        price = f"{sym}{item['unit_price']:.2f}"
        total = f"{sym}{item['total']:.2f}"
        lines.append(f"{name:<22}{qty:<5}{price:<7}{total:>8}")

        # Itemize modifiers
        for mod in item.get("modifiers", []):
            mod_str = f"  + {mod['name']}"
            if mod["price"] > 0:
                mod_str += f" (+{sym}{mod['price']:.2f})"
            lines.append(f"{mod_str:<34}")

        # Itemize special note
        if item.get("notes"):
            note_str = f"  * Note: {item['notes']}"
            lines.append(f"{note_str:<42}")

    lines.extend([
        "-" * w,
        f"{'Subtotal:':<24}{f'{sym}{subtotal:.2f}':>18}"
    ])

    if tax_amount > 0:
        tax_label = f"{settings.get('tax_name', 'Sales Tax')} ({tax_rate:.2f}%):"
        lines.append(f"{tax_label:<24}{f'{sym}{tax_amount:.2f}':>18}")

    lines.extend([
        f"{'Total Due:':<24}{f'{sym}{total_due:.2f}':>18}",
        f"{'Cash Tendered:':<24}{f'{sym}{payment:.2f}':>18}",
        f"{'Change Given:':<24}{f'{sym}{change:.2f}':>18}",
        "=" * w,
        "Scan QR code below for digital copy".center(w),
        "=" * w
    ])
    return "\n".join(lines)


def get_analytics():
    """Calculate store analytics and inventory health."""
    products = load_products()
    transactions = load_transactions()

    total_sales = round(sum(tx.get("total_due", tx.get("subtotal", 0.0)) for tx in transactions), 2)
    tx_count = len(transactions)
    avg_order = round(total_sales / tx_count, 2) if tx_count > 0 else 0.0

    low_stock_items = [p for p in products if p.get("stock", 0) <= 10]
    out_of_stock_items = [p for p in products if p.get("stock", 0) == 0]

    return {
        "total_revenue": total_sales,
        "transaction_count": tx_count,
        "average_ticket": avg_order,
        "total_sku_count": len(products),
        "low_stock_count": len(low_stock_items),
        "out_of_stock_count": len(out_of_stock_items),
        "low_stock_items": low_stock_items
    }
