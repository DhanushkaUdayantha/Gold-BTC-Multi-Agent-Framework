import requests

url = "https://api.goldprice.dev/v1/prices"

params = {
    "symbol": "XAU-USD-SPOT"
}

response = requests.get(url, params=params)

print(response.status_code)
print(response.text)