import random
import time
import re
import base64
import streamlit as st
from collections import defaultdict

# ────────────────────────────────────────────────
# 1. 데이터 로드 (words.js 우선)
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_word_data():
    try:
        with open("words.js", "r", encoding="utf-8") as f:
            content = f.read()
        extracted = re.findall(r'["\']([가-힣]{2,4})["\']', content)
        if extracted:
            return frozenset(extracted), "words.js"
    except FileNotFoundError:
        pass
    return frozenset(["가구", "가방", "가수", "기차", "나비", "나무"]), "기본 샘플"

# ────────────────────────────────────────────────
# 2. 로직 및 두음법칙
# ────────────────────────────────────────────────
DUEUM = {
    '녀': '여', '뇨': '요', '뉴': '유', '니': '이', '랴': '야', '려': '여', '례': '예', '료': '요',
    '류': '유', '리': '이', '락': '낙', '래': '내', '랭': '냉', '략': '약', '량': '양', '령': '영',
    '로': '노', '뢰': '뇌', '룡': '용', '루': '누', '륙': '육', '륜': '윤', '률': '율', '릉': '능',
    '린': '인', '림': '임', '립': '입', '라': '나', '랄': '날', '람': '남', '랍': '납',
}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM: chars.add(DUEUM[last_char])
    for k, v in DUEUM.items():
        if v == last_char: chars.add(k)
    return list(chars)

# ────────────────────────────────────────────────
# 3. 커스텀 CSS (그라데이션 제목 & 버튼 호버)
# ────────────────────────────────────────────────
st.set_page_config(page_title="끝말잇기", layout="centered")

st.markdown("""
<style>
    /* 그라데이션 제목 */
    .grad-title {
        background: linear-gradient(90deg, #FF0000, #8A2BE2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 10px;
    }
    
    /* 채팅창 스타일 */
    .chat-wrap { background: #f8f9fa; border-radius: 15px; padding: 20px; height: 380px; overflow-y: auto; border: 1px solid #e9ecef; margin-bottom: 15px; }
    .msg-row-ai { display:flex; justify-content:flex-start; margin-bottom:12px; }
    .msg-row-user { display:flex; justify-content:flex-end; margin-bottom:12px; }
    
    /* 봇 말풍선 (텍스트 검정 고정) */
    .bubble-ai { background: #ffffff; color: #000000 !important; border: 1px solid #dee2e6; border-radius: 15px 15px 15px 2px; padding: 10px 15px; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .bubble-user { background: linear-gradient(135deg, #FF0055, #7000FF); color: white; border-radius: 15px 15px 2px 15px; padding: 10px 15px; font-weight: 500; }
    
    /* 타이머 바 */
    .timer-container { width: 100%; background-color: #eee; border-radius: 10px; margin: 10px 0; height: 14px; }
    .timer-bar { height: 100%; border-radius: 10px; transition: width 0.3s ease, background-color 0.3s ease; }

    /* 버튼 그라데이션 및 호버 효과 */
    div.stButton > button {
        background: linear-gradient(135deg, #FF0000, #8A2BE2) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
    }
    div.stButton > button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 6px 20px rgba(255, 0, 0, 0.3) !important;
        filter: brightness(1.2);
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 4. 세션 초기화
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    words, source = load_word_data()
    index = defaultdict(list)
    for w in words: index[w[0]].append(w)
    
    first = random.choice(list(words))
    st.session_state.update({
        "words": words, "index": dict(index), "used": {first},
        "last_word": first, "history": [("AI", first)],
        "chain": 1, "turn_start": time.time(), "input_key": 0,
        "game_over": False, "initialized": True
    })

def get_max_time(chain):
    if chain < 10: return 15
    elif chain < 20: return 10
    elif chain < 30: return 7
    return 5

max_time = get_max_time(st.session_state.chain)

# ────────────────────────────────────────────────
# 5. 메인 UI 출력
# ────────────────────────────────────────────────
st.markdown('<div class="grad-title">QUANTUM WORD BATTLE</div>', unsafe_allow_html=True)

# 타이머 로직 (시간에 따른 4단계 색상 변화)
if not st.session_state.game_over:
    elapsed = time.time() - st.session_state.turn_start
    remaining = max(0.0, max_time - elapsed)
    ratio = remaining / max_time

    # 시간 비율에 따른 색상 정의 (초록 -> 노랑 -> 주황 -> 빨강)
    if ratio > 0.75: t_color = "#28a745"   # 초록
    elif ratio > 0.5: t_color = "#ffc107"  # 노랑
    elif ratio > 0.25: t_color = "#fd7e14" # 주황
    else: t_color = "#dc3545"              # 빨강

    st.markdown(f"⏱ **남은 시간: {remaining:.1f}초**")
    st.markdown(f"""
        <div class="timer-container">
            <div class="timer-bar" style="width: {ratio*100}%; background-color: {t_color};"></div>
        </div>
    """, unsafe_allow_html=True)

    if remaining <= 0:
        st.session_state.game_over = True
        st.rerun()

# 채팅창
chat_html = '<div class="chat-wrap">'
for speaker, text in st.session_state.history:
    if speaker == "AI":
        chat_html += f'<div class="msg-row-ai"><div class="bubble-ai">🤖 {text}</div></div>'
    else:
        chat_html += f'<div class="msg-row-user"><div class="bubble-user">{text} 👤</div></div>'
chat_html += '</div>'
st.markdown(chat_html, unsafe_allow_html=True)

# 입력 폼 및 자동 포커스
if not st.session_state.game_over:
    with st.form(key=f"frm_{st.session_state.input_key}", clear_on_submit=True):
        cols = st.columns([4, 1])
        user_input = cols[0].text_input("단어 입력", placeholder="단어를 입력하세요", label_visibility="collapsed")
        submit = cols[1].form_submit_button("전송")

    # 자동 포커스 JS
    st.components.v1.html("""
        <script>
        var input = window.parent.document.querySelector('input[data-testid="stTextInput"]');
        if (input) { input.focus(); }
        </script>
        """, height=0)

    if submit and user_input:
        word = user_input.strip()
        starts = get_start_chars(st.session_state.last_word[-1])
        
        if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
            st.session_state.used.add(word)
            st.session_state.history.append(("User", word))
            st.session_state.chain += 1
            
            # AI 대응
            possible = []
            for ch in get_start_chars(word[-1]):
                possible.extend([w for w in st.session_state.index.get(ch, []) if w not in st.session_state.used])
            
            if not possible:
                st.session_state.game_over = True
                st.balloons()
            else:
                ai_word = random.choice(possible)
                st.session_state.used.add(ai_word)
                st.session_state.history.append(("AI", ai_word))
                st.session_state.last_word = ai_word
                st.session_state.chain += 1
                st.session_state.turn_start = time.time()
                st.session_state.input_key += 1
            st.rerun()

else:
    st.error("GAME OVER")
    if st.button("다시 시작", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# 타이머 갱신을 위한 루프
if not st.session_state.game_over:
    time.sleep(0.1)
    st.rerun()
