import sys
import os

# 현재 폴더를 경로에 추가하여 'app' 폴더를 모듈로 인식하게 함
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()