import os

import openai
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

st.set_page_config(page_title="다국어 번역기", page_icon="🌐", layout="centered")

# 버튼 라벨 -> (언어 코드, 프롬프트용 언어명)
# 국기 이모지는 Windows에서 "US"처럼 글자로 보여서 언어 코드를 사용한다.
LANGUAGES = {
    "영어": ("EN", "English"),
    "일본어": ("JA", "Japanese"),
    "프랑스어": ("FR", "French"),
}
DEFAULT_MODEL = "gpt-6-astra"
MAX_CHARS = 5000
REQUEST_TIMEOUT = 30  # 초
SYSTEM_PROMPT = (
    "You are a professional translator. Translate the user's text into "
    "{target_language}. Output only the translated text without explanations."
)

# 색상은 테마 기본값을 따르고 여백·모양만 조정 (라이트/다크 모두 대응)
st.markdown(
    """
    <style>
    .block-container { padding-top: 2.5rem; max-width: 760px; }
    .stButton > button { border-radius: 10px; font-size: 1.05rem; padding: 0.6rem 0; }
    .subtitle { opacity: 0.75; margin-top: -0.6rem; margin-bottom: 1.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_client(api_key: str) -> OpenAI:
    """API 키로 OpenAI 클라이언트를 만든다 (재실행 간 재사용)."""
    # 연결은 5초, 응답은 REQUEST_TIMEOUT초까지 기다리고 실패 시 1번만 재시도
    timeout = openai.Timeout(REQUEST_TIMEOUT, connect=5.0)
    return OpenAI(api_key=api_key, timeout=timeout, max_retries=1)


def translate(client: OpenAI, model: str, text: str, target_language: str) -> str:
    """입력 텍스트를 target_language로 번역해 번역문만 반환한다."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(target_language=target_language)},
            {"role": "user", "content": text},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def error_message(exc: Exception, model: str) -> str:
    """OpenAI 예외를 사용자용 한국어 메시지로 바꾼다."""
    if isinstance(exc, openai.AuthenticationError):
        return "API 키가 올바르지 않습니다. .env의 OPENAI_API_KEY를 확인하세요."
    if isinstance(exc, openai.NotFoundError):
        return f"모델 '{model}'을(를) 찾을 수 없습니다. .env의 OPENAI_MODEL을 확인하세요."
    if isinstance(exc, openai.RateLimitError):
        return "요청 한도를 초과했거나 크레딧이 부족합니다. 잠시 후 다시 시도하세요."
    if isinstance(exc, openai.APITimeoutError):
        return "OpenAI 서버 응답 시간이 초과되었습니다. 네트워크 상태를 확인하고 잠시 후 다시 시도하세요."
    if isinstance(exc, openai.APIConnectionError):
        return "OpenAI 서버에 연결할 수 없습니다. 네트워크 상태를 확인하세요."
    if isinstance(exc, openai.APIStatusError):
        return f"OpenAI API 오류가 발생했습니다 (HTTP {exc.status_code})."
    return f"번역 중 알 수 없는 오류가 발생했습니다: {exc}"


def clear_result() -> None:
    """이전 번역 결과를 지운다."""
    for key in ("result", "result_label", "result_source"):
        st.session_state.pop(key, None)


api_key = os.getenv("OPENAI_API_KEY", "").strip()
model = os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_MODEL

with st.sidebar:
    st.header("사용 방법")
    st.markdown(
        "1. 번역할 텍스트를 입력합니다.\n"
        "2. 영어 / 일본어 / 프랑스어 버튼 중 하나를 누릅니다.\n"
        "3. 아래에 번역 결과가 표시됩니다. 결과에 마우스를 올리면 나오는 복사 아이콘으로 복사할 수 있습니다."
    )
    st.divider()
    st.caption("사용 모델")
    st.code(model, language=None)

st.title("🌐 다국어 번역기")
st.markdown('<p class="subtitle">텍스트를 입력하고 번역할 언어를 선택하세요.</p>', unsafe_allow_html=True)

if not api_key:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일에 API 키를 추가한 뒤 앱을 다시 실행하세요.")
    st.stop()

client = get_client(api_key)

# max_chars를 지정하면 입력하는 동안 실시간으로 글자 수가 표시된다.
text = st.text_area(
    "번역할 텍스트",
    height=200,
    max_chars=MAX_CHARS,
    placeholder=f"여기에 번역할 글을 입력하세요... (최대 {MAX_CHARS:,}자)",
    help=f"최대 {MAX_CHARS:,}자까지 입력할 수 있습니다. 이보다 긴 글을 붙여넣으면 입력되지 않으니 나눠서 번역하세요.",
)

cols = st.columns(len(LANGUAGES))
for col, (label, (code, lang)) in zip(cols, LANGUAGES.items()):
    if col.button(f"{label} ({code})", use_container_width=True):
        st.session_state.pop("error", None)
        if not text.strip():
            clear_result()
            st.warning("번역할 텍스트를 입력하세요.")
        else:
            with st.spinner("번역 중..."):
                try:
                    st.session_state["result"] = translate(client, model, text, lang)
                    st.session_state["result_label"] = label
                    st.session_state["result_source"] = text
                except Exception as exc:
                    clear_result()
                    st.session_state["error"] = error_message(exc, model)

if "error" in st.session_state:
    st.error(st.session_state["error"])

with st.container(border=True):
    if "result" in st.session_state:
        st.markdown(f"**번역 결과** · {st.session_state['result_label']}")
        if st.session_state["result_source"] != text:
            st.caption("⚠️ 입력이 바뀌었습니다. 아래는 이전 입력의 번역입니다. 다시 번역하려면 버튼을 누르세요.")
        st.code(st.session_state["result"], language=None, wrap_lines=True)
    else:
        st.caption("번역 결과가 여기에 표시됩니다.")
