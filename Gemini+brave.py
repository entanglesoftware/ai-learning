import requests
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re
import unicodedata
from urllib.parse import urlparse
import json
import sys
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

        print("\n🌐 Brave Search Top Result:")
        print(f"🔹 Title: {title}")
        print(f"🔗 URL: {url}")
        print(f"📝 Snippet: {description}")

        gemini_prompt = (
            f"Based on this web search result:\nTitle: {title}\nURL: {url}\n"
            f"Snippet: {description}\n\n"
            f"Give a useful and updated answer to this query: '{query}'"
        )
        gemini_response = query_gemini(gemini_prompt)

        if gemini_response:
            print("\n🧠 Gemini Response (Generated using Brave result):\n", gemini_response)
        else:
            print("❌ No response from Gemini.")
    else:
        print("❌ No search results from Brave Search.")


def extract_wine_info(query):
    # Try to extract number of cases and bottles per case from the format like "2 cases ... (6x75cl)"
    case_match = re.search(r'(\d+)\s+cases?.*?\((\d+)x75cl\)', query, re.IGNORECASE)
    if case_match:
        num_cases = int(case_match.group(1))
        bottles_per_case = int(case_match.group(2))
        total_bottles = num_cases * bottles_per_case
    else:
        # Fallback: assume 1 bottle if nothing is mentioned
        total_bottles = 1

    # Try to remove "Add ... to my cart" and clean up the wine name
    wine_name_match = re.search(r'(?:add\s*\d+\s*cases?\s*of\s+)?(.+?)(?:\s*\(\d+x75cl\))?(?:\s*to\s+my\s+cart)?$', query, re.IGNORECASE)
    if wine_name_match:
        wine_name_cleaned = wine_name_match.group(1).strip()
    else:
        wine_name_cleaned = query.strip()  # fallback to full query

    print("User query:", query)
    print("Wine name:", wine_name_cleaned, "| Total bottles:", total_bottles)
    final_prompt = f"Extract the wine name from query and respond only the name and nothing else : '{query}'."
    response = model.generate_content(final_prompt)
    wine_name_cleaned = response.text.strip()
    return {
        "name": wine_name_cleaned,
        "total_bottles": total_bottles
    }    
    return None, None


# Main function to get wine details and attempt add-to-cart
def get_wine_details_tool(query, intent, intent_list):
    print("Getting wine details from user query:")
    wine_info = extract_wine_info(query)
    wine_name = wine_info["name"]
    quantity = wine_info["total_bottles"]

    print("Wine name:", wine_name, "| Quantity:", quantity)

    try:
        url = 'https://uk.crustaging.com/live-markets/api_buyBid/autosuggestionsearch'
        params = {
            'q': wine_name,
            'exactStockAvailable': 'undefined',
            'limit': 10,
            'searchProducers': 'true',
            'platform': 'web'
        }

        headers = {'User-Agent': 'cru-script'}
        cookies = {
            'frontend': 'mgmc90d0b0io1vbceg0sh8nbl9',
            'frontend_cid': 'SK9WNt8zBeqmbFIZ',
            'session_hash': '29983',
            'CACHED_FRONT_FORM_KEY': 'RZWBEWMAUGMO5qqo'
        }

        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        print("Search Status Code:", response.status_code)

        if response.status_code != 200:
            return f"❌ API returned error code {response.status_code}", None

        products = response.json()
        print("RAW API Response:", products)
        print("Search API Response: ", products.get('found'))

        output = []
        if products.get('found'):
            print("Found products in API response:")
            found_wine = None
            for item in products.get('data', []):
                item_type = item.get('type')
                entries = item.get('data', [])

                if item_type == 'product':
                    for product in entries:
                        product_name = product.get('name', '').lower()
                        print(f"Product name: {product_name}")
                        if wine_name.lower() in product_name:  # Check if the extracted wine_name matches product name
                            found_wine = product
                            print(f"Found wine: {found_wine}")
                            break

                if found_wine:
                    print(f"Found wine: {found_wine}")
                    product_url = found_wine.get('url', '')
                    lwin = found_wine.get('lwin', '')
                    if lwin and product_url:
                        req_path = product_url.split('/')[3] if '/' in product_url else ''
                        (
                            product_detail,
                            product_id,
                            qty_available,
                            wine_name,
                            wine_description,
                            wine_image,
                            stock_location,
                            stock_location_eta
                        ) = get_product_details_by_req_path(req_path, lwin)
                        print("stock, description or image : ", (intent == intent_list[0]) or (intent == intent_list[1]) or (intent == intent_list[2]))

                        if intent == intent_list[3] and product_id:
                            # 🔽 Replace the original add_to_cart() call with this:
                            if qty_available >= quantity:
                                cart_response, current_cart = add_to_cart(
                                                        product_id,
                                                        quantity
                                                    )
                                return f"{cart_response}\n\n🛒 Current Cart:\n" + json.dumps(current_cart, indent=2)
                            # 🔽 Return both the response and the current cart details
                            else:
                                return "❌ Product is not available in the desired quantity."
                        elif (intent == intent_list[0]) or (intent == intent_list[1]) or (intent == intent_list[2]):  # stock, description or image
                            print("stock, description or image")
                            return {
                                "product_detail": product_detail,
                                "product_id": product_id,
                                "qty_available": qty_available,
                                "wine_name": wine_name,
                                "wine_description": wine_description,
                                "wine_image": wine_image,
                                "stock_location": stock_location,
                                "stock_location_eta": stock_location_eta
                            }
                    else:
                        output.append(f"❌ No LWIN or URL for product: {found_wine.get('name')}")
                    break

            if not found_wine:
                return f"❌ No wine found matching '{wine_name}'.", None

            return "\n".join(output)
        else:
            return f"❌ No wine found matching '{wine_name}'.", None
    except Exception as e:
        return f"❌ Error fetching wine details: {e}", None



# Function to get product details from PDP API and attempt add-to-cart
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

        # Extract main product details
        if 'main_details' in product_detail and product_detail['main_details']:
            main_details = product_detail['main_details']
            wine_name = main_details.get('short_name', 'No short name')
            wine_description = main_details.get('description', 'No description available')
            wine_image = main_details.get('image_url', 'No image available')
            stock_location = main_details.get('stock_location', 'No stock location')
            stock_location_eta = main_details.get('stock_location_eta', 'No ETA available')

            print("Wine Name:", wine_name)
            print("Description:", wine_description)
            print("Image URL:", wine_image)
            print("Stock Location:", stock_location)
            print("Stock Location ETA:", stock_location_eta)

        buy_details = product_detail.get('buy_details', [])
        product_found = False

        for item in buy_details:
            product_id = item.get('product_id')
            unit_qty_info = item.get('unit_qty_info', {})
            qty_available_raw = unit_qty_info.get('qty_available')

            try:
                qty_available = int(qty_available_raw)
            except (ValueError, TypeError):
                qty_available = 0

            print("  DEBUG:", {
                "product_id": product_id,
                "qty_available": qty_available
            })

            if product_id and qty_available and qty_available > 0:
                print("Product available to add to cart:")
                print(f"PRODUCT ID: {product_id}")
                print(f"Qty Available: {qty_available}")
                product_found = True
                # return product_detail, product_id

        return (
            product_detail,
            product_id,
            qty_available,
            wine_name,
            wine_description,
            wine_image,
            stock_location,
            stock_location_eta
        )


    except Exception as e:
        print(f" Error fetching product details: {e}")
        return {}

# function for add-to-cart
cart = []

def add_to_cart(product_id, quantity):
    print("Adding to cart...")
    add_to_cart_url = "https://uk.crustaging.com/live-markets/api_cart/addToCart"
    
    payload = {
        "availability": "available",  
        "condition_status": "verified",
        "escape": True,  
        "platform": "web",  
        "product": product_id, 
        "qty": quantity,  
        "skip_mini_cart": 1,  
        "uenc": "",  
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "cru-script"
    }

    try:
        response = requests.post(add_to_cart_url, headers=headers, json=payload)
        print("Add to Cart Status:", response.status_code)

        if response.status_code == 200:
            try:
                response_data = response.json()
                print("🧾 Add-to-Cart API Response:", response_data)

                if response_data.get("status") == 1:
                    cart_item = response_data.get("cart_items", [])[0]
                    cart_item_data = {
                        "item_id": cart_item.get("item_id"),
                        "product_id": cart_item.get("product_id"),
                        "product_name": cart_item.get("name"),
                        "location": cart_item.get("eta", {}).get("stock_location"),
                        "condition_status": cart_item.get("condition_status"),
                        "image_url": cart_item.get("image_url"),
                        "eta": cart_item.get("eta", {}).get("eta_val"),
                        "price": cart_item.get("price"),
                        "vintage": cart_item.get("vintage"),
                        "warehouse": cart_item.get("warehouse", {}).get("name"),
                        "format": cart_item.get("format"),
                        "quantity": quantity
                    }
                    cart.append(cart_item_data)

                    print("\n🛒 Current Cart Items:")
                    for item in cart:
                        print(item)

                    return f"✅ Successfully added {quantity}x {cart_item_data['product_name']} to cart.", cart
                else:
                    return f"❌ API responded but did not confirm success: {response_data}", None
            except ValueError:
                return "❌ Response is not valid JSON.", None
        else:
            return f"❌ Failed to add product to cart. Status: {response.status_code}, Response: {response.text}", None

    except Exception as e:
        return f"❌ Exception occurred: {e}", None

def show_cart_handler():
    return cart

# For getting the intent
def classify_user_intent(query, intent_list):
    query = query.lower()
    # if re.search(r"(add|buy|purchase)\s+\d+\s+(bottles?|cases?)\s+.*(to\s+my\s+cart|add\s+to\s+cart)", query):
    #     return "add_to_cart"
    # elif "stock" in query or "availability" in query:
    #     return "stock"
    # elif "description" in query or "details" in query or "info" in query:
    #     return "description"
    # elif "image" in query or "picture" in query or "photo" in query:
    #     return "image"
    # elif "show cart" in query or "my cart" in query or "view cart" in query:
    #     return "show_cart"
    #
    # else:
    #     return "general"
    system_prompt = f"Give a strictly one word answer and classify the user's intent out of the following options : {intent_list}."
    final_prompt = system_prompt+f"\nUser query : {query}"
    print(f'Final Prompt {final_prompt}')
    response = model.generate_content(final_prompt).text
    # print(response, len(response), response.lower().strip(), len(response.lower().strip()))
    return response.lower().strip()



def generate_gemini_response_from_wine_data(query, wine_data_formatted, intent, intent_list):
    # intent = classify_user_intent(query)
    prompt = ""
    # intent_list = ["stock", "description", "image", "add_to_cart","show_cart", "general"]

    if intent == intent_list[0]:    # stock
        prompt = (
            f"User asked: '{query}'\n\n"
            f"🍷 Wine Product Data from API:\n{wine_data_formatted}\n\n"
            f"Please provide stock availability information for the wine in question."
        )
    elif intent == intent_list[1]:  # description
        prompt = (
            f"User asked: '{query}'\n\n"
            f"🍷 Wine Product Data from API:\n{wine_data_formatted}\n\n"
            f"Please provide the detailed description of the wine."
        )
    elif intent == intent_list[2]:  #image
        prompt = (
            f"User asked: '{query}'\n\n"
            f"🍷 Wine Product Data from API:\n{wine_data_formatted}\n\n"
            f"Please provide the image URL of the wine (make sure to keep the correct base URL, 'uk.crustaging.com')."
        )
    elif intent == intent_list[3]:  #add_to_cart
        prompt = (
            f"User asked: '{query}'\n\n"
            f"🍷 Wine Product Data from API:\n{wine_data_formatted}\n\n"
            f"Please call the search API, then PDP API, and then add the product to the cart."
        )
    elif intent == intent_list[4]:  # show_cart
        # if not cart:
        #     return "🛒 Your cart is empty."
        # response = "🛒 **Your Cart:**\n"
        # for item in cart:
        #     response += f"- {item['quantity']}x {item['name'].title()}\n"
        # return response
        prompt = (
            f"User asked: '{query}'\n\n"
            f"here's the cart : {wine_data_formatted}\n\n"
            f"Please provide the cart items, price and their quantities. If cart is empty, say 'Your cart is empty.'"
        )
    else:
        prompt = (
            f"User asked: '{query}'\n\n"
            f"🍷 Wine Product Data from API:\n{wine_data_formatted}\n\n"
            f"Now write a helpful, friendly response to the user, combining both the web and wine product data."
        )

    try:
        response = model.generate_content(prompt)
        return (response.text.strip())
    except Exception as e:
        return f"❌ Gemini generation error: {e}"
    
# For user interaction
def interactive_query():
    intent_list = ["stock", "description", "image", "add_to_cart","show_cart", "general"]
    while True:
        user_query = input("\n🔍 Please enter a query (or type 'exit' to quit): ")
        
        if user_query.lower() == 'exit':
            print("👋 Exiting...")
            break
        intent = classify_user_intent(user_query, intent_list)
        print(f"Intent detected: {intent}, {intent in intent_list}")
        if intent in intent_list:
            print(f"🍷 Gemini detected '{intent}' intent. Processing...")
            wine_data = None
            if intent == intent_list[4]:
                wine_data = show_cart_handler()
            else:
                wine_data = get_wine_details_tool(user_query, intent, intent_list)
                if not wine_data or (isinstance(wine_data, list) and not wine_data[0].strip()):
                    print("❌ Failed to get wine data or it was empty.")
                    continue

                if intent == intent_list[3] and isinstance(wine_data, str): # add to cart
                    print(f"\n✅ Gemini Raw Add-to-Cart Result:\n{wine_data}")
                    # wine_data_formatted = wine_data
                # else:
                #     wine_data_formatted = wine_data[0].strip()

            # gemini_output = generate_gemini_response_from_wine_data(user_query, wine_data_formatted, intent, intent_list)
            gemini_output = generate_gemini_response_from_wine_data(user_query, wine_data, intent, intent_list)

            print("\n🧠 Gemini Final Response:\n", gemini_output)

        else:
            print("🌐 No wine-related intent. Handling with general Gemini + Brave logic...")
            search_and_generate_response(user_query)

# # 🔥 Start the script
if __name__ == "__main__":
    interactive_query()