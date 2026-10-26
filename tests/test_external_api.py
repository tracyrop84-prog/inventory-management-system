"""Tests for external_api.py. requests.get is mocked, so no real network calls."""

from unittest.mock import Mock, patch

import pytest
import requests

from external_api import (
    ExternalAPIError,
    fetch_product_by_barcode,
    normalize_product,
    search_products_by_name,
)

SAMPLE_PRODUCT = {
    "code": "737628064502",
    "product_name": "Thai peanut noodle kit",
    "brands": "Simply Asia",
    "ingredients_text": "Rice noodles, peanuts, sugar",
    "categories": "Noodles",
    "nutriscore_grade": "d",
    "image_url": "https://example.com/image.jpg",
}


def make_response(status_code=200, json_data=None, bad_json=False):
    """Build a fake requests.Response."""
    response = Mock()
    response.status_code = status_code
    if bad_json:
        response.json.side_effect = ValueError("invalid json")
    else:
        response.json.return_value = json_data
    return response


# ---------- normalize_product ----------

def test_normalize_product_maps_fields():
    result = normalize_product(SAMPLE_PRODUCT)
    assert result["barcode"] == "737628064502"
    assert result["product_name"] == "Thai peanut noodle kit"


def test_normalize_product_handles_missing_and_none_values():
    result = normalize_product({"product_name": None})
    assert result["product_name"] == ""
    assert result["brands"] == ""


# ---------- fetch_product_by_barcode ----------

@patch("external_api.requests.get")
def test_fetch_by_barcode_success(mock_get):
    mock_get.return_value = make_response(json_data={"status": 1, "product": SAMPLE_PRODUCT})

    product = fetch_product_by_barcode("737628064502")

    assert product["brands"] == "Simply Asia"
    called_url = mock_get.call_args[0][0]
    assert "737628064502" in called_url
    assert "User-Agent" in mock_get.call_args.kwargs["headers"]


@patch("external_api.requests.get")
def test_fetch_by_barcode_not_found_status_0(mock_get):
    mock_get.return_value = make_response(json_data={"status": 0})
    assert fetch_product_by_barcode("000") is None


@patch("external_api.requests.get")
def test_fetch_by_barcode_not_found_404(mock_get):
    mock_get.return_value = make_response(status_code=404)
    assert fetch_product_by_barcode("000") is None


@patch("external_api.requests.get")
def test_fetch_by_barcode_network_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("no internet")
    with pytest.raises(ExternalAPIError):
        fetch_product_by_barcode("737628064502")


@patch("external_api.requests.get")
def test_fetch_by_barcode_server_error(mock_get):
    mock_get.return_value = make_response(status_code=500)
    with pytest.raises(ExternalAPIError):
        fetch_product_by_barcode("737628064502")


@patch("external_api.requests.get")
def test_fetch_by_barcode_invalid_json(mock_get):
    mock_get.return_value = make_response(bad_json=True)
    with pytest.raises(ExternalAPIError):
        fetch_product_by_barcode("737628064502")


# ---------- search_products_by_name ----------

@patch("external_api.requests.get")
def test_search_by_name_returns_products(mock_get):
    mock_get.return_value = make_response(json_data={"products": [SAMPLE_PRODUCT]})

    results = search_products_by_name("noodle")

    assert len(results) == 1
    assert results[0]["product_name"] == "Thai peanut noodle kit"
    assert mock_get.call_args.kwargs["params"]["search_terms"] == "noodle"


@patch("external_api.requests.get")
def test_search_by_name_no_results(mock_get):
    mock_get.return_value = make_response(json_data={"products": []})
    assert search_products_by_name("zzzz") == []


@patch("external_api.requests.get")
def test_search_by_name_timeout(mock_get):
    mock_get.side_effect = requests.Timeout("too slow")
    with pytest.raises(ExternalAPIError):
        search_products_by_name("milk")