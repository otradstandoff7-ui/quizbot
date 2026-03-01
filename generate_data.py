import requests
import json

url = "https://restcountries.com/v3.1/all?fields=name,capital,flags"
data = requests.get(url).json()

countries = []

for c in data:
    if "capital" in c and c["capital"]:
        countries.append({
            "name": c["name"]["common"],
            "capital": c["capital"][0],
            "flag": c["flags"]["png"]
        })

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(countries, f, ensure_ascii=False, indent=2)

print("Стран загружено:", len(countries))