import random
import time
import re
import streamlit as st
from collections import defaultdict

# ────────────────────────────────────────────────
# 1. 데이터 로드
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
    return frozenset(["가구","가방","가수","기차","나비","나무"]), "기본"

# ────────────────────────────────────────────────
# 2. 두음법칙
# ────────────────────────────────────────────────
DUEUM = {
    '녀':'여','뇨':'요','뉴':'유','니':'이','랴':'야','려':'여','례':'예','료':'요',
    '류':'유','리':'이','락':'낙','래':'내','랭':'냉','략':'약','량':'양','령':'영',
    '로':'노','뢰':'뇌','룡':'용','루':'누','륙':'육','륜':'윤','률':'율','릉':'능',
    '린':'인','림':'임','립':'입','라':'나','람':'남','랑':'낭','르':'느'
}

def get_start_chars(last):
    chars = {last}
    if last in DUEUM:
        chars.add(DUEUM[last])
    return list(chars)

# ────────────────────────────────────────────────
# 3. UI 스타일 (🔥 복구 완료)
# ────────────────────────────────────────────────
st.set_page_config(page_title="끝말잇기", layout="centered")

st.markdown("""
<style>
.grad-title {
    background: linear-gradient(90deg, #FF0000, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 3rem; font-weight: 800; text-align: center;
}

.chain-display {
    text-align: center; font-size: 1.4rem; font-weight: 700;
    color: #8A2BE2;
}

.chat-wrap {
    background: #f8f9fa; border-radius: 15px;
    padding: 20px; height: 350px; overflow-y: auto;
}

.msg-row-ai { display:flex; justify-content:flex-start; margin:8px; }
.msg-row-user { display:flex; justify-content:flex-end; margin:8px; }

.bubble-ai {
    background:#fff; border-radius:15px 15px 15px 2px;
    padding:10px;
}
.bubble-user {
    background: linear-gradient(135deg,#FF0055,#7000FF);
    color:white; border-radius:15px 15px 2px 15px;
    padding:10px;
}

/* 🔥 버튼 */
div.stButton > button {
    background: linear-gradient(135deg,#FF0000,#8A2BE2) !important;
    color:white !important;
    border:none !important;
    border-radius:10px !important;
    transition:0.2s;
}
div.stButton > button:hover {
    transform: scale(1.05);
}

/* 🔥 타이머 */
.timer-container {
    width:100%; background:#eee;
    border-radius:10px; height:14px;
}
.timer-bar {
    height:100%;
    border-radius:10px;
    transition:0.1s linear;
}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 4. 초기화
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:

    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)

    mode = st.radio("모드", ["일반", "끄투"], horizontal=True)

    if mode == "일반":
        diff = st.radio("시간", ["20초","15초","10초","5초"], horizontal=True)
    else:
        diff = st.radio("전체 시간", ["150","120","90","60"], horizontal=True)

    if st.button("시작"):

        words,_ = load_word_data()
        index = defaultdict(list)
        for w in words:
            index[w[0]].append(w)

        first = random.choice(list(words))

        st.session_state.update({
            "words": words,
            "index": dict(index),
            "used": {first},
            "last_word": first,
            "history": [("AI", first)],
            "chain": 1,
            "mode": mode,
            "turn_start": time.time(),
            "game_start": time.time(),
            "game_over": False,
            "turn_limit": 5.0,
            "total_time": int(diff),
            "initialized": True
        })

        st.rerun()
    st.stop()

# ────────────────────────────────────────────────
# 5. UI 출력
# ────────────────────────────────────────────────
st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
st.markdown(f'<div class="chain-display">체인: {st.session_state.chain}</div>', unsafe_allow_html=True)

# 🔥 점수
score = st.session_state.chain * 10
st.markdown(f"<div style='text-align:center;'>점수: {score}</div>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 타이머
# ────────────────────────────────────────────────
if not st.session_state.game_over:

    if st.session_state.mode == "끄투":
        remaining = st.session_state.total_time - (time.time() - st.session_state.game_start)
    else:
        elapsed = time.time() - st.session_state.turn_start
        limit = max(2.0, 5 - st.session_state.chain // 3)
        remaining = limit - elapsed

    if remaining <= 0:
        st.session_state.game_over = True
        st.rerun()

    ratio = max(0, remaining / max(1, st.session_state.total_time))

    st.markdown(f"⏱ {remaining:.1f}초")

    st.markdown(
        f'<div class="timer-container"><div class="timer-bar" style="width:{ratio*100}%; background:red;"></div></div>',
        unsafe_allow_html=True
    )

# 힌트
starts = get_start_chars(st.session_state.last_word[-1])
st.markdown(f"<div class='rule-hint'>{' / '.join(starts)}</div>", unsafe_allow_html=True)

# 채팅
chat_html = '<div class="chat-wrap">'
for s,t in st.session_state.history:
    if s=="AI":
        chat_html += f'<div class="msg-row-ai"><div class="bubble-ai">{t}</div></div>'
    else:
        chat_html += f'<div class="msg-row-user"><div class="bubble-user">{t}</div></div>'
chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 입력
# ────────────────────────────────────────────────
if not st.session_state.game_over:

    user_input = st.text_input("")

    if user_input:
        word = user_input.strip()

        if word in st.session_state.words and word not in st.session_state.used:
            st.session_state.history.append(("User", word))
            st.session_state.used.add(word)
            st.session_state.chain += 1

            # AI
            candidates = []
            for ch in get_start_chars(word[-1]):
                candidates += st.session_state.index.get(ch, [])

            candidates = [w for w in candidates if w not in st.session_state.used]

            if not candidates:
                st.success("승리!")
                st.session_state.game_over = True
            else:
                ai = random.choice(candidates)
                st.session_state.history.append(("AI", ai))
                st.session_state.used.add(ai)
                st.session_state.last_word = ai
                st.session_state.chain += 1
                st.session_state.turn_start = time.time()

            st.rerun()

# 종료
if st.session_state.game_over:
    st.error("게임 종료")

    if st.button("다시"):
        st.session_state.clear()
        st.rerun()

if not st.session_state.game_over:
    time.sleep(0.1)
    st.rerun()
