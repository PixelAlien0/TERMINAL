import json
import os
import urllib.request
import urllib.error
import pos_core

BASE_URL = "http://127.0.0.1:8000"

def fetch_json(endpoint, method="GET", data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def test_sync():
    print("[1/5] Verifying API Server & Storage Sync Endpoint...")
    sync_data = fetch_json("/api/sync")
    assert sync_data["success"] is True, "Sync endpoint failed"
    meta = sync_data["sync"]
    assert "products_mtime" in meta
    assert "transactions_mtime" in meta
    assert "settings_mtime" in meta
    print(f"      Sync state: {meta['products_count']} products, {meta['transactions_count']} transactions.")

    print("[2/5] Testing Storage File Linking (products.json <-> Python)...")
    file_products = pos_core.load_products()
    api_products = fetch_json("/api/products")["products"]
    assert len(file_products) == len(api_products), f"Count mismatch: {len(file_products)} vs {len(api_products)}"
    print(f"      Both Python storage and REST API report exactly {len(file_products)} products.")

    print("[3/5] Testing Web Checkout -> Disk Synchronization...")
    initial_stock = next(p["stock"] for p in file_products if p["id"] == 101)
    checkout_res = fetch_json("/api/checkout", method="POST", data={
        "items": [{"id": 101, "qty": 1, "modifiers": [{"name": "Extra Shot", "price": 25.00}], "notes": "Sync Test"}],
        "cash_received": 500.00,
        "cashier": "Sync Verification Agent"
    })
    assert checkout_res["success"] is True, "Checkout failed"
    tx = checkout_res["transaction"]
    
    # Verify stock in products.json was decremented on disk
    updated_products = pos_core.load_products()
    updated_stock = next(p["stock"] for p in updated_products if p["id"] == 101)
    assert updated_stock == initial_stock - 1, f"Stock not decremented on disk! Expected {initial_stock - 1}, got {updated_stock}"

    # Verify transaction was appended to transactions.json on disk
    tx_file = pos_core.load_transactions()
    assert any(t["id"] == tx["id"] for t in tx_file), "Transaction not found in transactions.json on disk!"

    # Verify receipt.txt on disk was generated
    assert os.path.exists(pos_core.RECEIPT_FILE), "receipt.txt does not exist on disk!"
    with open(pos_core.RECEIPT_FILE, "r", encoding="utf-8") as f:
        receipt_content = f.read()
    assert tx["id"] in receipt_content, "receipt.txt does not contain latest transaction ID!"
    print(f"      Checkout successfully deducted inventory and updated products.json, transactions.json, and receipt.txt on disk.")

    print("[4/5] Testing Settings Synchronization (settings.json <-> Python)...")
    orig_settings = pos_core.load_settings()
    new_tax_rate = 8.88
    fetch_json("/api/settings", method="PATCH", data={"tax_rate": new_tax_rate})
    disk_settings = pos_core.load_settings()
    assert disk_settings["tax_rate"] == new_tax_rate, f"Tax rate not updated in settings.json! Got {disk_settings['tax_rate']}"
    # Revert back to original
    fetch_json("/api/settings", method="PATCH", data={"tax_rate": orig_settings["tax_rate"]})
    print(f"      Settings PATCH immediately wrote to settings.json and verified.")

    print("[5/5] Testing Real-Time Product CRUD on disk...")
    # Add product
    new_item = fetch_json("/api/products", method="POST", data={
        "name": "Live Sync Test Item",
        "price": 4.20,
        "stock": 15,
        "category": "Beverages",
        "barcode": "8909999"
    })["product"]
    new_id = new_item["id"]
    
    # Verify it exists in products.json
    disk_prods = pos_core.load_products()
    assert any(p["id"] == new_id for p in disk_prods), "New product not written to products.json!"

    # Delete product
    del_res = fetch_json(f"/api/products/{new_id}", method="DELETE")
    assert del_res["success"] is True

    # Verify it was removed from products.json
    disk_prods_after = pos_core.load_products()
    assert not any(p["id"] == new_id for p in disk_prods_after), "Deleted product still in products.json!"
    print(f"      Product CRUD immediately persisted to and deleted from products.json on disk.")

    # Restore stock for item 101
    pos_core.update_product(101, {"stock": initial_stock})
    print("\nALL SYNCHRONIZATION TESTS PASSED WITH 100% DISK-BACKEND INTEGRITY!")

if __name__ == "__main__":
    test_sync()
