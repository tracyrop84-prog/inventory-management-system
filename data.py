"""
data.py
Simulated in-memory database for the inventory system.
Each item resembles the structure of an OpenFoodFacts product,
with extra fields (id, price, stock) used only by our store.
"""

inventory = [
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
        "stock": 25,
    },
    {
        "id": 2,
        "barcode": "3017620422003",
        "product_name": "Nutella",
        "brands": "Ferrero",
        "ingredients_text": "Sugar, palm oil, hazelnuts, skimmed milk powder, fat-reduced cocoa",
        "categories": "Spreads",
        "nutriscore_grade": "e",
        "image_url": "",
        "price": 6.50,
        "stock": 40,
    },
    {
        "id": 3,
        "barcode": "5449000000996",
        "product_name": "Coca-Cola",
        "brands": "Coca-Cola",
        "ingredients_text": "Carbonated water, sugar, colour (caramel E150d), phosphoric acid, natural flavourings, caffeine",
        "categories": "Sodas",
        "nutriscore_grade": "e",
        "image_url": "",
        "price": 1.20,
        "stock": 100,
    },
]


def get_next_id():
    """Return the next available ID (highest existing ID + 1)."""
    if not inventory:
        return 1
    return max(item["id"] for item in inventory) + 1


def find_item(item_id):
    """Return the item with the given ID, or None if it doesn't exist."""
    return next((item for item in inventory if item["id"] == item_id), None)