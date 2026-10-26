"""
external_api.py
Functions for talking to the OpenFoodFacts API.
Docs: https://openfoodfacts.github.io/openfoodfacts-server/api/
"""

import requests

BASE_URL = "https://world.openfoodfacts.org"

# OpenFoodFacts asks every app to identify itself with a User-Agent
HEADERS = {"User-Agent": "InventoryManagementSystem/1.0 (Moringa student project)"}
TIMEOUT = 10  # seconds

# Only request the fields we actually store (keeps responses small)
FIELDS = "code,product_name,brands,ingredients_text,categories,nutriscore_grade,image_url"


class ExternalAPIError(Exception):
    """Raised when OpenFoodFacts can't be reached or returns bad data."""


def normalize_product(raw):
    """Convert a raw OpenFoodFacts product into the shape our inventory uses."""
    return {
        "barcode": raw.get("code") or "",
        "product_name": raw.get("product_name") or "",
        "brands": raw.get("brands") or "",
        "ingredients_text": raw.get("ingredients_text") or "",
        "categories": raw.get("categories") or "",
        "nutriscore_grade": raw.get("nutriscore_grade") or "",
        "image_url": raw.get("image_url") or "",
    }


def _get_json(url, params):
    """Make a GET request and return parsed JSON, or raise ExternalAPIError."""
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ExternalAPIError(f"Could not reach OpenFoodFacts: {exc}") from exc

    # OpenFoodFacts returns 404 when a barcode doesn't exist
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise ExternalAPIError(f"OpenFoodFacts returned status {response.status_code}")

    try:
        return response.json()
    except ValueError as exc:
        raise ExternalAPIError("OpenFoodFacts returned invalid JSON") from exc


def fetch_product_by_barcode(barcode):
    """
    Look up a product by barcode.
    Returns a normalized product dict, or None if not found.
    """
    url = f"{BASE_URL}/api/v2/product/{barcode}.json"
    data = _get_json(url, {"fields": FIELDS})

    if not data or data.get("status") != 1:
        return None

    product = normalize_product(data.get("product", {}))
    product["barcode"] = product["barcode"] or str(barcode)
    return product


def search_products_by_name(name, limit=5):
    """
    Search products by name.
    Returns a list of normalized product dicts (may be empty).
    """
    url = f"{BASE_URL}/cgi/search.pl"
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
        "fields": FIELDS,
    }
    data = _get_json(url, params)
    if not data:
        return []
    return [normalize_product(p) for p in data.get("products", [])]