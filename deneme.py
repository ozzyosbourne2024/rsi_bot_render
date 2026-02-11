import requests

TOKEN = "8541248285:AAFBU1zNp7wtdrM5tfUh1gsu8or4HiQ1NJc "
CHAT_ID = "1863652639"
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
data = {"chat_id": CHAT_ID, "text": "Test mesajı"}
res = requests.post(url, data=data)
print(res.json())

