from flask import Flask
import yfinance as yf
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "웹앱이 정상적으로 작동 중입니다!"

# 여기에 기존에 작성하셨던 yfinance나 requests 관련 로직을 
# 아래에 추가하시면 됩니다.

if __name__ == "__main__":
    app.run()