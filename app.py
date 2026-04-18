import sys
import os

# 현재 파일이 있는 디렉토리를 경로 맨 앞에 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()