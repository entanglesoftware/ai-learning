from server import mcp
import requests

@mcp.tool('ListProducts')
def ListProducts():
    response =  requests.get("https://micro-scale.software/api/products")
    return response.json()