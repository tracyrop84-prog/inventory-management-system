"""Tests for cli.py. User input and HTTP calls are mocked."""

from unittest.mock import Mock, patch

import pytest
import requests

import cli

ITEM = {
    "id": 1,
    "barcode": "025293600232",
    "product_name": "Organic Almond Milk",
    "brands": "Silk",
    "ingredients_text": "Filtered water, almonds",
    "categories": "Plant-based milks",
    "nutriscore_grade": "b",
    "image_url": "",
    "price": 4.99,
    "stock": 25,
}


# ---------- api_request ----------

@patch("cli.requests.request")
def test_api_request_returns_status_and_data(mock_request):
    mock_request.return_value = Mock(status_code=200, json=Mock(return_value=[ITEM]))
    status, data = cli.api_request("GET", "/inventory")
    assert status == 200
    assert data == [ITEM]
    assert mock_request.call_args[0] == ("GET", "http://127.0.0.1:5000/inventory")


@patch("cli.requests.request", side_effect=requests.ConnectionError("refused"))
def test_api_request_raises_when_server_down(mock_request):
    with pytest.raises(cli.APIConnectionError):
        cli.api_request("GET", "/inventory")


@patch("cli.requests.request")
def test_api_request_handles_invalid_json(mock_request):
    mock_request.return_value = Mock(status_code=500, json=Mock(side_effect=ValueError))
    status, data = cli.api_request("GET", "/inventory")
    assert status == 500
    assert "error" in data


# ---------- Input helpers ----------

@patch("builtins.input", side_effect=["abc", "-1", "5"])
def test_prompt_int_reasks_until_valid(mock_input):
    assert cli.prompt_int("Number: ") == 5
    assert mock_input.call_count == 3


@patch("builtins.input", side_effect=[""])
def test_prompt_int_blank_allowed_returns_none(mock_input):
    assert cli.prompt_int("Number: ", allow_blank=True) is None


@patch("builtins.input", side_effect=["free", "-2", "4.999"])
def test_prompt_float_reasks_until_valid(mock_input):
    assert cli.prompt_float("Price: ") == 5.0


@patch("builtins.input", side_effect=["", "  ", "Milk"])
def test_prompt_text_required(mock_input):
    assert cli.prompt_text("Name: ") == "Milk"


def test_format_item_shows_key_details():
    text = cli.format_item(ITEM)
    assert "Organic Almond Milk" in text
    assert "4.99" in text
    assert "Silk" in text


# ---------- View ----------

@patch("cli.api_request", return_value=(200, [ITEM]))
def test_view_all_items(mock_api, capsys):
    cli.view_all_items()
    output = capsys.readouterr().out
    assert "1 item(s)" in output
    assert "Organic Almond Milk" in output


@patch("cli.api_request", return_value=(200, []))
def test_view_all_items_empty(mock_api, capsys):
    cli.view_all_items()
    assert "Inventory is empty" in capsys.readouterr().out


@patch("cli.api_request", return_value=(404, {"error": "Item 9 not found"}))
@patch("builtins.input", side_effect=["9"])
def test_view_item_not_found(mock_input, mock_api, capsys):
    cli.view_item()
    assert "Item 9 not found" in capsys.readouterr().out


# ---------- Add ----------

@patch("cli.api_request", return_value=(201, {**ITEM, "id": 4, "product_name": "Bread"}))
@patch("builtins.input", side_effect=["Bread", "Festive", "", "Bakery", "0.9", "30"])
def test_add_item_sends_payload(mock_input, mock_api, capsys):
    cli.add_item()
    mock_api.assert_called_once_with(
        "POST",
        "/inventory",
        json={
            "product_name": "Bread",
            "brands": "Festive",
            "barcode": "",
            "categories": "Bakery",
            "price": 0.9,
            "stock": 30,
        },
    )
    assert "Item added" in capsys.readouterr().out


# ---------- Update ----------

@patch("cli.api_request", return_value=(200, {**ITEM, "price": 5.49}))
@patch("builtins.input", side_effect=["1", "5.49", ""])
def test_update_item_price_only(mock_input, mock_api):
    cli.update_item()
    mock_api.assert_called_once_with("PATCH", "/inventory/1", json={"price": 5.49})


@patch("cli.api_request")
@patch("builtins.input", side_effect=["1", "", ""])
def test_update_item_nothing_to_update(mock_input, mock_api, capsys):
    cli.update_item()
    mock_api.assert_not_called()
    assert "Nothing to update" in capsys.readouterr().out


# ---------- Delete ----------

@patch("cli.api_request", return_value=(200, {"message": "Item 1 deleted"}))
@patch("builtins.input", side_effect=["1", "y"])
def test_delete_item_confirmed(mock_input, mock_api, capsys):
    cli.delete_item()
    mock_api.assert_called_once_with("DELETE", "/inventory/1")
    assert "Item 1 deleted" in capsys.readouterr().out


@patch("cli.api_request")
@patch("builtins.input", side_effect=["1", "n"])
def test_delete_item_cancelled(mock_input, mock_api, capsys):
    cli.delete_item()
    mock_api.assert_not_called()
    assert "cancelled" in capsys.readouterr().out


# ---------- Find on OpenFoodFacts ----------

@patch("cli.api_request")
@patch("builtins.input", side_effect=["1", "737628064502", "y", "3.25", "15"])
def test_find_by_barcode_and_import(mock_input, mock_api, capsys):
    product = {**ITEM, "barcode": "737628064502", "product_name": "Noodle kit"}
    mock_api.side_effect = [(200, product), (201, {**product, "id": 4})]

    cli.find_on_api()

    assert mock_api.call_args_list[0].args == ("GET", "/products/barcode/737628064502")
    mock_api.assert_called_with(
        "POST", "/inventory/import",
        json={"barcode": "737628064502", "price": 3.25, "stock": 15},
    )
    assert "added to inventory" in capsys.readouterr().out


@patch("cli.api_request")
@patch("builtins.input", side_effect=["1", "abc"])
def test_find_by_barcode_rejects_letters(mock_input, mock_api, capsys):
    cli.find_on_api()
    mock_api.assert_not_called()
    assert "digits only" in capsys.readouterr().out


@patch("cli.api_request")
@patch("builtins.input", side_effect=["2", "noodle", "1", "2.5", "10"])
def test_search_by_name_and_import(mock_input, mock_api):
    product = {**ITEM, "barcode": "737628064502", "product_name": "Noodle kit"}
    mock_api.side_effect = [(200, [product]), (201, {**product, "id": 4})]

    cli.find_on_api()

    assert mock_api.call_args_list[0].kwargs == {"params": {"name": "noodle"}}
    mock_api.assert_called_with(
        "POST", "/inventory/import",
        json={"barcode": "737628064502", "price": 2.5, "stock": 10},
    )


@patch("cli.api_request", return_value=(502, {"error": "Could not reach OpenFoodFacts"}))
@patch("builtins.input", side_effect=["2", "milk"])
def test_search_handles_api_failure(mock_input, mock_api, capsys):
    cli.find_on_api()
    assert "Could not reach OpenFoodFacts" in capsys.readouterr().out


# ---------- Enrich ----------

@patch("cli.api_request", return_value=(200, ITEM))
@patch("builtins.input", side_effect=["1"])
def test_enrich_item(mock_input, mock_api, capsys):
    cli.enrich_item()
    mock_api.assert_called_once_with("PATCH", "/inventory/1/enrich")
    assert "Item enriched" in capsys.readouterr().out


# ---------- Main menu ----------

@patch("builtins.input", side_effect=["9", "0"])
def test_main_invalid_option_then_exit(mock_input, capsys):
    cli.main()
    output = capsys.readouterr().out
    assert "Invalid option" in output
    assert "Goodbye" in output


@patch("cli.api_request", side_effect=cli.APIConnectionError("Server is down"))
@patch("builtins.input", side_effect=["1", "0"])
def test_main_handles_server_down(mock_input, mock_api, capsys):
    cli.main()
    assert "Server is down" in capsys.readouterr().out