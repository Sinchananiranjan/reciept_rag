import re
from typing import List, Dict, Any

CATEGORIES = [
    "Groceries",
    "Food",
    "Electronics",
    "Clothing",
    "Travel",
    "Healthcare",
    "Entertainment",
    "Utilities",
    "Shopping",
    "Fuel",
    "Other"
]

CATEGORY_KEYWORDS = {
    "Groceries": ["supermarket", "mart", "fresh", "dmart", "reliance fresh", "more supermarket", "grocery", "milk", "vegetables", "fruit", "bread", "food hall"],
    "Food": ["restaurant", "cafe", "bistro", "pizza", "burger", "coffee", "swiggy", "zomato", "starbucks", "mcdonalds", "kfc", "diner", "bakery"],
    "Electronics": ["amazon", "flipkart", "croma", "reliance digital", "sony", "headphones", "apple", "laptop", "cable", "tech", "mobile", "samsung", "gadgets"],
    "Clothing": ["zara", "h&m", "uniqlo", "pantaloons", "trends", "apparel", "shirt", "pants", "shoes", "fashion", "nike", "adidas"],
    "Travel": ["uber", "ola", "flight", "airways", "hotel", "irctc", "railway", "tours", "make-my-trip", "petrol", "cab", "bus"],
    "Healthcare": ["pharmacy", "apollo", "medplus", "hospital", "clinic", "medicine", "doctor", "health", "lab", "dental"],
    "Entertainment": ["bookmyshow", "pvr", "inox", "cinema", "movie", "gaming", "netflix", "spotify", "concert", "ticket"],
    "Utilities": ["electricity", "water bill", "broadband", "airtel", "jio", "gas", "utility", "bescom"],
    "Fuel": ["petrol", "diesel", "hpcl", "bpcl", "iocl", "shell", "fuel", "gas station"],
    "Shopping": ["mall", "store", "retail", "general store", "shopping", "gift"]
}

class CategorizationService:
    def classify_receipt(self, merchant_name: str, items: List[Dict[str, Any]], raw_text: str = "") -> str:
        merchant_lower = (merchant_name or "").lower()
        items_str = " ".join([item.get("product_name", "").lower() for item in items])
        combined_text = f"{merchant_lower} {items_str} {(raw_text or '').lower()}"

        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", combined_text):
                    return category

        return "Other"

categorization_service = CategorizationService()
