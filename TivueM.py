import streamlit as st
import pymupdf as fitz
import datetime
import requests
from itertools import cycle
from PIL import Image
import io

# --- [보안] 암호화 키 ---
SECRET_KEY = "Tivue_Secure_System_Key_2026"

def xor_cipher(data, key):
    key_bytes = key.encode()
    return bytes(a ^ b for a, b in zip(data, cycle(key_bytes)))

def get_server_date():
    try:
        res = requests.get('https://www.google.com', timeout=2)
        date_str = res.headers['Date']
        curr = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        return curr.date()
    except:
        return None

# --- [설정] 전체 화면 및 핀치 줌 허용 설정 ---
st.set_page_config(
    page_title="TivueM Viewer", 
    page_icon="🔒", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- [스타일] 주소창 숨김 유도 및 여백 제로 CSS ---
st.markdown("""
    <style>
    /* 1. 모든 여백 제거 및 배경색 통일 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .block-container {
        padding: 0rem !important;
        margin: 0rem !important;
    }
    
    /* 2. 브라우저 주소창 자동 숨김 유도를 위한 최소 높이 설정 */
    [data-testid="stAppViewContainer"] {
        background-color: #1a1a1a;
        overflow-x: hidden;
    }

    /* 3. 이미지 보안 및 꽉 찬 화면 */
    img {
        width: 100% !important;
        height: auto !important;
        display: block;
        pointer-events: none;
        -webkit-touch-callout: none;
        margin-bottom: 2px; /* 페이지 간 미세한 구분 */
    }

    /* 4. 슬라이더 등 불필요한 위젯 숨김 (파일 업로드 후에만 적용) */
    .stSelectSlider { display: none; }
    </style>
    """, unsafe_allow_html=True)

def apply_watermark(base_image, watermark_img):
    base_image = base_image.convert("RGBA")
    target_width = int(base_image.width * 0.4)
    w_percent = (target_width / float(watermark_img.size[0]))
    h_size = int((float(watermark_img.size[1]) * float(w_percent)))
    watermark_resized = watermark_img.resize((target_width, h_size), Image.Resampling.LANCZOS)
    r, g, b, a = watermark_resized.split()
    a = a.point(lambda p: p * 0.1)
    watermark_resized.putalpha(a)
    bg_w, bg_h = base_image.size
    wm_w, wm_h = watermark_resized.size
    offset = ((bg_w - wm_w) // 2, (bg_h - wm_h) // 2)
    transparent_layer = Image.new('RGBA', base_image.size, (0,0,0,0))
    transparent_layer.paste(watermark_resized, offset)
    return Image.alpha_composite(base_image, transparent_layer)

def main():
    # 1. 파일 업로더 (최대한 깔끔하게 표시)
    uploaded_file = st.file_uploader(
        "보안 문서 선택", 
        type=None, 
        label_visibility="collapsed"
    )

    if uploaded_file is None:
        st.markdown("<div style='text-align: center; color: white; padding: 50px;'>🔒 TivueM Secure Viewer<br><small>Browse files를 눌러 [파일] 앱을 선택하세요</small></div>", unsafe_allow_html=True)
    else:
        try:
            # 복호화 및 데이터 로드
            encrypted_data = uploaded_file.read()
            decrypted_data = xor_cipher(encrypted_data, SECRET_KEY)
            expiry_str = decrypted_data[-10:].decode()
            pdf_bytes = decrypted_data[:-10]
            
            # 날짜 검증
            today = get_server_date()
            if today:
                expiry_date = datetime.datetime.strptime(expiry_str, '%Y-%m-%d').date()
                if today > expiry_date:
                    st.error("⛔ 만료된 문서입니다.")
                    return

            # 고정 고해상도 렌더링 (핀치 줌 대비)
            # 사용자가 손가락으로 확대해도 깨지지 않도록 기본 해상도를 2.5배로 높여 렌더링합니다.
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            try:
                watermark_source = Image.open("watermark.png").convert("RGBA")
            except:
                watermark_source = None

            # 문서 출력
            for i, page in enumerate(doc):
                # 기본 해상도를 높여서 핀치 줌 시 선명도 유지
                pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                if watermark_source:
                    img = apply_watermark(img, watermark_source)
                
                st.image(img, use_container_width=True)
            
            doc.close()

        except Exception:
            st.error("❌ 복호화 실패. 올바른 보안 문서가 아닙니다.")

if __name__ == "__main__":
    main()