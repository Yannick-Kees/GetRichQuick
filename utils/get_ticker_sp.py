import pandas as pd
import requests

url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'

# Wir definieren einen User-Agent Header
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Erst die Seite mit requests laden
response = requests.get(url, headers=headers)

# Dann den HTML-Inhalt an pandas übergeben
pd.read_html(response.text)[0].to_csv('sp500.csv', index=False)