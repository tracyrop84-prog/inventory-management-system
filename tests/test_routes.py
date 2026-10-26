"""Tests for the Flask CRUD endpoints."""

import data


# ---------- GET ----------

def test_get_all_items(client):
    response = client.get("/inventory")
    assert response.status_code == 200
    assert len(response.get_json()) == 3


def test_get_single_item(client):
    response = client.get("/inventory/1")
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Organic Almond Milk"


def test_get_missing_item_returns_404(client):
    response = client.get("/inventory/999")
    assert response.status_code == 404
    assert "error" in response.get_json()


# ---------- POST ----------

def test_create_item(client):
    response = client.post(
        "/inventory",
        json={"product_name": "Brown Bread", "brands": "Festive", "price": 0.9, "stock": 30},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 4
    assert body["product_name"] == "Brown Bread"
    assert len(data.inventory) == 4


def test_create_item_requires_product_name(client):
    response = client.post("/inventory", json={"price": 2.0})
    assert response.status_code == 400
    assert len(data.inventory) == 3


def test_create_item_rejects_negative_price(client):
    response = client.post("/inventory", json={"product_name": "Tea", "price": -1})
    assert response.status_code == 400


def test_create_item_rejects_non_integer_stock(client):
    response = client.post("/inventory", json={"product_name": "Tea", "stock": "ten"})
    assert response.status_code == 400


def test_create_item_rejects_unknown_fields(client):
    response = client.post("/inventory", json={"product_name": "Tea", "colour": "green"})
    assert response.status_code == 400


def test_create_item_without_body_returns_400(client):
    response = client.post("/inventory")
    assert response.status_code == 400


# ---------- PATCH ----------

def test_update_item(client):
    response = client.patch("/inventory/1", json={"price": 5.49, "stock": 20})
    assert response.status_code == 200
    body = response.get_json()
    assert body["price"] == 5.49
    assert body["stock"] == 20
    assert data.find_item(1)["stock"] == 20


def test_update_missing_item_returns_404(client):
    response = client.patch("/inventory/999", json={"price": 1.0})
    assert response.status_code == 404


def test_update_with_invalid_data_returns_400(client):
    response = client.patch("/inventory/1", json={"stock": -5})
    assert response.status_code == 400
    assert data.find_item(1)["stock"] == 25  # unchanged


def test_update_with_empty_body_returns_400(client):
    response = client.patch("/inventory/1", json={})
    assert response.status_code == 400


# ---------- DELETE ----------

def test_delete_item(client):
    response = client.delete("/inventory/3")
    assert response.status_code == 200
    assert data.find_item(3) is None
    assert len(data.inventory) == 2


def test_delete_missing_item_returns_404(client):
    response = client.delete("/inventory/999")
    assert response.status_code == 404


# ---------- Error handlers ----------

def test_unknown_route_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Resource not found"}


def test_wrong_method_returns_json_405(client):
    response = client.put("/inventory/1", json={"price": 1})
    assert response.status_code == 405
    assert "error" in response.get_json()