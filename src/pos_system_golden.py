import os
import sys
import webbrowser

# -------------------------------------------------------------
# Path & Module Configurations
# -------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_BASE_DIR, "src")
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import pos_core
import server

# UTF-8 Console I/O Encodings
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

STORE_DETAILS = ("Python Point of Sale", "Student Mini-Store")


# =====================================================================
# 1. CLI INPUT PROMPT HELPERS
# =====================================================================

def prompt_int(message, min_value=0, allow_blank=False, default=None):
    """Prompt user for a valid integer, repeating until valid input is given."""
    while True:
        raw = input(message).strip()
        if allow_blank and raw == "":
            return default
        try:
            val = int(raw)
            if min_value is not None and val < min_value:
                print(f"Value must be at least {min_value}.")
                continue
            return val
        except ValueError:
            print("Please enter a valid whole number.")


def prompt_float(message, min_value=0.0):
    """Prompt user for a valid decimal/float number."""
    while True:
        raw = input(message).strip()
        try:
            val = float(raw)
            if min_value is not None and val < min_value:
                print(f"Value must be at least {min_value:.2f}.")
                continue
            return val
        except ValueError:
            print("Please enter a valid amount (e.g., 50.00).")


# =====================================================================
# 2. CATALOG DISPLAY
# =====================================================================

def show_products(products=None):
    """Display product catalog in a formatted table."""
    if products is None:
        products = pos_core.load_products()

    settings = pos_core.load_settings()
    curr = settings.get("currency_symbol", "₱")

    print("\n" + "=" * 45)
    print(f"  {STORE_DETAILS[0]} - {STORE_DETAILS[1]}".center(45))
    print("=" * 45)
    print(f"{'ID':<6}{'Product Name':<22}{'Price':<10}{'Stock'}")
    print("-" * 45)
    for item in products:
        price_str = f"{curr}{item['price']:.2f}"
        print(f"{item['id']:<6}{item['name']:<22}{price_str:<10}{item['stock']}")
    print("=" * 45)


# =====================================================================
# 3. SALES & CHECKOUT WORKFLOW
# =====================================================================

def _build_cart(products, curr):
    """Interactively collect products and quantities for a new sale."""
    cart = []
    product_map = {p["id"]: p for p in products}

    while True:
        entry = input("\nEnter Product ID to buy (or 'done' / 'cancel'): ").strip().lower()

        # Step 1: Handle cancellation or completion
        if entry == "cancel":
            print("Transaction cancelled.")
            return None

        if entry == "done":
            break

        # Step 2: Validate product identifier
        if not entry.isdigit():
            print("Please enter a valid numeric Product ID.")
            continue

        product_id = int(entry)
        product = product_map.get(product_id)

        if not product:
            print("Product ID not found.")
            continue

        # Step 3: Check stock availability
        if product["stock"] <= 0:
            print(f"Sorry, {product['name']} is currently out of stock.")
            continue

        already_in_cart = next((c for c in cart if c["id"] == product_id), None)
        current_cart_qty = already_in_cart["qty"] if already_in_cart else 0
        available = product["stock"] - current_cart_qty

        if available <= 0:
            print(f"All {product['stock']} units of {product['name']} are already in your cart.")
            continue

        # Step 4: Prompt and validate requested quantity
        qty = prompt_int(f"Enter quantity for {product['name']} (Available: {available}): ", min_value=1)
        if qty > available:
            print(f"Cannot add {qty}. Only {available} more units available.")
            continue

        # Step 5: Accumulate into cart
        if already_in_cart:
            already_in_cart["qty"] += qty
            already_in_cart["total"] = already_in_cart["qty"] * already_in_cart["price"]
            print(f"Updated {product['name']} quantity in cart to {already_in_cart['qty']}.")
        else:
            cart.append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "qty": qty,
                "total": qty * product["price"]
            })
            print(f"Added {qty} x {product['name']} to cart.")

    return cart


def _collect_payment(subtotal, curr):
    """Prompt cashier for payment until cash covers total."""
    print(f"\nSubtotal Amount: {curr}{subtotal:.2f}")
    while True:
        payment = prompt_float(f"Enter cash received ({curr}): ", min_value=0.0)
        if payment < subtotal:
            print(f"Insufficient cash! Need at least {curr}{subtotal:.2f}.")
            continue
        return payment


def process_sale(products=None):
    """Guide the cashier through product selection, cash payment, and receipt generation."""
    # Step 1: Load catalog & present items
    if products is None:
        products = pos_core.load_products()

    show_products(products)
    settings = pos_core.load_settings()
    curr = settings.get("currency_symbol", "₱")

    # Step 2: Build shopping cart
    cart = _build_cart(products, curr)
    if not cart:
        if cart is not None:
            print("No items added to cart.")
        return

    # Step 3: Collect payment from customer
    subtotal = sum(item["total"] for item in cart)
    payment = _collect_payment(subtotal, curr)

    cashier = input("Enter Cashier Name (press Enter for 'Terminal Console'): ").strip()
    if not cashier:
        cashier = "Terminal Console"

    # Step 4: Finalize transaction & print receipt
    try:
        cart_payload = [{"id": item["id"], "qty": item["qty"]} for item in cart]
        tx = pos_core.process_checkout(cart_payload, payment, cashier=cashier)
        print("\n" + tx["receipt_text"])
        print("\n[Receipt printed and saved to 'receipt.txt']")
    except ValueError as err:
        print(f"Checkout failed: {err}")


# =====================================================================
# 4. INVENTORY & PRODUCT MANAGEMENT
# =====================================================================

def add_product_cli():
    """Prompt user to add a new product to the catalog."""
    settings = pos_core.load_settings()
    curr = settings.get("currency_symbol", "₱")

    print("\n--- Add New Product ---")

    # Step 1: Product Name Validation
    name = input("Enter product name: ").strip()
    if not name:
        print("Product name cannot be empty.")
        return

    # Step 2: Product Category, Price, and Stock
    category = input("Enter category (Beverages, Bakery, Rice Meals, etc.): ").strip()
    price = prompt_float(f"Enter unit price ({curr}): ", min_value=0.0)
    stock = prompt_int("Enter initial stock: ", min_value=0)

    # Step 3: Register Product in Database
    try:
        new_item = pos_core.add_product(name, price, stock, category=category)
        print(f"Success! '{new_item['name']}' added with ID {new_item['id']} and barcode {new_item['barcode']}.")
    except ValueError as err:
        print(f"Failed to add product: {err}")


def update_stock_cli(products=None):
    """Update stock quantity for an existing product."""
    # Step 1: Load catalog & present products
    if products is None:
        products = pos_core.load_products()

    show_products(products)
    product_map = {p["id"]: p for p in products}

    # Step 2: Prompt for target Product ID
    product_id = prompt_int("\nEnter Product ID to update stock: ")
    selected = product_map.get(product_id)

    if not selected:
        print(f"Product ID {product_id} not found.")
        return

    # Step 3: Prompt for updated stock count
    print(f"Selected: {selected['name']} (Current Stock: {selected['stock']})")
    new_stock = prompt_int("Enter new stock count: ", min_value=0)

    # Step 4: Persist updated stock
    try:
        pos_core.update_product(product_id, {"stock": new_stock})
        print(f"Stock successfully updated to {new_stock} for {selected['name']}.")
    except ValueError as err:
        print(f"Update failed: {err}")


# =====================================================================
# 5. SALES REPORTS & ANALYTICS
# =====================================================================

def view_sales_report_cli():
    """Display store analytics and recent sales transactions."""
    analytics = pos_core.get_analytics()
    transactions = pos_core.load_transactions()
    settings = pos_core.load_settings()
    curr = settings.get("currency_symbol", "₱")

    # Step 1: Header & Key Performance Indicators
    print("\n==========================================")
    print("        SALES REPORT & STORE KPIS         ")
    print("==========================================")
    print(f" Total Gross Revenue:     {curr}{analytics['total_revenue']:.2f}")
    print(f" Completed Transactions:  {analytics['transaction_count']}")
    print(f" Average Ticket Value:    {curr}{analytics['average_ticket']:.2f}")
    print(f" Total Catalog SKUs:      {analytics['total_sku_count']}")
    print(f" Low Stock Warnings:      {analytics['low_stock_count']}")
    print(f" Out of Stock SKUs:       {analytics['out_of_stock_count']}")
    print("------------------------------------------")

    # Step 2: Recent Transactions List
    print("Recent Transactions (Last 5):")
    print(f"{'ID':<21}{'Date/Time':<21}{'Cashier':<14}{'Total'}")
    print("-" * 65)

    if not transactions:
        print("  No transactions recorded yet.")
    else:
        for tx in list(reversed(transactions))[:5]:
            tx_id = tx.get("id", "N/A")[:19]
            dt = tx.get("timestamp", "N/A")[:19]
            cashier = tx.get("cashier", "Terminal 01")[:12]
            total = f"{curr}{tx.get('total_due', 0.0):.2f}"
            print(f"{tx_id:<21}{dt:<21}{cashier:<14}{total}")
    print("==========================================")


# =====================================================================
# 6. WEB SERVER INTEGRATION
# =====================================================================

def launch_web_server():
    """Open the browser and run the built-in HTTP server."""
    print("\n==========================================")
    print("  LAUNCHING WEB-BASED POS TERMINAL")
    print("==========================================")
    print("  Opening http://localhost:8000 in your browser...")
    print("  Press Ctrl+C to stop the web server.")
    print("==========================================")
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass
    server.run_server(8000)


# =====================================================================
# 7. MAIN CLI MENU DISPATCHER
# =====================================================================

MENU_OPTIONS = {
    "1": ("Process New Sale", process_sale),
    "2": ("View Available Products", show_products),
    "3": ("Add New Product", add_product_cli),
    "4": ("Update Product Stock", update_stock_cli),
    "5": ("View Sales Report & KPIs", view_sales_report_cli),
    "6": ("Launch Modern Web POS Terminal", launch_web_server),
    "7": ("Exit", None),
}


def main():
    while True:
        print("\n==========================================")
        print("       POINT OF SALE (POS) SYSTEM")
        print("==========================================")
        for key, (label, _) in MENU_OPTIONS.items():
            print(f" [{key}] {label}")
        print("==========================================")

        choice = input("Enter your choice (1-7): ").strip()
        if choice not in MENU_OPTIONS:
            print("Invalid selection! Please enter a number between 1 and 7.")
            continue

        label, action = MENU_OPTIONS[choice]
        if action is None:
            print("Thank you for using the POS System. Goodbye!")
            break

        action()


if __name__ == "__main__":
    main()
