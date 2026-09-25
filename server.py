import http.server
import json
import os
import socket
import sys
import urllib.parse
from datetime import datetime
from http import HTTPStatus

import pos_core

PORT = 8000
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class POSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def send_json(self, status_code, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, status_code, message):
        self.send_json(status_code, {"error": message, "success": False})

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise ValueError("Malformed JSON in request body.")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Route root to index.html
        if path in ["/", ""]:
            self.path = "/index.html"
            return super().do_GET()

        # Settings endpoint
        if path == "/api/settings":
            settings = pos_core.load_settings()
            return self.send_json(HTTPStatus.OK, {"settings": settings, "success": True})

        # Storage sync check endpoint
        if path == "/api/sync":
            products_file = pos_core.PRODUCTS_FILE
            tx_file = pos_core.TRANSACTIONS_FILE
            settings_file = pos_core.SETTINGS_FILE
            receipt_file = pos_core.RECEIPT_FILE

            def file_info(fpath):
                if os.path.exists(fpath):
                    stat = os.stat(fpath)
                    return {
                        "exists": True,
                        "filename": os.path.basename(fpath),
                        "abs_path": fpath,
                        "size_bytes": stat.st_size,
                        "mtime": stat.st_mtime,
                        "mtime_str": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    }
                return {
                    "exists": False,
                    "filename": os.path.basename(fpath),
                    "abs_path": fpath,
                    "size_bytes": 0,
                    "mtime": 0,
                    "mtime_str": "Not created"
                }

            def get_local_ip():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    ip = s.getsockname()[0]
                    s.close()
                    return ip
                except Exception:
                    return "127.0.0.1"

            products = pos_core.load_products()
            transactions = pos_core.load_transactions()
            local_ip = get_local_ip()

            sync_meta = {
                "python_version": sys.version.split()[0],
                "server_status": "online",
                "local_ip": local_ip,
                "port": PORT,
                "phone_connect_url": f"http://{local_ip}:{PORT}",
                "products_mtime": os.path.getmtime(products_file) if os.path.exists(products_file) else 0,
                "transactions_mtime": os.path.getmtime(tx_file) if os.path.exists(tx_file) else 0,
                "settings_mtime": os.path.getmtime(settings_file) if os.path.exists(settings_file) else 0,
                "receipt_mtime": os.path.getmtime(receipt_file) if os.path.exists(receipt_file) else 0,
                "products_count": len(products),
                "transactions_count": len(transactions),
                "storage_directory": pos_core.BASE_DIR,
                "files": {
                    "products": file_info(products_file),
                    "transactions": file_info(tx_file),
                    "settings": file_info(settings_file),
                    "receipt": file_info(receipt_file)
                }
            }
            return self.send_json(HTTPStatus.OK, {"sync": sync_meta, "success": True})

        # Products API
        if path == "/api/products":
            barcode = query.get("barcode", [None])[0]
            if barcode:
                match = pos_core.find_product_by_barcode(barcode)
                if match:
                    return self.send_json(HTTPStatus.OK, {"product": match, "success": True})
                return self.send_error_json(HTTPStatus.NOT_FOUND, f"No product with barcode '{barcode}' found.")

            products = pos_core.load_products()
            category = query.get("category", [None])[0]
            search = query.get("q", [None])[0]

            if category and category.lower() != "all":
                products = [p for p in products if p.get("category", "").lower() == category.lower()]
            if search:
                s = search.lower()
                products = [
                    p for p in products
                    if s in p.get("name", "").lower()
                    or str(p.get("id")) == s
                    or s in str(p.get("barcode", "")).lower()
                ]

            return self.send_json(HTTPStatus.OK, {"products": products, "success": True})

        if path == "/api/transactions":
            transactions = pos_core.load_transactions()
            return self.send_json(HTTPStatus.OK, {"transactions": list(reversed(transactions)), "success": True})

        if path == "/api/stats":
            stats = pos_core.get_analytics()
            return self.send_json(HTTPStatus.OK, {"stats": stats, "success": True})

        if path.startswith("/api/receipt/"):
            tx_id = path.split("/api/receipt/")[1]
            transactions = pos_core.load_transactions()
            match = next((t for t in transactions if t["id"] == tx_id), None)
            if match:
                return self.send_json(HTTPStatus.OK, {"receipt": match, "success": True})
            return self.send_error_json(HTTPStatus.NOT_FOUND, "Transaction not found.")

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            body = self.read_json_body()
        except ValueError as e:
            return self.send_error_json(HTTPStatus.BAD_REQUEST, str(e))

        if path == "/api/products":
            name = body.get("name")
            price = body.get("price")
            stock = body.get("stock")
            category = body.get("category")
            barcode = body.get("barcode")
            modifiers = body.get("available_modifiers")
            icon = body.get("icon")

            try:
                item = pos_core.add_product(name, price, stock, category, barcode, modifiers, icon=icon)
                return self.send_json(HTTPStatus.CREATED, {"product": item, "success": True})
            except ValueError as e:
                return self.send_error_json(HTTPStatus.BAD_REQUEST, str(e))
            except Exception as e:
                return self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Server error: {str(e)}")

        if path == "/api/checkout":
            cart_items = body.get("items", [])
            cash = body.get("cash_received", 0)
            cashier = body.get("cashier", "Terminal 01")

            try:
                tx = pos_core.process_checkout(cart_items, cash, cashier)
                return self.send_json(HTTPStatus.OK, {"transaction": tx, "success": True})
            except ValueError as e:
                return self.send_error_json(HTTPStatus.BAD_REQUEST, str(e))
            except Exception as e:
                return self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Checkout failed: {str(e)}")

        return self.send_error_json(HTTPStatus.NOT_FOUND, "Endpoint not found.")

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            body = self.read_json_body()
        except ValueError as e:
            return self.send_error_json(HTTPStatus.BAD_REQUEST, str(e))

        if path == "/api/settings":
            try:
                updated = pos_core.update_settings(body)
                return self.send_json(HTTPStatus.OK, {"settings": updated, "success": True})
            except ValueError as e:
                return self.send_error_json(HTTPStatus.BAD_REQUEST, str(e))

        if path.startswith("/api/products/"):
            try:
                pid = int(path.split("/api/products/")[1])
            except ValueError:
                return self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid product ID.")

            try:
                updated = pos_core.update_product(pid, body)
                return self.send_json(HTTPStatus.OK, {"product": updated, "success": True})
            except ValueError as e:
                return self.send_error_json(HTTPStatus.BAD_REQUEST, str(e))
            except Exception as e:
                return self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Update failed: {str(e)}")

        return self.send_error_json(HTTPStatus.NOT_FOUND, "Endpoint not found.")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/products/"):
            try:
                pid = int(path.split("/api/products/")[1])
            except ValueError:
                return self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid product ID.")

            success = pos_core.delete_product(pid)
            if success:
                return self.send_json(HTTPStatus.OK, {"message": f"Product {pid} deleted.", "success": True})
            return self.send_error_json(HTTPStatus.NOT_FOUND, f"Product {pid} not found.")

        return self.send_error_json(HTTPStatus.NOT_FOUND, "Endpoint not found.")


def run_server(port=PORT):
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)

    server_address = ("0.0.0.0", port)
    httpd = http.server.ThreadingHTTPServer(server_address, POSRequestHandler)
    print(f"==================================================")
    print(f"  Point of Sale Server running at:")
    print(f"  Local:   http://localhost:{port}")
    print(f"  Network: http://127.0.0.1:{port}")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.shutdown()


if __name__ == "__main__":
    port = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
