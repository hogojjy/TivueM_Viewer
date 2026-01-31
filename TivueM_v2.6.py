import streamlit as st
import pymupdf as fitz
import datetime
import requests
from itertools import cycle
from PIL import Image
import io

# --- [보안] 암호화 키 (데스크탑 v2.6 생성기와 반드시 동일해야 함) ---
SECRET_KEY = "Tivue_Secure_System_Key_2026"

# --- [보안] XOR 복호화 함수 ---
def xor_cipher(data, key):
    key_bytes = key.encode()
    return bytes(a ^ b for a, b in zip(data, cycle(key_bytes)))

# --- [보안] 서버 시간 체크 ---
def get_server_date():
    try:
        # 구글 서버 시간을 가져와 로컬 조작 방지
        res = requests.get('https://www.google.com', timeout=2)
        date_str = res.headers['Date']
        curr = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        return curr.date()
    except:
        return None

# --- [설정] 페이지 설정 ---
st.set_page_config(
    page_title="TivueM_v2.6", 
    page_icon="🔒", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- [스타일] 보안 강화 및 모바일 최적화 CSS ---
st.markdown("""
    <style>
    /* 이미지 꾹 누르기/드래그 및 저장 방지 */
    img {
        pointer-events: none;
        -webkit-user-select: none;
        user-select: none;
        -webkit-touch-callout: none;
    }
    /* 상단 헤더, 푸터 숨김으로 깔끔한 뷰어 구성 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    /* 모바일 가독성 향상 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [기능] 워터마크 합성 (v2.6 규칙: 크기 40%, 투명도 10%) ---
def apply_watermark(base_image, watermark_img):
    base_image = base_image.convert("RGBA")
    
    # 1. 크기 조절 (배경 가로폭의 40%)
    target_width = int(base_image.width * 0.4)
    w_percent = (target_width / float(watermark_img.size[0]))
    h_size = int((float(watermark_img.size[1]) * float(w_percent)))
    watermark_resized = watermark_img.resize((target_width, h_size), Image.Resampling.LANCZOS)
    
    # 2. 투명도 조절 (10%)
    r, g, b, a = watermark_resized.split()
    a = a.point(lambda p: p * 0.1)
    watermark_resized.putalpha(a)
    
    # 3. 중앙 위치 계산 및 합성
    bg_w, bg_h = base_image.size
    wm_w, wm_h = watermark_resized.size
    offset = ((bg_w - wm_w) // 2, (bg_h - wm_h) // 2)
    
    transparent_layer = Image.new('RGBA', base_image.size, (0,0,0,0))
    transparent_layer.paste(watermark_resized, offset)
    
    return Image.alpha_composite(base_image, transparent_layer)

# --- 메인 실행 함수 ---
def main():
    st.title("🔒 TivueM v2.6 Viewer")
    
    # 워터마크 이미지 로드 체크
    try:
        watermark_source = Image.open("watermark.png").convert("RGBA")
    except FileNotFoundError:
        st.caption("⚠️ 워터마크 없이 열람 모드로 진입합니다.")
        watermark_source = None

    # [중요] 모바일 환경 파일 선택기 최적화
    # type=None으로 설정하여 시스템 파일 탐색기(내 파일) 진입을 유도합니다.
    uploaded_file = st.file_uploader(
        "보안 문서(.bin)를 선택하세요", 
        type=None, 
        accept_multiple_files=False
    )

    # 모바일 사용자를 위한 안내 가이드
    if not uploaded_file:
        with st.expander("📱 모바일에서 파일이 안 보이시나요?", expanded=True):
            st.info("""
            **1. 파일 선택창이 뜨면:** 하단 메뉴에서 카메라가 아닌 **[파일]** 또는 **[내 파일]** 아이콘을 클릭하세요.
            **2. 경로 찾기:** 왼쪽 메뉴(≡)에서 **[내장 메모리]** 또는 **[다운로드]** 폴더로 이동하세요.
            **3. 최후의 수단:** 파일 이름 끝을 `.bin`에서 `.jpg`로 바꾼 뒤 '갤러리'에서 선택해도 정상 작동합니다.
            """)

    if uploaded_file is not None:
        try:
            # 1. 데이터 읽기 & 복호화
            encrypted_data = uploaded_file.read()
            decrypted_data = xor_cipher(encrypted_data, SECRET_KEY)
            
            # 2. 데이터 파싱 (끝 10바이트는 만료일)
            expiry_str = decrypted_data[-10:].decode()
            pdf_bytes = decrypted_data[:-10]
            
            # 3. 날짜 검증
            today = get_server_date()
            if today:
                expiry_date = datetime.datetime.strptime(expiry_str, '%Y-%m-%d').date()
                if today > expiry_date:
                    st.error(f"⛔ 열람 기한이 만료되었습니다. (만료일: {expiry_str})")
                    return
                else:
                    st.success(f"✅ 인증 성공 (만료일: {expiry_str})")
            else:
                st.warning("⚠️ 서버 시간 동기화 실패. 인터넷 연결을 확인하세요.")

            # 4. 화면 컨트롤 (슬라이더)
            zoom = st.slider("🔍 화면 확대/축소", 50, 200, 100, 10) / 100
            
            # 5. PDF 렌더링
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for i, page in enumerate(doc):
                # 모바일 해상도를 고려한 Matrix 설정
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom * 2, zoom * 2))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                # 워터마크 적용
                if watermark_source:
                    img = apply_watermark(img, watermark_source)
                
                # 화면 출력 (열 너비에 맞춤)
                st.image(img, caption=f"Page {i+1}", use_container_width=True)
            
            doc.close() # 메모리 해제

        except Exception as e:
            st.error("❌ 파일을 처리할 수 없습니다. 암호화 키가 다르거나 파일이 손상되었을 수 있습니다.")
            # 상세 에러 확인용 (개발 시에만 사용)
            # st.write(e)

if __name__ == "__main__":
    main()