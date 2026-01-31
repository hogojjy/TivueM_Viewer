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

# --- [설정] 페이지 설정 및 모바일 전체화면 테마 ---
st.set_page_config(
    page_title="TivueM Viewer", 
    page_icon="🔒", 
    layout="wide",  # 전체 화면을 위해 wide 모드 사용
    initial_sidebar_state="collapsed"
)

# --- [스타일] 모바일 최적화 및 전체 화면 UI ---
st.markdown("""
    <style>
    /* 1. 상단 메뉴 및 여백 제거 (전체 화면 느낌) */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
    }
    
    /* 2. 이미지 보안 및 풀스크린 설정 */
    img {
        width: 100% !important;
        height: auto !important;
        pointer-events: none; /* 꾹 눌러서 저장 방지 */
        -webkit-touch-callout: none;
    }

    /* 3. 모바일 핀치 줌 허용을 위한 설정 */
    [data-testid="stAppViewContainer"] {
        overflow: auto;
    }
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
    # 파일 업로드 전에는 안내 문구 표시
    if 'file_loaded' not in st.session_state:
        st.markdown("<h3 style='text-align: center; padding-top: 20px;'>🔒 TivueM Secure Viewer</h3>", unsafe_allow_html=True)

    # 1. 파일 업로더 최적화 (type 미지정으로 모든 파일 앱 유도)
    uploaded_file = st.file_uploader(
        "보안 문서(.bin) 선택", 
        type=None, 
        label_visibility="collapsed" # 디자인을 위해 숨김
    )

    if uploaded_file is None:
        st.info("💡 **[Browse files]** 클릭 후 **[파일]** 또는 **[내 파일]**을 선택하세요.")
    else:
        st.session_state['file_loaded'] = True
        try:
            # 복호화 및 검증
            encrypted_data = uploaded_file.read()
            decrypted_data = xor_cipher(encrypted_data, SECRET_KEY)
            
            expiry_str = decrypted_data[-10:].decode()
            pdf_bytes = decrypted_data[:-10]
            
            today = get_server_date()
            if today:
                expiry_date = datetime.datetime.strptime(expiry_str, '%Y-%m-%d').date()
                if today > expiry_date:
                    st.error(f"⛔ 만료된 문서입니다. ({expiry_str})")
                    return

            # 워터마크 로드
            try:
                watermark_source = Image.open("watermark.png").convert("RGBA")
            except:
                watermark_source = None

            # 3. 확대/축소 컨트롤 (상단 고정)
            zoom_val = st.select_slider("🔍 화면 확대 비율", options=[50, 75, 100, 125, 150, 200], value=100)
            zoom = zoom_val / 100

            # PDF 렌더링
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # 컨테이너를 사용하여 좌우 여백 없이 출력
            for i, page in enumerate(doc):
                # 해상도를 높여서 확대 시에도 글자가 깨지지 않게 함
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom * 2, zoom * 2))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                if watermark_source:
                    img = apply_watermark(img, watermark_source)
                
                # use_container_width=True로 전체 화면 대응
                st.image(img, use_container_width=True)
            
            doc.close()

        except Exception:
            st.error("❌ 파일을 열 수 없습니다. 암호화 키를 확인하세요.")

if __name__ == "__main__":
    main()