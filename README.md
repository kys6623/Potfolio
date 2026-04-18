# Asset Portfolio Dashboard (Flask + SQLite)

개인 자산(주식/금/현금/달러/부동산)을 저장하고 실시간 시세 기반으로 평가금액과 비중을 보여주는 모바일 친화형 대시보드 웹앱입니다.

## 1) 프로젝트 구조

```text
AIPORTFOLIO/
├─ app/
│  ├─ __init__.py          # Flask 앱 팩토리, 설정
│  ├─ db.py                # SQLite 연결/스키마/CRUD
│  ├─ market_data.py       # yfinance 시세 조회 유틸
│  ├─ real_estate_data.py  # 국토부 실거래가 조회 유틸
│  ├─ services.py          # 입력 검증 + 평가/비중 계산 로직
│  ├─ routes.py            # 라우트(대시보드, 추가, 삭제)
│  ├─ templates/
│  │  ├─ base.html         # 공통 레이아웃
│  │  └─ dashboard.html    # 메인 대시보드 화면
│  └─ static/
│     └─ style.css         # UI 보조 스타일
├─ run.py                  # 실행 엔트리
├─ requirements.txt
└─ README.md
```

## 2) 실행 방법

### Windows PowerShell

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

실행 후 브라우저에서 `http://127.0.0.1:5000` 접속

## 3) 구현된 핵심 기능

- **자산 입력**
  - 주식: 티커 + 수량 입력 시 yfinance로 자산명 자동 조회 후 저장
  - 금: 중량(g) 입력 저장
  - 현금(KRW), 달러(USD): 각각 별도 입력/저장
  - 부동산(아파트): 아파트명 + 면적(m2) + 지역코드 입력 후 실거래가 기반 저장 (자동조회 실패 시 수동가 입력 가능)
- **실시간 평가**
  - 주식: 티커 실시간 가격 조회 (통화가 USD면 KRW 환산)
  - 금: `GC=F` 선물가(USD/oz) -> g당 KRW로 변환
  - 달러: `KRW=X` 환율로 KRW 환산
- **대시보드 계산**
  - 총 자산(원화 기준)
  - 위험자산(주식), 안전자산(금), 현금성(현금+달러), 부동산 비중(%)
- **모바일 UI**
  - Tailwind 기반 카드형 레이아웃
  - iPhone 웹앱 용도로 보기 쉬운 단일 컬럼 구성
  - 비중 원형(도넛) 차트

## 4) 주의 사항

- yfinance 데이터는 시장 상황/API 응답 상태에 따라 일시적으로 지연/누락될 수 있습니다.
- 부동산 실거래가 자동조회는 `MOLIT_API_KEY` 환경변수가 있어야 동작합니다.
- 자동조회가 실패하면 폼의 `수동 실거래가(원)` 값으로 저장할 수 있습니다.
- 현재 버전은 단일 사용자 로컬 저장(SQLite) 기준입니다.
