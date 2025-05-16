from server import mcp
import requests
import constants
# @mcp.tool('ListProducts')
# def ListProducts():
#     response =  requests.get("https://micro-scale.software/api/products")
#     return response.json()

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
        'frontend': 'mgmc90d0b0io1vbceg0sh8nbl9',
        'frontend_cid': 'SK9WNt8zBeqmbFIZ',
        'session_hash': '29983',
        'CACHED_FRONT_FORM_KEY': 'RZWBEWMAUGMO5qqo'
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


