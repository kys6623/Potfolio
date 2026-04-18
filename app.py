from flask import Flask
import yfinance as yf

app = Flask(__name__)

@app.route('/')
def home():
    # 애플(AAPL) 주가 정보를 가져오는 예시
    ticker = yf.Ticker("AAPL")
    price = ticker.history(period="1d")['Close'].iloc[-1]
    return f"현재 애플 주가: {price:.2f} 달러"

if __name__ == "__main__":
    app.run()