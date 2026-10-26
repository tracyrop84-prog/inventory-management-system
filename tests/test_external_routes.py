"""Tests for the OpenFoodFacts helper routes in app.py."""

from unittest.mock import patch

import data
from external_api import ExternalAPIError

API_PRODUCT = {
    "barcode": "737628064502",
    "product_name": "Thai peanut noodle kit",
    "brands": "Simply Asia",
    "ingredients_text": "Rice noodles, peanuts, sugar",
    "categories": "Noodles",
    "nutriscore_grade": "d",
    "image_url": "https://example.com/image.jpg",
}


# ---------- GET /products/barcode/<barcode> ----------

@patch("app.fetch_product_by_barcode", return_value=API_PRODUCT)
def test_lookup_barcode_success(mock_fetch, client):
    response = client.get("/products/barcode/737628064502")
    assert response.status_code == 200
    assert response.get_json()["brands"] == "Simply Asia"
    mock_fetch.assert_called_once_with("737628064502")


@patch("app.fetch_product_by_barcode", return_value=None)
def test_lookup_barcode_not_found(mock_fetch, client):
    response = client.get("/products/barcode/000000")
    assert response.status_code == 404


def test_lookup_barcode_rejects_non_digits(client):
    response = client.get("/products/barcode/abc123")
    assert response.status_code == 400


@patch("app.fetch_product_by_barcode", side_effect=ExternalAPIError("down"))
def test_lookup_barcode_api_failure_returns_502(mock_fetch, client):
    response = client.get("/products/barcode/737628064502")
    assert response.status_code == 502


# ---------- GET /products/search ----------

@patch("app.search_products_by_name", return_value=[API_PRODUCT])
def test_search_success(mock_search, client):
    response = client.get("/products/search?name=noodle")
    assert response.status_code == 200
    assert len(response.get_json()) == 1
    mock_search.assert_called_once_with("noodle")


def test_search_requires_name(client):
    response = client.get("/products/search")
    assert response.status_code == 400


@patch("app.search_products_by_name", side_effect=ExternalAPIError("down"))
def test_search_api_failure_returns_502(mock_search, client):
    response = client.get("/products/search?name=milk")
    assert response.status_code == 502


# ---------- POST /inventory/import ----------

@patch("app.fetch_product_by_barcode", return_value=API_PRODUCT)
def test_import_adds_product_to_inventory(mock_fetch, client):
    response = client.post(
        "/inventory/import", json={"barcode": "737628064502", "price": 3.25, "stock": 15}
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 4
    assert body["product_name"] == "Thai peanut noodle kit"
    assert body["price"] == 3.25
    assert body["stock"] == 15
    assert len(data.inventory) == 4


@patch("app.fetch_product_by_barcode", return_value={**API_PRODUCT, "product_name": ""})
def test_import_uses_fallback_name_when_missing(mock_fetch, client):
    response = client.post("/inventory/import", json={"barcode": "737628064502"})
    assert response.status_code == 201
    assert response.get_json()["product_name"] == "Unknown product"


@patch("app.fetch_product_by_barcode")
def test_import_duplicate_barcode_returns_409(mock_fetch, client):
    # Nutella's barcode is already in the mock inventory
    response = client.post("/inventory/import", json={"barcode": "3017620422003"})
    assert response.status_code == 409
    mock_fetch.assert_not_called()


def test_import_requires_numeric_barcode(client):
    response = client.post("/inventory/import", json={"barcode": "abc"})
    assert response.status_code == 400


def test_import_rejects_invalid_price(client):
    response = client.post("/inventory/import", json={"barcode": "737628064502", "price": -3})
    assert response.status_code == 400


@patch("app.fetch_product_by_barcode", return_value=None)
def test_import_product_not_found(mock_fetch, client):
    response = client.post("/inventory/import", json={"barcode": "000000"})
    assert response.status_code == 404
    assert len(data.inventory) == 3


@patch("app.fetch_product_by_barcode", side_effect=ExternalAPIError("down"))
def test_import_api_failure_returns_502(mock_fetch, client):
    response = client.post("/inventory/import", json={"barcode": "737628064502"})
    assert response.status_code == 502
    assert len(data.inventory) == 3


# ---------- PATCH /inventory/<id>/enrich ----------

@patch("app.fetch_product_by_barcode")
def test_enrich_fills_only_empty_fields(mock_fetch, client):
    mock_fetch.return_value = {
        **API_PRODUCT,
        "barcode": "025293600232",
        "product_name": "Different Name From API",
    }
    response = client.patch("/inventory/1/enrich")
    assert response.status_code == 200
    body = response.get_json()
    assert body["image_url"] == "https://example.com/image.jpg"  # was empty -> filled
    assert body["product_name"] == "Organic Almond Milk"          # existing -> kept
    assert body["price"] == 4.99                                  # never overwritten


def test_enrich_missing_item_returns_404(client):
    response = client.patch("/inventory/999/enrich")
    assert response.status_code == 404


def test_enrich_item_without_barcode_returns_400(client):
    client.post("/inventory", json={"product_name": "Homemade Jam"})
    response = client.patch("/inventory/4/enrich")
    assert response.status_code == 400


@patch("app.fetch_product_by_barcode", return_value=None)
def test_enrich_product_not_found(mock_fetch, client):
    response = client.patch("/inventory/1/enrich")
    assert response.status_code == 404


@patch("app.fetch_product_by_barcode", side_effect=ExternalAPIError("down"))
def test_enrich_api_failure_returns_502(mock_fetch, client):
    response = client.patch("/inventory/1/enrich")
    assert response.status_code == 502