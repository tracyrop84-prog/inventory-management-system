# Inventory Management System

An administrator portal for a small retail e-commerce store, built with **Flask**. Employees can add, view, update and delete inventory items through a REST API or an interactive command-line interface (CLI). Product details are supplemented with real-time data from the [OpenFoodFacts API](https://openfoodfacts.github.io/openfoodfacts-server/api/).

## Features

- **REST API** with full CRUD for inventory items (Flask)
- **OpenFoodFacts integration**: look up products by barcode or name, import them straight into inventory, and enrich existing items with missing details
- **Interactive CLI** to manage inventory and search OpenFoodFacts
- **Input validation and error handling** for bad input, missing items and external API failures (always JSON responses)
- **Test suite** (pytest + `unittest.mock`) covering every feature, with no real network calls

## Project Structure

```
inventory-management-system/
├── app.py              # Flask app: CRUD routes, OpenFoodFacts helper routes, error handlers
├── data.py             # Mock in-memory database (array) + helper functions
├── external_api.py     # Functions that call the OpenFoodFacts API
├── cli.py              # Interactive command-line interface
├── requirements.txt    # Python dependencies
├── README.md
└── tests/
    ├── conftest.py              # Shared fixtures (Flask test client, inventory reset)
    ├── test_data.py             # Mock database tests
    ├── test_routes.py           # CRUD endpoint tests
    ├── test_external_api.py     # OpenFoodFacts function tests (mocked requests)
    ├── test_external_routes.py  # Lookup / search / import / enrich route tests
    └── test_cli.py              # CLI command tests (mocked input and HTTP)
```

## Installation and Setup

**Requirements:** Python 3.10+ and Git.

```bash
# 1. Clone the repository
git clone https://github.com/tracyrop84-prog/inventory-management-system.git
cd inventory-management-system

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Mac / Linux / WSL
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

## Running the Application

**Start the API** (runs in debug mode on http://127.0.0.1:5000):

```bash
python app.py
```

**Start the CLI** in a second terminal (with the venv activated):

```bash
python cli.py
```

## Data Model

Inventory is stored in an in-memory array in `data.py` (data resets when the server restarts). Each item mirrors the structure of an OpenFoodFacts product, plus store-specific fields:

```json
{
  "id": 1,
  "barcode": "025293600232",
  "product_name": "Organic Almond Milk",
  "brands": "Silk",
  "ingredients_text": "Filtered water, almonds, cane sugar, sea salt, natural flavors",
  "categories": "Plant-based milks",
  "nutriscore_grade": "b",
  "image_url": "",
  "price": 4.99,
  "stock": 25
}
```

## API Endpoints

### Inventory (CRUD)

| Method | Endpoint | Description | Body | Success |
|--------|----------|-------------|------|---------|
| GET | `/inventory` | Fetch all items | none | 200 |
| GET | `/inventory/<id>` | Fetch a single item | none | 200 |
| POST | `/inventory` | Add a new item (`product_name` required) | JSON item fields | 201 |
| PATCH | `/inventory/<id>` | Update only the fields sent | JSON fields to change | 200 |
| DELETE | `/inventory/<id>` | Remove an item | none | 200 |

### OpenFoodFacts helper routes

| Method | Endpoint | Description | Body | Success |
|--------|----------|-------------|------|---------|
| GET | `/products/barcode/<barcode>` | Look up a product on OpenFoodFacts by barcode | none | 200 |
| GET | `/products/search?name=<name>` | Search OpenFoodFacts by product name | none | 200 |
| POST | `/inventory/import` | Fetch a product by barcode and add it to inventory | `{"barcode": "...", "price": 3.25, "stock": 15}` | 201 |
| PATCH | `/inventory/<id>/enrich` | Fill an item's empty fields with OpenFoodFacts data | none | 200 |

### Validation and error responses

All errors are returned as JSON, e.g. `{"error": "Item 99 not found"}`.

| Status | When |
|--------|------|
| 400 | Invalid input (missing `product_name`, negative price, non-integer stock, unknown fields, non-numeric barcode) |
| 404 | Item or product not found, or unknown route |
| 405 | HTTP method not allowed on that route |
| 409 | Importing a barcode that is already in inventory |
| 502 | OpenFoodFacts is unreachable or returned an error |

### Example requests (curl)

```bash
# Get all items
curl http://127.0.0.1:5000/inventory

# Add an item
curl -X POST http://127.0.0.1:5000/inventory \
  -H "Content-Type: application/json" \
  -d '{"product_name": "Brown Bread", "brands": "Festive", "price": 0.9, "stock": 30}'

# Update price and stock
curl -X PATCH http://127.0.0.1:5000/inventory/1 \
  -H "Content-Type: application/json" \
  -d '{"price": 5.49, "stock": 20}'

# Delete an item
curl -X DELETE http://127.0.0.1:5000/inventory/3

# Look up a product on OpenFoodFacts
curl http://127.0.0.1:5000/products/barcode/737628064502

# Import a product from OpenFoodFacts into inventory
curl -X POST http://127.0.0.1:5000/inventory/import \
  -H "Content-Type: application/json" \
  -d '{"barcode": "737628064502", "price": 3.25, "stock": 15}'
```

These requests can also be run in **Postman**.

## CLI Usage

```
===== Inventory Management =====
  1. View all items
  2. View one item
  3. Add an item
  4. Update price / stock
  5. Delete an item
  6. Find product on OpenFoodFacts
  7. Enrich item with OpenFoodFacts data
  0. Exit
Choose an option:
```

**Example: find a product by barcode and add it to inventory**

```
Choose an option: 6

  Search OpenFoodFacts by:
  1. Barcode
  2. Product name
Choose 1 or 2: 1
Barcode: 737628064502

[-] Thai peanut noodle kit includes stir-fry rice noodles & thai peanut seasoning
    Brand:       Simply Asia, Thai Kitchen
    Barcode:     737628064502
    ...

Add this product to inventory? (y/n): y
Price: 3.25
Stock quantity: 15

  Product added to inventory:
[4] Thai peanut noodle kit ...
```

**Example: update stock**

```
Choose an option: 4
Item ID to update: 1
  Press Enter to keep the current value.
New price:
New stock level: 40

  Item updated:
[1] Organic Almond Milk
    ...
    Stock:       40
```

The CLI re-asks on invalid input (e.g. letters for a price), asks for confirmation before deleting, and shows a clear message if the API server isn't running or OpenFoodFacts is unavailable.

## Running Tests

The tests mock all HTTP calls with `unittest.mock`, so the server does not need to be running and no internet connection is required.

```bash
python -m pytest -v
```

| Test file | Feature covered |
|-----------|-----------------|
| `test_data.py` | Mock database and helper functions |
| `test_routes.py` | GET, POST, PATCH, DELETE endpoints, validation, JSON error handlers |
| `test_external_api.py` | OpenFoodFacts lookup and search, including network errors, timeouts, bad JSON |
| `test_external_routes.py` | Lookup, search, import and enrich routes |
| `test_cli.py` | CLI commands, input validation, menu, server-down handling |

## Git Workflow

Each feature was developed on its own branch, merged into `main` through a pull request, then deleted:

`feature/mock-data` → `feature/crud-routes` → `feature/external-api` → `feature/cli` → `feature/tests` → `feature/readme`

## Technologies

- Python 3, Flask, Requests
- pytest, unittest.mock
- OpenFoodFacts API
- Git and GitHub

## Author

[tracyrop84-prog](https://github.com/tracyrop84-prog)