"""
cli.py
Command-line interface for the Inventory Management API.

Usage:
    1. Start the API in one terminal:   python app.py
    2. Start the CLI in another:        python cli.py
"""

import requests

API_URL = "http://127.0.0.1:5000"
TIMEOUT = 20  # seconds (OpenFoodFacts searches can be slow)


class APIConnectionError(Exception):
    """Raised when the CLI cannot reach the Flask API."""


# ---------- HTTP helper ----------

def api_request(method, path, json=None, params=None):
    """
    Send a request to the Flask API.
    Returns (status_code, data). Raises APIConnectionError if unreachable.
    """
    try:
        response = requests.request(
            method, f"{API_URL}{path}", json=json, params=params, timeout=TIMEOUT
        )
    except requests.RequestException as exc:
        raise APIConnectionError(
            "Could not connect to the inventory API. Is the server running? (python app.py)"
        ) from exc

    try:
        data = response.json()
    except ValueError:
        data = {"error": "Server returned an invalid response"}
    return response.status_code, data


# ---------- Input helpers (re-ask until the input is valid) ----------

def prompt_text(message, required=True):
    while True:
        value = input(message).strip()
        if value or not required:
            return value
        print("  This field is required.")


def prompt_int(message, allow_blank=False):
    """Ask for a whole number >= 0. Blank returns None if allow_blank."""
    while True:
        value = input(message).strip()
        if allow_blank and value == "":
            return None
        if value.isdigit():
            return int(value)
        print("  Please enter a whole number (0 or more).")


def prompt_float(message, allow_blank=False):
    """Ask for a number >= 0. Blank returns None if allow_blank."""
    while True:
        value = input(message).strip()
        if allow_blank and value == "":
            return None
        try:
            number = float(value)
            if number >= 0:
                return round(number, 2)
        except ValueError:
            pass
        print("  Please enter a valid price (e.g. 4.99).")


def prompt_yes_no(message):
    return input(message).strip().lower() in ("y", "yes")


# ---------- Display helpers ----------

def format_item(item):
    """Return a readable multi-line string for one inventory item."""
    lines = [
        f"[{item.get('id', '-')}] {item.get('product_name') or 'Unnamed product'}",
        f"    Brand:       {item.get('brands') or 'N/A'}",
        f"    Barcode:     {item.get('barcode') or 'N/A'}",
        f"    Category:    {item.get('categories') or 'N/A'}",
        f"    Nutri-Score: {(item.get('nutriscore_grade') or 'N/A').upper()}",
    ]
    if "price" in item:
        lines.append(f"    Price:       {item['price']:.2f}")
    if "stock" in item:
        lines.append(f"    Stock:       {item['stock']}")
    if item.get("ingredients_text"):
        lines.append(f"    Ingredients: {item['ingredients_text']}")
    return "\n".join(lines)


def print_error(data):
    print(f"\n  Error: {data.get('error', 'Something went wrong')}")


# ---------- Menu actions ----------

def view_all_items():
    status, data = api_request("GET", "/inventory")
    if status != 200:
        return print_error(data)
    if not data:
        print("\n  Inventory is empty.")
        return
    print(f"\n  {len(data)} item(s) in inventory:\n")
    for item in data:
        print(format_item(item), "\n")


def view_item():
    item_id = prompt_int("Item ID: ")
    status, data = api_request("GET", f"/inventory/{item_id}")
    if status != 200:
        return print_error(data)
    print("\n" + format_item(data))


def add_item():
    print("\n  Add a new item (press Enter to skip optional fields)")
    payload = {
        "product_name": prompt_text("Product name: "),
        "brands": prompt_text("Brand (optional): ", required=False),
        "barcode": prompt_text("Barcode (optional): ", required=False),
        "categories": prompt_text("Category (optional): ", required=False),
        "price": prompt_float("Price: "),
        "stock": prompt_int("Stock quantity: "),
    }
    status, data = api_request("POST", "/inventory", json=payload)
    if status != 201:
        return print_error(data)
    print("\n  Item added:\n" + format_item(data))


def update_item():
    item_id = prompt_int("Item ID to update: ")
    print("  Press Enter to keep the current value.")
    payload = {}
    price = prompt_float("New price: ", allow_blank=True)
    stock = prompt_int("New stock level: ", allow_blank=True)
    if price is not None:
        payload["price"] = price
    if stock is not None:
        payload["stock"] = stock
    if not payload:
        print("\n  Nothing to update.")
        return

    status, data = api_request("PATCH", f"/inventory/{item_id}", json=payload)
    if status != 200:
        return print_error(data)
    print("\n  Item updated:\n" + format_item(data))


def delete_item():
    item_id = prompt_int("Item ID to delete: ")
    if not prompt_yes_no(f"Are you sure you want to delete item {item_id}? (y/n): "):
        print("\n  Delete cancelled.")
        return
    status, data = api_request("DELETE", f"/inventory/{item_id}")
    if status != 200:
        return print_error(data)
    print(f"\n  {data['message']}")


def import_product(barcode):
    """Ask for price/stock, then import an OpenFoodFacts product into inventory."""
    payload = {
        "barcode": barcode,
        "price": prompt_float("Price: "),
        "stock": prompt_int("Stock quantity: "),
    }
    status, data = api_request("POST", "/inventory/import", json=payload)
    if status != 201:
        return print_error(data)
    print("\n  Product added to inventory:\n" + format_item(data))


def find_on_api():
    print("\n  Search OpenFoodFacts by:")
    print("  1. Barcode")
    print("  2. Product name")
    choice = input("Choose 1 or 2: ").strip()

    if choice == "1":
        barcode = prompt_text("Barcode: ")
        if not barcode.isdigit():
            print("\n  Error: Barcode must contain digits only.")
            return
        status, data = api_request("GET", f"/products/barcode/{barcode}")
        if status != 200:
            return print_error(data)
        print("\n" + format_item(data))
        if prompt_yes_no("\nAdd this product to inventory? (y/n): "):
            import_product(data["barcode"])

    elif choice == "2":
        name = prompt_text("Product name: ")
        print("  Searching OpenFoodFacts...")
        status, data = api_request("GET", "/products/search", params={"name": name})
        if status != 200:
            return print_error(data)
        if not data:
            print("\n  No products found.")
            return
        for number, product in enumerate(data, start=1):
            print(f"\n  ({number})")
            print(format_item(product))

        pick = input("\nEnter a number to add it to inventory (or press Enter to skip): ").strip()
        if not pick:
            return
        if not pick.isdigit() or not 1 <= int(pick) <= len(data):
            print("\n  Invalid choice.")
            return
        chosen = data[int(pick) - 1]
        if not chosen.get("barcode"):
            print("\n  That product has no barcode, so it can't be imported.")
            return
        import_product(chosen["barcode"])

    else:
        print("\n  Invalid choice.")


def enrich_item():
    item_id = prompt_int("Item ID to enrich with OpenFoodFacts data: ")
    status, data = api_request("PATCH", f"/inventory/{item_id}/enrich")
    if status != 200:
        return print_error(data)
    print("\n  Item enriched:\n" + format_item(data))


# ---------- Main menu ----------

MENU_OPTIONS = {
    "1": ("View all items", view_all_items),
    "2": ("View one item", view_item),
    "3": ("Add an item", add_item),
    "4": ("Update price / stock", update_item),
    "5": ("Delete an item", delete_item),
    "6": ("Find product on OpenFoodFacts", find_on_api),
    "7": ("Enrich item with OpenFoodFacts data", enrich_item),
}


def print_menu():
    print("\n===== Inventory Management =====")
    for key, (label, _) in MENU_OPTIONS.items():
        print(f"  {key}. {label}")
    print("  0. Exit")


def main():
    while True:
        print_menu()
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye!")
            break

        option = MENU_OPTIONS.get(choice)
        if option is None:
            print("\n  Invalid option, please choose from the menu.")
            continue

        try:
            option[1]()
        except APIConnectionError as exc:
            print(f"\n  Error: {exc}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")