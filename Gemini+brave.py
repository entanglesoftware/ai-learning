import requests
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re
import unicodedata
from urllib.parse import urlparse
import json

# Load environment variables
load_dotenv()

# Set API keys
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Set up Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')


# Normalize text function
def normalize(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()

# Function to perform Brave Search
def brave_search(query):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": 3,
        "freshness": "week"
    }
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print("❌ Error with Brave Search:", response.status_code)
        return None

# Function to query Gemini using search result
def query_gemini(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("❌ Error querying Gemini:\n", e)
        return None

# Main logic to handle query and fetch results
def search_and_generate_response(query):
    search_results = brave_search(query)

    if search_results and 'web' in search_results and 'results' in search_results['web']:
        top_result = search_results['web']['results'][0]
        title = top_result.get('title')
        url = top_result.get('url')
        description = top_result.get('description', 'No description available')

        print("\n Brave Search Top Result:")
        print(f" Title: {title}")
        print(f" URL: {url}")
        print(f" Snippet: {description}")

        gemini_prompt = (
            f"Based on this web search result:\nTitle: {title}\nURL: {url}\n"
            f"Snippet: {description}\n\n"
            f"Give a useful and updated answer to this query: '{query}'"
        )
        gemini_response = query_gemini(gemini_prompt)

        if gemini_response:
            print("\n Gemini Response (Generated using Brave result):\n", gemini_response)
        else:
            print("❌ No response from Gemini.")
    else:
        print("❌ No search results from Brave Search.")

def extract_wine_info(query):
    quantity_match = re.search(r'(\d+)\s*(qty|quantity)?', query.lower())
    quantity = int(quantity_match.group(1)) if quantity_match else 1
    wine_match = re.search(r'(purchase|buy|get|order)\s+(.*)', query, re.IGNORECASE)
    wine_name = wine_match.group(2).strip() if wine_match else query.strip()
    return wine_name, quantity

def get_wine_details_tool(query):
    wine_name, quantity = extract_wine_info(query)

    if not wine_name:
        return "🍷 Sorry, I couldn't extract the wine name from your query.", None

    try:
        url = 'https://uk.crustaging.com/live-markets/api_buyBid/autosuggestionsearch'
        params = {
            'q': wine_name,
            'exactStockAvailable': 'undefined',
            'limit': 10,
            'searchProducers': 'true',
            'platform': 'web'
        }

        headers = {
            'User-Agent': 'cru-script'
        }

        cookies = {
            'frontend': 'mgmc90d0b0io1vbceg0sh8nbl9',
            'frontend_cid': 'SK9WNt8zBeqmbFIZ',
            'session_hash': '29983',
            'CACHED_FRONT_FORM_KEY': 'RZWBEWMAUGMO5qqo'
        }

        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        print("Status Code:", response.status_code)

        if response.status_code != 200:
            return f"❌ API returned error code {response.status_code}", None

        products = response.json()
        output = []
        valid_product_id = None
        lwin = None

        if products.get('found'):
            for item in products.get('data', []):
                item_type = item.get('type')
                entries = item.get('data', [])

                if item_type == 'producer':
                    for producer in entries:
                        output.append(
                            f" Producer: {producer.get('name', 'No name')}\n"
                            f" Image URL: {producer.get('image_url', 'No image')}\n"
                        )
                elif item_type == 'product':
                    for product in entries:
                        product_url = product.get('url', '')
                        lwin = product.get('lwin', '')
                        if lwin:
                            req_path = product_url.split('/')[3] if '/' in product_url else ''
                            detailed_info, valid_product_id, qty_available = get_product_details_by_req_path(req_path, lwin)


                            output.append(
                                f" Product: {product.get('name', 'No name')}\n"
                                f" Image URL: {product.get('image_url', 'No image')}\n"
                                f" LWIN: {lwin}\n"
                                f" URL: {product_url}\n"
                                f"  Product Detailed Info:\n{json.dumps(detailed_info, indent=2)}\n"
                            )
                        else:
                            output.append(
                                f" Product: {product.get('name', 'No name')}\n"
                                f" Image URL: {product.get('image_url', 'No image')}\n"
                                f" LWIN: Not available\n"
                                f" URL: {product_url}\n"
                            )

        # if valid_product_id:
        #     last_viewed_wine = {}
        #     last_viewed_wine["name"] = wine_name.lower()
        #     last_viewed_wine["lwin"] = lwin
        #     last_viewed_wine["product_id"] = valid_product_id
        #         # Step 2: Add product to the cart
        # if valid_product_id:
        #     get_product_details_by_req_path(req_path, lwin) # Function to add product to the cart
        #     gemini_output = generate_gemini_response_from_wine_data(user_query, wine_data_formatted)
        if valid_product_id:
            add_to_cart_result = add_to_cart(valid_product_id, quantity)
            output.append(add_to_cart_result)


        return "\n".join(output), valid_product_id


    except Exception as e:
        return f"❌ Error fetching wine details: {e}", None


# Function to get product details by req_path and Lwin


def get_product_details_by_req_path(req_path, lwin):
    try:
        if not req_path or not lwin:
            return "❌ req_path or lwin is missing."

        req_path = req_path.lstrip('/')
        url = f"https://uk.crustaging.com/live-markets/api_pdp/get?req_path={req_path}&lwin={lwin}&offer_type=cru&selected_transfer_type=storage&platform=web"
        print(f"Product Detail API URL: {url}")

        headers = {
            'User-Agent': 'cru-script'
        }

        response = requests.get(url, headers=headers)
        print("Status Code (Product Details):", response.status_code)

        if response.status_code != 200:
            print(f"Error Details: {response.text}")
            return f"❌ Product detail API returned error {response.status_code}"

        product_detail = response.json()

        if 'main_details' in product_detail and product_detail['main_details']:
            main_details = product_detail['main_details']
            print("Starting Product Details:")
            print(f"Short Name: {main_details.get('short_name', 'No short name')}")
            print(f"Description: {main_details.get('description', 'No description available')}")
            print(f"Image URL: {main_details.get('image_url', 'No image available')}")
            print(f"Stock Location: {main_details.get('stock_location', 'No stock location')}")
            print(f"Stock Location ETA: {main_details.get('stock_location_eta', 'No ETA available')}")

        buy_details = product_detail.get('buy_details', [])
        product_found = False

        for item in buy_details:
            product_id = item.get('product_id')
            unit_qty_info = item.get('unit_qty_info', {})
            print("  DEBUG: unit_qty_info:", unit_qty_info)
            qty_available_raw = unit_qty_info.get('qty_available')

            try:
                qty_available = int(qty_available_raw)
            except (ValueError, TypeError):
                qty_available = 0

            print(" DEBUG:", {
                "product_id": product_id,
                "qty_available": qty_available
            })

            if product_id and qty_available and qty_available > 0:
                print("Product available to add to cart:")
                print(f"PRODUCT ID: {product_id}")
                print(f"Qty Available: {qty_available}")
                product_found = True
                return product_detail, product_id, qty_available

        return product_detail, None, 0

    except Exception as e:
        print(f" Error fetching product details: {e}")
        return {}



def add_to_cart(product_id, quantity):
    add_to_cart_url = "https://uk.crustaging.com/live-markets/api_cart/addToCart"
    payload = {
        "availability": "available",
        "condition_status": "verified",
        "escape": True,
        "platform": "web",
        "product": product_id,
        "qty": quantity,  # corrected to use `quantity` from function parameter
        "skip_mini_cart": 1,
        "special_price": 0.0000,
        "status": "on_bpo",
        "uenc": "",
        "warehouse_id": 52
    }

    headers_post = {
        "Content-Type": "application/json",
        "User-Agent": "cru-script"
    }

    try:
        response = requests.post(add_to_cart_url, headers=headers_post, json=payload)
        print(f"Status Code (Add to Cart): {response.status_code}")

        if response.status_code == 200:
            response_json = response.json()
            print(" Product added to cart successfully!")

            cart_items = response_json.get("cart_items", [])
            if cart_items:
                item = cart_items[0]
                print("Item Details:")
                print(f" Item ID: {item.get('item_id')}")
                print(f" Product ID: {item.get('product_id')}")
                print(f" Name: {item.get('name')}")
                print(f" Short Name: {item.get('short_name')}")
                print(f" Quantity: {item.get('quantity')}")
                print(f" Price: {item.get('price')}")
                print(f" Price (incl. tax): {item.get('price_including_tax')}")
                print(f" Tax: {item.get('tax')}")
                print(f" Row Total: {item.get('row_total')}")
                print(f" Row Total (incl. tax): {item.get('row_total_including_tax')}")
                print(f" Product Type: {item.get('product_type')}")
                print(f" LWIN: {item.get('lwin')}")
                print(f" Vintage: {item.get('vintage')}")
                print(f" Format: {item.get('format')}")
            else:
                print("ℹNo cart items found in response.")
        else:
            print(f" API Error: {response.text}")
    except Exception as e:
        print(f" Exception occurred: {e}")


def classify_user_intent(query):
    """Classify user's intent: add to cart, get stock, description, image, or general info."""
    query = query.lower()

    # Check for 'add to cart' intent first
    if "add" in query and ("to my cart" in query or "to cart" in query or "buy" in query or "purchase" in query):
        return "add_to_cart"
    
    # Check other types of intents
    elif "stock" in query or "availability" in query:
        return "stock"
    elif "description" in query or "details" in query or "info" in query:
        return "description"
    elif "image" in query or "picture" in query or "photo" in query:
        return "image"
    else:
        return "general"


def correct_image_url(response_text):
    """Corrects incorrect base domains and image size in Gemini-generated URLs."""
    
    # Replace incorrect domains with the correct one
    response_text = re.sub(r"https://(www\.)?crustaging\.com", "https://uk.crustaging.com", response_text)
    
    # Replace the incorrect image size if needed (e.g., 50x to 750x)
    response_text = re.sub(r"/image/50x/", "/image/750x/", response_text)

    # Replace any cache key change, optionally standardize to '1'
    response_text = re.sub(r"/cache/\d+/", "/cache/1/", response_text)

    return response_text

def generate_gemini_response_from_wine_data(query, wine_data_formatted):
    """ Generate a Gemini response based on user's wine query and wine data using chain-of-thought prompting. """
    intent = classify_user_intent(query)

    prompt = ""

    if intent == "stock":
        prompt = (
            f"User asked: '{query}'\n\n"
            f"Step 1: Analyze the query to identify if the user is asking about wine stock or availability.\n"
            f"Step 2: Check the product data for stock-related fields such as quantity, availability status, or ETA.\n"
            f"Step 3: Based on this data, explain whether the wine is in stock and when it will be available.\n\n"
            f"🍷 Wine Product Data:\n{wine_data_formatted}"
        )
    elif intent == "description":
        prompt = (
            f"User asked: '{query}'\n\n"
            f"Step 1: Identify that the user is looking for details about the wine.\n"
            f"Step 2: Extract the wine's description, tasting notes, or product details from the data.\n"
            f"Step 3: Summarize this information in a clear and friendly way.\n\n"
            f"🍷 Wine Product Data:\n{wine_data_formatted}"
        )
    elif intent == "image":
        prompt = (
            f"User asked: '{query}'\n\n"
            f"Step 1: Understand that the user wants to see the wine image.\n"
            f"Step 2: Locate the image URL in the wine data.\n"
            f"Step 3: Ensure the image URL contains the correct base domain 'uk.crustaging.com'.\n"
            f"Step 4: Return the complete image URL with a short description if available.\n\n"
            f"🍷 Wine Product Data:\n{wine_data_formatted}"
        )
    elif intent == "add_to_cart":
        prompt = (
            f"User asked: '{query}'\n\n"
            f"Step 1: Recognize that the user wants to add a wine to their cart.\n"
            f"Step 2: Look for the wine's product name, ID, and essential add-to-cart attributes.\n"
            f"Step 3: Present this data in a structured way so the system can easily process the cart addition.\n\n"
            f"🛒 Add to Cart Data:\n{wine_data_formatted}"
        )
    else:
        prompt = (
            f"User asked: '{query}'\n\n"
            f"Step 1: Interpret the user's intent from the question.\n"
            f"Step 2: Summarize all relevant information from the wine data.\n"
            f"Step 3: Compose a complete and helpful reply, including product name, description, image URL, product URL, stock location, and ETA.\n\n"
            f"🍷 Wine Product Data:\n{wine_data_formatted}"
        )

    try:
        response = model.generate_content(prompt)
        corrected_response = correct_image_url(response.text.strip())
        return corrected_response
    except Exception as e:
        return f" Gemini generation error: {e}"


def interactive_query():
    while True:
        user_query = input("\n Please enter a query (or type 'exit' to quit): ")
        if user_query.lower() == 'exit':
            print("👋 Exiting...")
            break

        # Classify intent
        is_wine_intent = classify_user_intent(user_query)  # Use your combined function

        if is_wine_intent in ["stock", "description", "image", "add_to_cart", "general"]:
            print(" Gemini detected wine-related intent. Fetching wine details...")

            wine_data = get_wine_details_tool(user_query)
            if not wine_data or (isinstance(wine_data, list) and not wine_data[0].strip()):
                print("Failed to get wine data or it was empty.")
                continue


            wine_data_formatted = wine_data[0].strip()
            gemini_output = generate_gemini_response_from_wine_data(user_query, wine_data_formatted)
            print("\n Gemini Final Response:\n", gemini_output)
        else:
            print("🌐 No wine-related intent. Fetching from Brave and Gemini...")
            search_and_generate_response(user_query)

#  Start the script
if __name__ == "__main__":
    interactive_query()

