from server import mcp
import requests
import constants
import os
from dotenv import load_dotenv
load_dotenv()

@mcp.tool('SearchWines')
def SearchWines(SearchQuery :str):
    print("Searching for Wine...")
    url = constants.SEARCH_URL
    params = {
        'q': SearchQuery,
        'exactStockAvailable': 'undefined',
        'limit': 10,
        'searchProducers': 'true',
        'platform': 'web'
    }
    headers = {'User-Agent': 'cru-script'}
    cookies = {
        'frontend': os.getenv('FRONTEND_COOKIE'),
        'frontend_cid': os.getenv('FRONTEND_CID'),
        'session_hash': os.getenv('SESSION_HASH'),
        'CACHED_FRONT_FORM_KEY': os.getenv('CACHED_FRONT_FORM_KEY')
    }
    response = requests.get(url, headers=headers, cookies=cookies, params=params)
    print("Search Status Code:", response.status_code)

    if response.status_code != 200:
        return f"API returned error code {response.status_code}"

    products = response.json()
    print("Data : ",products['data'])
    if products['found'] == False:
        return "No Such Product Found"
    return products['data']

@mcp.tool('WineDetails')
def WineDetails(ProductUrl :str, LwinID :str):
    try:
        RequestPath = ProductUrl.split('/')[3] if '/' in ProductUrl else ''

        if not RequestPath or not LwinID:
            return "❌ req_path or lwin is missing."
        RequestPath = RequestPath.lstrip('/')
        SearchUrl = f"https://uk.crustaging.com/live-markets/api_pdp/get?req_path={RequestPath}&lwin={LwinID}&offer_type=cru&selected_transfer_type=storage&platform=web"
        headers = {
            'User-Agent': 'cru-script'
        }
        response = requests.get(SearchUrl, headers=headers)
        if response.status_code != 200:
            print(f"Error Details: {response.text}")
            return f"Product detail API returned error {response.status_code}"
        ProductDetail = response.json()
        return ProductDetail
    except Exception as e:
        return e

@mcp.tool('AddToCart')
def AddToCart(ProductId :str, Quantity :int):
    print("Adding to cart...")
    Url = constants.ADD_TO_CART_URL

    payload = {
        "availability": "available",
        "condition_status": "verified",
        "escape": True,
        "platform": "web",
        "product": ProductId,
        "qty": Quantity,
        "skip_mini_cart": 1,
        "uenc": "",
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "cru-script"
    }

    try:
        response = requests.post(Url, headers=headers, json=payload)
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
                        "quantity": Quantity
                    }
                    return f"✅ Successfully added {Quantity}x {cart_item_data['product_name']} to cart."
                else:
                    return f"❌ API responded but did not confirm success: {response_data}", None
            except ValueError:
                return "❌ Response is not valid JSON.", None
        else:
            return f"❌ Failed to add product to cart. Status: {response.status_code}, Response: {response.text}", None

    except Exception as e:
        return f"❌ Exception occurred: {e}", None

