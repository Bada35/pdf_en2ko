import os
import requests
import fitz  # PyMuPDF
from pathlib import Path

# DeepL API 설정
DEEPL_API_KEY = '02ad6235-f0ce-4a15-8ff3-f03225553dc9:fx'
DEEPL_API_URL = 'https://api-free.deepl.com/v2/translate'

def translate_text(text, source_lang='EN', target_lang='KO'):
    """DeepL API로 텍스트 번역"""
    text_clean = text.strip()
    if not text_clean:
        return text
    
    # 특수 문자만 있는 경우 (점선 등) 번역하지 않음
    if text_clean.replace('.', '').replace('-', '').replace('_', '').replace(' ', '').strip() == '':
        return text
    
    payload = {
        'auth_key': DEEPL_API_KEY,
        'text': text_clean,
        'source_lang': source_lang,
        'target_lang': target_lang
    }
    
    try:
        response = requests.post(DEEPL_API_URL, data=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'translations' in result and len(result['translations']) > 0:
                translated = result['translations'][0]['text']
                # 번역 결과가 원본과 다른지 확인
                if translated.strip() == text_clean:
                    # 원본과 동일하면 다시 시도 (API가 번역을 건너뛴 경우)
                    return text
                return translated
            else:
                return text
        else:
            error_msg = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
            if response.status_code != 429:  # Rate limit이 아니면만 출력
                print(f"⚠️ 번역 오류 {response.status_code}: {error_msg}")
            return text
    except requests.exceptions.Timeout:
        print(f"⚠️ 번역 타임아웃")
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
                    text = span["text"].strip()
                    # 빈 텍스트나 공백만 있는 경우 제외
                    if text and len(text) > 0:
                        text_blocks.append({
                            "text": span["text"],  # 원본 텍스트 (공백 포함)
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
        texts_to_translate = [block["text"].strip() for block in text_blocks]
        
        # 배치 처리
        translated_texts = []
        for i in range(0, len(texts_to_translate), batch_size):
            batch = texts_to_translate[i:i+batch_size]
            # 빈 텍스트 필터링
            valid_batch = [(idx, t) for idx, t in enumerate(batch) if t and t.strip()]
            
            if not valid_batch:
                # 모두 빈 텍스트면 원본 그대로
                translated_texts.extend(batch)
                continue
            
            # 유효한 텍스트만 번역
            valid_texts = [t for _, t in valid_batch]
            combined_text = "\n###SPLIT###\n".join(valid_texts)
            
            translated_combined = translate_text(combined_text)
            
            # 번역이 실제로 되었는지 확인
            if translated_combined == combined_text or not translated_combined.strip():
                print(f"  ⚠️ 배치 {i//batch_size + 1}: 번역 실패, 개별 재시도")
                # 개별 번역으로 재시도 (최대 2회)
                translated_batch = []
                for orig_text in batch:
                    if not orig_text or not orig_text.strip():
                        translated_batch.append(orig_text)
                        continue
                    translated = translate_text(orig_text)
                    # 재시도 후에도 동일하면 한 번 더 시도
                    if translated == orig_text:
                        translated = translate_text(orig_text)
                    translated_batch.append(translated)
            else:
                translated_batch_split = translated_combined.split("\n###SPLIT###\n")
                
                # 분할 개수가 안 맞으면 개별 번역
                if len(translated_batch_split) != len(valid_texts):
                    print(f"  ⚠️ 배치 분할 불일치 ({len(translated_batch_split)}/{len(valid_texts)}), 개별 번역")
                    translated_batch = []
                    for orig_text in batch:
                        if not orig_text or not orig_text.strip():
                            translated_batch.append(orig_text)
                        else:
                            translated_batch.append(translate_text(orig_text))
                else:
                    # 번역 결과를 원래 순서대로 배치
                    translated_batch = []
                    valid_idx = 0
                    for orig_text in batch:
                        if not orig_text or not orig_text.strip():
                            translated_batch.append(orig_text)
                        else:
                            translated_batch.append(translated_batch_split[valid_idx])
                            valid_idx += 1
            
            translated_texts.extend(translated_batch)
            print(f"  🔄 {min(i+batch_size, len(texts_to_translate))}/{len(texts_to_translate)} 블록 번역 완료")
        
        # 3. 원본 텍스트를 흰색으로 덮기 (이미지 등은 보존)
        for block in text_blocks:
            bbox = block["bbox"]
            text_rect = fitz.Rect(bbox)
            # 텍스트 영역을 흰색으로 덮기 (약간 여유 공간 추가)
            page.draw_rect(text_rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
        
        # 4. 번역된 텍스트를 같은 위치에 삽입
        inserted_count = 0
        skipped_count = 0
        
        for idx, (block, translated_text) in enumerate(zip(text_blocks, translated_texts)):
            bbox = block["bbox"]
            font_size = block["size"]
            original_text = block["text"].strip()
            translated_text_clean = translated_text.strip() if translated_text else ""
            
            # 빈 텍스트는 건너뛰기
            if not translated_text_clean:
                skipped_count += 1
                continue
            
            # 번역이 실제로 되었는지 확인
            if translated_text_clean == original_text:
                # 번역이 안 된 경우, 원본 텍스트를 그대로 사용하지 않고 다시 번역 시도
                retry_translated = translate_text(original_text)
                if retry_translated != original_text and retry_translated.strip():
                    translated_text_clean = retry_translated.strip()
                else:
                    # 번역 실패해도 원본 텍스트는 삽입
                    translated_text_clean = original_text
            
            # bbox를 Rect 객체로 변환
            text_rect = fitz.Rect(bbox)
            
            # 텍스트 삽입 시도
            success = False
            font_sizes_to_try = [
                font_size * 0.9,  # 기본 크기
                font_size * 0.8,  # 조금 작게
                font_size * 0.7,  # 더 작게
                max(font_size * 0.6, 6)  # 최소 크기
            ]
            
            for try_font_size in font_sizes_to_try:
                try:
                    if korean_font_path:
                        result = page.insert_textbox(
                            text_rect,
                            translated_text_clean,
                            fontsize=try_font_size,
                            fontname="noto",
                            fontfile=korean_font_path,
                            color=(0, 0, 0),
                            align=0
                        )
                    else:
                        result = page.insert_textbox(
                            text_rect,
                            translated_text_clean,
                            fontsize=try_font_size,
                            color=(0, 0, 0),
                            align=0
                        )
                    
                    # 성공 (남은 공간이 0 이상)
                    if result >= 0:
                        inserted_count += 1
                        success = True
                        break
                    # 실패했지만 약간만 넘친 경우 (-10 이하) - 텍스트를 약간 자르기
                    elif result > -10:
                        # 텍스트를 약간 줄여서 재시도
                        words = translated_text_clean.split()
                        if len(words) > 1:
                            # 마지막 단어 제거하고 재시도
                            shortened = " ".join(words[:-1])
                            if korean_font_path:
                                result2 = page.insert_textbox(
                                    text_rect,
                                    shortened,
                                    fontsize=try_font_size,
                                    fontname="noto",
                                    fontfile=korean_font_path,
                                    color=(0, 0, 0),
                                    align=0
                                )
                            else:
                                result2 = page.insert_textbox(
                                    text_rect,
                                    shortened,
                                    fontsize=try_font_size,
                                    color=(0, 0, 0),
                                    align=0
                                )
                            if result2 >= 0:
                                inserted_count += 1
                                success = True
                                break
                except Exception as e:
                    continue
            
            # 모든 시도 실패 시 insert_text로 단일 라인 삽입
            if not success:
                try:
                    # 텍스트가 너무 길면 자르기
                    display_text = translated_text_clean
                    if len(display_text) > 100:
                        display_text = display_text[:97] + "..."
                    
                    if korean_font_path:
                        page.insert_text(
                            (text_rect.x0, text_rect.y0 + font_size * 0.9),
                            display_text,
                            fontsize=font_size * 0.9,
                            fontfile=korean_font_path,
                            color=(0, 0, 0)
                        )
                    else:
                        page.insert_text(
                            (text_rect.x0, text_rect.y0 + font_size * 0.9),
                            display_text,
                            fontsize=font_size * 0.9,
                            color=(0, 0, 0)
                        )
                    inserted_count += 1
                except Exception as e:
                    skipped_count += 1
        
        print(f"  📝 {inserted_count}/{len(text_blocks)} 블록 삽입 성공, {skipped_count}개 건너뜀")
        
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