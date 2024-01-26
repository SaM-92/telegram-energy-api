import requests

url = "https://api-access.electricitymaps.com/free-tier/home-assistant"
headers = {"auth-token": "8YB3GhYHdn6DGVoKEIV7rCxBvdEW5FNF"}

response = requests.get(url, headers=headers)

print(response.text)
