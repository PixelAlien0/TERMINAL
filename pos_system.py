import os
import sys
import webbrowser
import pos_core
import server

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

STORE_DETAILS = ("Python Point of Sale", "Student Mini-Store")
FILE_NAME = "products.json"


def show_products(products):
    settings = pos_core.load_settings()
    curr = settings.get("currency_symbol", "₱")
    print("\n-------------------------------------------")
    print(f"      {STORE_DETAILS[0]} - {STORE_DETAILS[1]}")
    print("-------------------------------------------")
    print("ID   Product Name          Price     Stock")
    print("-------------------------------------------")
    for item in products:
        item_id = item["id"]
        name = item["name"]
        price = item["price"]
        stock = item["stock"]
        print(f"{item_id:<5}{name:<22}{curr}{price:<8.2f}{stock}")
    print("-------------------------------------------")


def process_sale(products):
    show_products(products)
    cart = []

    while True:
        choice = input("\nEnter Product ID to buy (or 'done' to checkout, 'cancel' to exit): ").strip()

        if choice.lower() == "cancel":
            print("Transaction cancelled.")
            return

        if choice.lower() == "done":
            break

        if not choice.isdigit():
            print("Please enter a valid numeric ID.")
            continue

        product_id = int(choice)
        selected_product = next((item for item in products if item["id"] == product_id), None)

        if selected_product is None:
            print("Product ID not found!")
            continue

        if selected_product["stock"] <= 0:
            print(f"Sorry, {selected_product['name']} is out of stock.")
            continue

        qty_input = input(f"Enter quantity for {selected_product['name']} (Available: {selected_product['stock']}): ").strip()
        if not qty_input.isdigit() or int(qty_input) <= 0:
            print("Quantity must be a positive whole number.")
            continue

        qty = int(qty_input)

        if qty > selected_product["stock"]:
            print(f"Not enough stock! Only {selected_product['stock']} available.")
            continue

        # Check if item is already in cart
        found_in_cart = False
        for cart_item in cart:
            if cart_item["id"] == product_id:
                if cart_item["qty"] + qty > selected_product["stock"]:
                    print("Cannot add more. Exceeds available stock.")
                    found_in_cart = True
                    break
                cart_item["qty"] += qty
                cart_item["total"] = cart_item["qty"] * cart_item["price"]
                found_in_cart = True
                print(f"Updated {selected_product['name']} quantity in cart to {cart_item['qty']}.")
                break

        if not found_in_cart:
            cart.append({
                "id": selected_product["id"],
                "name": selected_product["name"],
                "price": selected_product["price"],
                "qty": qty,
                "total": qty * selected_product["price"]
            })
            print(f"Added {qty} x {selected_product['name']} to cart.")

    if len(cart) == 0:
        print("No items purchased.")
        return

    settings = pos_core.load_settings()
    curr = settings.get("currency_symbol", "₱")
    subtotal = sum(item["total"] for item in cart)
    print(f"\nTotal Amount Due: {curr}{subtotal:.2f}")

    payment = 0.0
    while True:
        pay_input = input(f"Enter cash received ({curr}): ").strip()
        try:
            payment = float(pay_input)
            if payment < subtotal:
                print(f"Insufficient money! You need at least {curr}{subtotal:.2f}")
            else:
                break
        except ValueError:
            print("Please enter a valid amount of money (e.g., 100.00).")

    cashier_name = input("Enter Cashier Name (press Enter for 'Terminal Console'): ").strip()
    if not cashier_name:
        cashier_name = "Terminal Console"

    # Delegate checkout through unified pos_core
    try:
        cart_payload = [{"id": item["id"], "qty": item["qty"]} for item in cart]
        tx = pos_core.process_checkout(cart_payload, payment, cashier=cashier_name)
        print("\n" + tx["receipt_text"])
        print("\n[Receipt printed and recorded to database & 'receipt.txt']")
    except ValueError as e:
        print(f"Transaction failed: {e}")


def view_sales_report_cli():
    analytics = pos_core.get_analytics()
    transactions = pos_core.load_transactions()
    settings = pos_core.load_settings()
    curr = settings.get("currency_symbol", "₱")

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
    print("Recent Transactions (Last 5):")
    print("ID                   Date/Time            Cashier       Total")
    print("---------------------------------------------------------------")
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


def add_product_cli():
    settings = pos_core.load_settings()
    curr = settings.get("currency_symbol", "₱")
    print("\n--- Add New Product ---")
    name = input("Enter product name: ").strip()
    if not name:
        print("Product name cannot be empty.")
        return

    category = input("Enter category (Beverages, Bakery, Fresh, etc.): ").strip()

    try:
        price = float(input(f"Enter unit price ({curr}): ").strip())
        stock = int(input("Enter initial stock: ").strip())
        new_item = pos_core.add_product(name, price, stock, category)
        print(f"Success! '{new_item['name']}' added with ID {new_item['id']}.")
    except ValueError as e:
        print(f"Invalid input: {e}")


def update_stock_cli(products):
    show_products(products)
    choice = input("\nEnter Product ID to update stock: ").strip()

    if not choice.isdigit():
        print("Invalid ID.")
        return

    product_id = int(choice)
    selected_product = next((item for item in products if item["id"] == product_id), None)

    if selected_product is None:
        print("Product not found.")
        return

    print(f"Selected: {selected_product['name']} (Current Stock: {selected_product['stock']})")
    stock_input = input("Enter new stock count: ").strip()

    if not stock_input.isdigit():
        print("Stock must be a positive whole number.")
        return

    try:
        pos_core.update_product(product_id, {"stock": int(stock_input)})
        print(f"Stock updated successfully for {selected_product['name']}.")
    except ValueError as e:
        print(f"Update failed: {e}")


def launch_web_server():
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


def main():
    while True:
        products = pos_core.load_products()
        print("\n==========================================")
        print("       POINT OF SALE (POS) SYSTEM")
        print("==========================================")
        print(" [1] Process New Sale")
        print(" [2] View Available Products")
        print(" [3] Add New Product")
        print(" [4] Update Product Stock")
        print(" [5] View Sales Report & KPIs")
        print(" [6] Launch Modern Web POS Terminal")
        print(" [7] Exit")
        print("==========================================")

        choice = input("Enter your choice (1-7): ").strip()

        if choice == "1":
            process_sale(products)
        elif choice == "2":
            show_products(products)
        elif choice == "3":
            add_product_cli()
        elif choice == "4":
            update_stock_cli(products)
        elif choice == "5":
            view_sales_report_cli()
        elif choice == "6":
            launch_web_server()
        elif choice == "7":
            print("Thank you for using the POS System. Goodbye!")
            break
        else:
            print("Invalid selection! Please enter a number between 1 and 7.")


if __name__ == "__main__":
    main()
