import streamlit as st
import pymupdf as fitz
import datetime
import requests
from itertools import cycle
from PIL import Image, ImageDraw
import io

# --- [보안] 암호화 키 (데스크탑 v2.6과 반드시 동일해야 함) ---
SECRET_KEY = "Tivue_Secure_System_Key_2026"

# --- [보안] XOR 복호화 함수 ---
def xor_cipher(data, key):
    key_bytes = key.encode()
    return bytes(a ^ b for a, b in zip(data, cycle(key_bytes)))

# --- [보안] 서버 시간 체크 ---
def get_server_date():
    try:
        res = requests.get('https://www.google.com', timeout=2)
        date_str = res.headers['Date']
        curr = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        return curr.date()
    except:
        return None

# --- [설정] 페이지 설정 ---
st.set_page_config(
    page_title="Tivue M v2.6", 
    page_icon="🔒", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- [스타일] 이미지 저장 방지 및 모바일 최적화 CSS ---
st.markdown("""
    <style>
    /* 이미지 꾹 누르기/드래그 방지 */
    img {
        pointer-events: none;
        -webkit-user-select: none;
        -khtml-user-select: none;
        -moz-user-select: none;
        -o-user-select: none;
        user-select: none;
        -webkit-touch-callout: none; /* iOS 길게 누르기 메뉴 차단 */
    }
    /* 상단 헤더, 푸터 숨김 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    /* 모바일에서 여백 최소화 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [기능] 워터마크 합성 (v2.6 규칙: 크기 40%, 투명도 10%) ---
def apply_watermark(base_image, watermark_img):
    base_image = base_image.convert("RGBA")
    
    # 1. 크기 조절 (가로폭의 40%)
    target_width = int(base_image.width * 0.4)
    w_percent = (target_width / float(watermark_img.size[0]))
    h_size = int((float(watermark_img.size[1]) * float(w_percent)))
    
    # 리사이징 (품질 유지)
    watermark_resized = watermark_img.resize((target_width, h_size), Image.Resampling.LANCZOS)
    
    # 2. 투명도 조절 (10%)
    r, g, b, a = watermark_resized.split()
    # 알파 채널에 0.1을 곱해 아주 흐리게 만듦
    a = a.point(lambda p: p * 0.1)
    watermark_resized.putalpha(a)
    
    # 3. 중앙 위치 계산
    bg_w, bg_h = base_image.size
    wm_w, wm_h = watermark_resized.size
    offset = ((bg_w - wm_w) // 2, (bg_h - wm_h) // 2)
    
    # 4. 합성
    transparent_layer = Image.new('RGBA', base_image.size, (0,0,0,0))
    transparent_layer.paste(watermark_resized, offset)
    
    return Image.alpha_composite(base_image, transparent_layer)

# --- 메인 실행 ---
def main():
    st.title("🔒 Tivue M v2.6")
    
    # 워터마크 이미지 로드
    try:
        watermark_source = Image.open("watermark.png").convert("RGBA")
    except FileNotFoundError:
        st.warning("⚠️ 서버에 'watermark.png' 파일이 없습니다.")
        watermark_source = None

    uploaded_file = st.file_uploader("보안 문서(.bin)를 선택하세요", type="bin")

    if uploaded_file is not None:
        try:
            # 1. 데이터 읽기 & 복호화
            encrypted_data = uploaded_file.read()
            decrypted_data = xor_cipher(encrypted_data, SECRET_KEY)
            
            # 2. 데이터 파싱
            expiry_str = decrypted_data[-10:].decode()
            pdf_bytes = decrypted_data[:-10]
            
            # 3. 날짜 검증
            today = get_server_date()
            if today:
                expiry_date = datetime.datetime.strptime(expiry_str, '%Y-%m-%d').date()
                if today > expiry_date:
                    st.error(f"⛔ 열람 기한이 만료되었습니다.\n(만료일: {expiry_str})")
                    return
                else:
                    st.success(f"✅ 인증 완료 (만료일: {expiry_str})")
            else:
                st.warning("⚠️ 인터넷 연결을 확인하세요 (시간 동기화 실패)")

            # 4. 뷰어 컨트롤
            zoom = st.slider("🔍 화면 배율", 50, 200, 100, 10, help="이미지 해상도를 조절합니다.") / 100
            
            # 5. PDF 렌더링
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for i, page in enumerate(doc):
                # 줌 배율에 맞춰 고해상도 렌더링
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom * 1.5, zoom * 1.5))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                # 워터마크 적용
                if watermark_source:
                    img = apply_watermark(img, watermark_source)
                
                # 화면 표시 (모바일 너비에 자동 맞춤)
                st.image(img, caption=f"- {i+1} -", use_column_width=True)

        except Exception:
            st.error("❌ 파일을 열 수 없습니다. (암호화 키 불일치 또는 손상된 파일)")

if __name__ == "__main__":
    main()