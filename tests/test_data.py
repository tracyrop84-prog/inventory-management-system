"""Tests for the mock database and its helper functions."""

import data


def test_every_item_has_a_unique_id():
    ids = [item["id"] for item in data.inventory]
    assert len(ids) == len(set(ids))


def test_items_resemble_openfoodfacts_structure():
    for item in data.inventory:
        for field in ("product_name", "brands", "ingredients_text", "barcode"):
            assert field in item


def test_get_next_id_returns_highest_plus_one():
    assert data.get_next_id() == 4


def test_get_next_id_on_empty_inventory_returns_1():
    data.inventory.clear()
    assert data.get_next_id() == 1


def test_find_item_returns_matching_item():
    assert data.find_item(2)["product_name"] == "Nutella"


def test_find_item_returns_none_when_missing():
    assert data.find_item(999) is None