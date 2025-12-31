# PDF 번역기 (English → 한국어)

DeepL API를 사용하여 PDF 파일을 번역하는 Python 스크립트입니다.

## 기능

- ✅ PDF 레이아웃 유지하며 번역
- ✅ 폴더 내 여러 PDF 일괄 처리
- ✅ 배치 번역으로 API 호출 최소화
- ✅ 자동 한글 폰트 감지

## 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/your-username/pdf-translator.git
cd pdf-translator
```

2. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
`.env.example`을 복사하여 `.env` 파일 생성:
```bash
cp .env.example .env
```

`.env` 파일을 열어 DeepL API 키 입력:
```env
DEEPL_API_KEY=your_actual_api_key_here
```

DeepL API 키는 [DeepL Pro API](https://www.deepl.com/pro-api)에서 발급받을 수 있습니다 (무료 플랜: 월 50만 자).

## 사용 방법

1. `pdfs/` 폴더에 번역할 PDF 파일 넣기

2. 스크립트 실행
```bash
python pdf_translator.py
```

3. `translated_pdfs/` 폴더에서 번역된 PDF 확인

## 번역 모드

### Layout 모드 (기본)
원본 레이아웃을 최대한 유지하며 번역
```python
translate_folder('./pdfs', './translated_pdfs', mode="layout")
```

### Simple 모드
빠른 처리, 단순한 레이아웃
```python
translate_folder('./pdfs', './translated_pdfs', mode="simple")
```

## 폴더 구조
```
pdf-translator/
├── pdf_translator.py
├── .env (API 키 - Git에 올라가지 않음)
├── .env.example (예시 파일)
├── requirements.txt
├── pdfs/ (원본 PDF)
└── translated_pdfs/ (번역된 PDF)
```

## 주의사항

- `.env` 파일은 절대 GitHub에 올리지 마세요
- API 키가 노출되지 않도록 주의하세요
- DeepL 무료 플랜은 월 50만 자 제한이 있습니다

## 라이선스

MIT License
```

---

## 전체 폴더 구조
```
pdf-translator/
├── pdf_translator.py          # 메인 스크립트 (위에서 수정한 코드)
├── .env                        # API 키 (Git 제외)
├── .env.example                # API 키 예시
├── .gitignore                  # Git 제외 파일 목록
├── requirements.txt            # 필요한 패키지 목록
├── README.md                   # 사용 설명서
├── pdfs/                       # 원본 PDF (Git 제외)
└── translated_pdfs/            # 번역본 (Git 제외)