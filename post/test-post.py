import requests
import json
import base64

url = 'http://172.25.77.112:8866/predict/ocr_system'
img = open(r'./3.jpg', 'rb').read()

data = {'images': [base64.b64encode(img).decode('utf8')]}

headers = {
    "Content-Type": "application/json"
}

r = requests.post(url, headers=headers, data=json.dumps(data))
img_result = r.json()["results"]
results = []
for i in range(len(img_result)):
    for j in range(len(img_result[i])):
        results.append(img_result[i][j])

print(({
    '服务状态': 'success',
    '识别结果': results
}))