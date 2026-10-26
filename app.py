"""
app.py
Flask REST API for the inventory management system.
Data is stored in the in-memory `inventory` list from data.py.
"""

from flask import Flask, jsonify, request

from data import inventory, get_next_id, find_item
from external_api import (
    ExternalAPIError,
    fetch_product_by_barcode,
    search_products_by_name,
)
app = Flask(__name__)

# Fields a client is allowed to set when creating or updating an item
ALLOWED_FIELDS = {
    "barcode",
    "product_name",
    "brands",
    "ingredients_text",
    "categories",
    "nutriscore_grade",
    "image_url",
    "price",
    "stock",
}


def validate_fields(data, require_name=False):
    """
    Check incoming JSON. Returns an error message string,
    or None if the data is valid.
    """
    if not isinstance(data, dict) or not data:
        return "Request body must be a non-empty JSON object"

    unknown = set(data) - ALLOWED_FIELDS
    if unknown:
        return f"Unknown field(s): {', '.join(sorted(unknown))}"

    if require_name and not str(data.get("product_name", "")).strip():
        return "product_name is required"

    if "price" in data:
        price = data["price"]
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
            return "price must be a non-negative number"

    if "stock" in data:
        stock = data["stock"]
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            return "stock must be a non-negative integer"

    return None


# ---------- CRUD routes ----------

@app.route("/inventory", methods=["GET"])
def get_inventory():
    """GET /inventory -> return all items."""
    return jsonify(inventory), 200


@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    """GET /inventory/<id> -> return one item."""
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": f"Item {item_id} not found"}), 404
    return jsonify(item), 200


@app.route("/inventory", methods=["POST"])
def add_item():
    """POST /inventory -> add a new item. product_name is required."""
    data = request.get_json(silent=True)
    error = validate_fields(data, require_name=True)
    if error:
        return jsonify({"error": error}), 400

    new_item = {
        "id": get_next_id(),
        "barcode": data.get("barcode", ""),
        "product_name": data["product_name"].strip(),
        "brands": data.get("brands", ""),
        "ingredients_text": data.get("ingredients_text", ""),
        "categories": data.get("categories", ""),
        "nutriscore_grade": data.get("nutriscore_grade", ""),
        "image_url": data.get("image_url", ""),
        "price": data.get("price", 0.0),
        "stock": data.get("stock", 0),
    }
    inventory.append(new_item)
    return jsonify(new_item), 201


@app.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    """PATCH /inventory/<id> -> update only the fields sent."""
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": f"Item {item_id} not found"}), 404

    data = request.get_json(silent=True)
    error = validate_fields(data)
    if error:
        return jsonify({"error": error}), 400

    item.update(data)
    return jsonify(item), 200


@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """DELETE /inventory/<id> -> remove an item."""
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": f"Item {item_id} not found"}), 404

    inventory.remove(item)
    return jsonify({"message": f"Item {item_id} deleted", "item": item}), 200


# ---------- Error handlers (always return JSON, never HTML) ----------
# ---------- External API helper routes (OpenFoodFacts) ----------

@app.route("/products/barcode/<barcode>", methods=["GET"])
def lookup_by_barcode(barcode):
    """GET /products/barcode/<barcode> -> look up a product on OpenFoodFacts."""
    if not barcode.isdigit():
        return jsonify({"error": "Barcode must contain digits only"}), 400
    try:
        product = fetch_product_by_barcode(barcode)
    except ExternalAPIError as exc:
        return jsonify({"error": str(exc)}), 502

    if product is None:
        return jsonify({"error": f"No product found for barcode {barcode}"}), 404
    return jsonify(product), 200


@app.route("/products/search", methods=["GET"])
def search_by_name():
    """GET /products/search?name=<name> -> search OpenFoodFacts by name."""
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Query parameter 'name' is required"}), 400
    try:
        results = search_products_by_name(name)
    except ExternalAPIError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(results), 200


@app.route("/inventory/import", methods=["POST"])
def import_item():
    """
    POST /inventory/import -> fetch a product from OpenFoodFacts by barcode
    and add it to the inventory. Body: {"barcode": "...", "price": 1.5, "stock": 10}
    """
    data = request.get_json(silent=True) or {}
    barcode = str(data.get("barcode", "")).strip()
    if not barcode.isdigit():
        return jsonify({"error": "A numeric barcode is required"}), 400

    # Validate optional price/stock using the same rules as POST /inventory
    extras = {key: data[key] for key in ("price", "stock") if key in data}
    if extras:
        error = validate_fields(extras)
        if error:
            return jsonify({"error": error}), 400

    # Don't add the same product twice
    if any(item.get("barcode") == barcode for item in inventory):
        return jsonify({"error": f"Barcode {barcode} is already in inventory"}), 409

    try:
        product = fetch_product_by_barcode(barcode)
    except ExternalAPIError as exc:
        return jsonify({"error": str(exc)}), 502
    if product is None:
        return jsonify({"error": f"No product found for barcode {barcode}"}), 404

    new_item = {
        "id": get_next_id(),
        **product,
        "product_name": product["product_name"] or "Unknown product",
        "price": data.get("price", 0.0),
        "stock": data.get("stock", 0),
    }
    inventory.append(new_item)
    return jsonify(new_item), 201


@app.route("/inventory/<int:item_id>/enrich", methods=["PATCH"])
def enrich_item(item_id):
    """
    PATCH /inventory/<id>/enrich -> fill in any empty fields of an existing
    item using OpenFoodFacts data (looked up by the item's barcode).
    """
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": f"Item {item_id} not found"}), 404
    if not item.get("barcode"):
        return jsonify({"error": "Item has no barcode to look up"}), 400

    try:
        product = fetch_product_by_barcode(item["barcode"])
    except ExternalAPIError as exc:
        return jsonify({"error": str(exc)}), 502
    if product is None:
        return jsonify({"error": f"No product found for barcode {item['barcode']}"}), 404

    # Only fill fields that are currently empty; never overwrite price/stock
    for key, value in product.items():
        if value and not item.get(key):
            item[key] = value
    return jsonify(item), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


if __name__ == "__main__":
    app.run(debug=True, port=5000)