import requests
import json

url = 'http://127.0.0.1:5000/ocr'
files = {'file': open('./imgs/20240914144515.jpg', 'rb')}

r = requests.post(url, files=files)
print(r.text)
