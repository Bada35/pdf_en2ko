import os
import requests
import fitz  # PyMuPDF
from pathlib import Path

# DeepL API 설정
DEEPL_API_KEY = '02ad6235-f0ce-4a15-8ff3-f03225553dc9:fx'
DEEPL_API_URL = 'https://api-free.deepl.com/v2/translate'

def translate_text(text, source_lang='EN', target_lang='KO'):
    """DeepL API로 텍스트 번역"""
    if not text.strip():
        return text
    
    payload = {
        'auth_key': DEEPL_API_KEY,
        'text': text,
        'source_lang': source_lang,
        'target_lang': target_lang
    }
    
    try:
        response = requests.post(DEEPL_API_URL, data=payload)
        if response.status_code == 200:
            result = response.json()
            return result['translations'][0]['text']
        else:
            print(f"⚠️ 번역 오류 {response.status_code}: {response.text}")
            return text
    except Exception as e:
        print(f"❌ 번역 실패: {e}")
        return text

def get_font_for_korean():
    """한글 폰트 찾기"""
    # 시스템에서 사용 가능한 한글 폰트 경로
    font_paths = [
        # Windows
        "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕
        "C:/Windows/Fonts/NanumGothic.ttf",
        # Mac
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        # Linux
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        # 현재 디렉토리
        "./NotoSansKR-Regular.ttf",
        "./fonts/NotoSansKR-Regular.ttf"
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            return font_path
    
    print("⚠️ 한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다 (한글이 깨질 수 있음)")
    return None

def extract_text_blocks(page):
    """페이지에서 텍스트 블록 추출 (위치 정보 포함)"""
    blocks = page.get_text("dict")["blocks"]
    text_blocks = []
    
    for block in blocks:
        if block["type"] == 0:  # 텍스트 블록
            for line in block["lines"]:
                for span in line["spans"]:
                    text_blocks.append({
                        "text": span["text"],
                        "bbox": span["bbox"],  # (x0, y0, x1, y1)
                        "size": span["size"],
                        "font": span["font"],
                        "color": span["color"]
                    })
    
    return text_blocks

def translate_pdf_with_layout(input_pdf, output_pdf, batch_size=10):
    """레이아웃을 유지하면서 PDF 번역"""
    print(f"📄 PDF 번역 시작: {input_pdf}")
    
    # PDF 열기
    doc = fitz.open(input_pdf)
    
    # 한글 폰트 찾기
    korean_font_path = get_font_for_korean()
    
    total_pages = len(doc)
    print(f"📖 총 {total_pages}페이지\n")
    
    # 각 페이지 처리
    for page_num in range(total_pages):
        page = doc[page_num]
        print(f"[{page_num + 1}/{total_pages}] 페이지 처리 중...")
        
        # 1. 텍스트 블록 추출
        text_blocks = extract_text_blocks(page)
        
        if not text_blocks:
            print(f"  ℹ️ 텍스트 없음, 건너뜀")
            continue
        
        # 2. 텍스트 배치 번역 (API 호출 최소화)
        texts_to_translate = [block["text"] for block in text_blocks]
        
        # 배치 처리
        translated_texts = []
        for i in range(0, len(texts_to_translate), batch_size):
            batch = texts_to_translate[i:i+batch_size]
            combined_text = "\n###SPLIT###\n".join(batch)
            
            translated_combined = translate_text(combined_text)
            translated_batch = translated_combined.split("\n###SPLIT###\n")
            
            # 분할 개수가 안 맞으면 개별 번역
            if len(translated_batch) != len(batch):
                translated_batch = [translate_text(t) for t in batch]
            
            translated_texts.extend(translated_batch)
            print(f"  🔄 {min(i+batch_size, len(texts_to_translate))}/{len(texts_to_translate)} 블록 번역 완료")
        
        # 3. 원본 텍스트 제거
        page.clean_contents()  # 페이지 정리
        
        # 4. 번역된 텍스트를 같은 위치에 삽입
        for block, translated_text in zip(text_blocks, translated_texts):
            bbox = block["bbox"]
            font_size = block["size"]
            
            # 텍스트 삽입
            try:
                # 한글 폰트 사용
                if korean_font_path:
                    page.insert_textbox(
                        bbox,
                        translated_text,
                        fontsize=font_size * 0.9,  # 한글은 약간 작게
                        fontname="noto",
                        fontfile=korean_font_path,
                        color=(0, 0, 0),
                        align=0  # 좌측 정렬
                    )
                else:
                    # 폰트 없으면 기본 폰트
                    page.insert_textbox(
                        bbox,
                        translated_text,
                        fontsize=font_size * 0.9,
                        color=(0, 0, 0),
                        align=0
                    )
            except Exception as e:
                print(f"  ⚠️ 텍스트 삽입 실패: {e}")
        
        print(f"  ✅ 페이지 {page_num + 1} 완료\n")
    
    # 저장
    doc.save(output_pdf)
    doc.close()
    
    print(f"🎉 번역 완료! 저장 위치: {output_pdf}\n")

def translate_pdf_simple(input_pdf, output_pdf):
    """간단 버전: 원본 제거하고 번역본만 생성"""
    print(f"📄 PDF 번역 시작 (간단 모드): {input_pdf}")
    
    doc = fitz.open(input_pdf)
    output_doc = fitz.open()  # 새 PDF
    
    korean_font_path = get_font_for_korean()
    total_pages = len(doc)
    
    for page_num in range(total_pages):
        page = doc[page_num]
        print(f"[{page_num + 1}/{total_pages}] 페이지 처리 중...")
        
        # 새 페이지 생성 (같은 크기)
        new_page = output_doc.new_page(
            width=page.rect.width,
            height=page.rect.height
        )
        
        # 텍스트 추출 및 번역
        text = page.get_text()
        
        if text.strip():
            translated_text = translate_text(text)
            
            # 번역된 텍스트 삽입
            rect = page.rect
            margin = 50
            text_rect = fitz.Rect(
                margin, 
                margin, 
                rect.width - margin, 
                rect.height - margin
            )
            
            try:
                if korean_font_path:
                    new_page.insert_textbox(
                        text_rect,
                        translated_text,
                        fontsize=11,
                        fontname="noto",
                        fontfile=korean_font_path,
                        color=(0, 0, 0),
                        align=0
                    )
                else:
                    new_page.insert_textbox(
                        text_rect,
                        translated_text,
                        fontsize=11,
                        color=(0, 0, 0),
                        align=0
                    )
            except Exception as e:
                print(f"  ⚠️ 오류: {e}")
        
        print(f"  ✅ 페이지 {page_num + 1} 완료")
    
    output_doc.save(output_pdf)
    output_doc.close()
    doc.close()
    
    print(f"🎉 번역 완료! 저장 위치: {output_pdf}\n")

def translate_folder(folder_path, output_folder, mode="layout"):
    """폴더 내 모든 PDF 번역
    
    Args:
        folder_path: 원본 PDF 폴더
        output_folder: 번역본 저장 폴더
        mode: "layout" (레이아웃 유지) 또는 "simple" (간단)
    """
    folder = Path(folder_path)
    output = Path(output_folder)
    
    if not folder.exists():
        print(f"❌ 폴더를 찾을 수 없습니다: {folder_path}")
        return
    
    output.mkdir(exist_ok=True)
    
    pdf_files = list(folder.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ PDF 파일이 없습니다: {folder_path}")
        return
    
    print(f"📁 폴더 내 PDF 파일 {len(pdf_files)}개 발견\n")
    print("=" * 60)
    
    for i, pdf_file in enumerate(pdf_files, 1):
        input_path = str(pdf_file)
        output_filename = f"번역_{pdf_file.name}"
        output_path = str(output / output_filename)
        
        print(f"\n📌 [{i}/{len(pdf_files)}] {pdf_file.name}")
        print("-" * 60)
        
        try:
            if mode == "layout":
                translate_pdf_with_layout(input_path, output_path)
            else:
                translate_pdf_simple(input_path, output_path)
        except Exception as e:
            print(f"❌ 오류 발생: {e}\n")
            continue
        
        print("=" * 60)
    
    print(f"\n🎊 모든 번역 완료! 저장 위치: {output_folder}")

# 사용 예시
if __name__ == "__main__":
    # 방법 1: 단일 파일 번역 (레이아웃 유지)
    # translate_pdf_with_layout('input.pdf', 'output_translated.pdf')
    
    # 방법 2: 단일 파일 번역 (간단)
    # translate_pdf_simple('input.pdf', 'output_simple.pdf')
    
    # 방법 3: 폴더 전체 번역
    input_folder = './pdfs'  # PDF가 있는 폴더
    output_folder = './translated_pdfs'  # 번역본 저장 폴더
    
    # mode="layout" : 레이아웃 유지 (복잡, 느림, 정교함)
    # mode="simple" : 단순 번역 (빠름, 레이아웃 단순화)
    translate_folder(input_folder, output_folder, mode="layout")