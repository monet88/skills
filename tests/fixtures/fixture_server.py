import http.server
import json
import socketserver
import sys
import urllib.parse


class StoreHandler(http.server.SimpleHTTPRequestHandler):
    items = [
        {
            "id": f"item-{i+1}",
            "title": f"Product {i+1}",
            "price": (i + 1) * 10,
            "category": "electronics" if i % 2 == 0 else "books",
        }
        for i in range(30)
    ]

    def log_message(self, format, *args):
        # Silence default request logging to avoid stderr/stdout pollution
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/catalog":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head><title>Test Store Catalog</title></head>
<body>
  <h1>Product Catalog</h1>
  <div id="controls">
    <input id="search-input" placeholder="Search products..." />
    <select id="category-select">
      <option value="">All Categories</option>
      <option value="electronics">Electronics</option>
      <option value="books">Books</option>
    </select>
  </div>
  <ul id="items-list"></ul>
  <script>
    fetch('/api/items?page=1&limit=5')
      .then(r => r.json())
      .then(data => {
        const list = document.getElementById('items-list');
        data.items.forEach(it => {
          const li = document.createElement('li');
          li.className = 'product-card';
          li.textContent = it.title + ' - $' + it.price;
          list.appendChild(li);
        });
      });
  </script>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
            return

        if parsed.path == "/api/items":
            qs = urllib.parse.parse_qs(parsed.query)
            q = (qs.get("q", [""])[0]).lower()
            page = int(qs.get("page", ["1"])[0])
            limit = int(qs.get("limit", ["10"])[0])
            cat = qs.get("category", [None])[0]

            filtered = self.items
            if q:
                filtered = [it for it in filtered if q in it["title"].lower()]
            if cat:
                filtered = [it for it in filtered if it["category"] == cat]

            start = (page - 1) * limit
            paginated = filtered[start : start + limit]
            has_more = (start + limit) < len(filtered)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "items": paginated,
                "page": page,
                "limit": limit,
                "total": len(filtered),
                "has_more": has_more,
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        if parsed.path == "/api/categories":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "categories": [
                            {"slug": "electronics", "name": "Electronics"},
                            {"slug": "books", "name": "Books"},
                        ]
                    }
                ).encode("utf-8")
            )
            return

        if parsed.path == "/api/session-only":
            auth = self.headers.get("x-browser-session-token")
            if not auth or auth != "valid-session-123":
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "error": True,
                            "code": "FORBIDDEN",
                            "message": "Browser session required",
                        }
                    ).encode("utf-8")
                )
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"secret_data": "authenticated-session-data"}).encode(
                    "utf-8"
                )
            )
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")


def main():
    server = socketserver.TCPServer(("127.0.0.1", 0), StoreHandler)
    port = server.server_address[1]
    print(f"READY:{port}", flush=True)
    try:
        server.serve_forever()
    except Exception:
        pass


if __name__ == "__main__":
    main()
