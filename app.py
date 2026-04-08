import random
import time
import re
import base64
import streamlit as st
import streamlit.components.v1 as components
from collections import defaultdict

# ────────────────────────────────────────────────
# 🔥 0. 오디오 재생 함수 (핵심)
# ────────────────────────────────────────────────
def play_sound(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f"""
            <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
            st.markdown(md, unsafe_allow_html=True)
    except:
        pass

# ────────────────────────────────────────────────
# 1. 데이터 로드 및 두음법칙
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_word_data():
    try:
        with open("words.js", "r", encoding="utf-8") as f:
            content = f.read()
        extracted = re.findall(r'["\']([가-힣]{2,4})["\']', content)
        if extracted:
            return frozenset(extracted)
    except:
        pass
    return frozenset(["가구", "가방", "가수", "기차", "나비", "나무", "우주", "주스"])

DUEUM = {'녀':'여','뇨':'요','뉴':'유','니':'이','라':'나','락':'낙','량':'양','려':'여','로':'노','루':'누'}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM:
        chars.add(DUEUM[last_char])
    return list(chars)

# ────────────────────────────────────────────────
# 2. UI
# ────────────────────────────────────────────────
st.set_page_config(page_title="끝말잇기", layout="centered")

st.markdown("""
<style>
.grad-title {
    background: linear-gradient(90deg, #FF0000, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 3rem;
    text-align: center;
}
.chat-wrap {
    height:300px;
    overflow-y:auto;
    background:#f8f9fa;
    padding:15px;
    border-radius:10px;
}
.bubble-ai {background:white; padding:8px 12px; border-radius:10px;}
.bubble-user {background:linear-gradient(135deg,#FF0055,#7000FF); color:white; padding:8px 12px; border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 3. 초기화
# ────────────────────────────────────────────────
if "init" not in st.session_state:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)

    rounds = st.number_input("라운드",1,10,3)
    total_time = st.selectbox("시간",[180,120,90],1)

    if st.button("시작"):
        words = load_word_data()
        idx = defaultdict(list)

        for w in words:
            idx[w[0]].append(w)

        first = random.choice(list(words))

        st.session_state.update({
            "init":True,
            "words":words,
            "index":idx,
            "used":{first},
            "last_word":first,
            "history":[("AI",first)],
            "chain":1,
            "round":1,
            "total_rounds":rounds,
            "time_limit":total_time,
            "start":time.time()
        })
        st.rerun()
    st.stop()

# ────────────────────────────────────────────────
# 🔥 사운드 트리거 처리
# ────────────────────────────────────────────────
if "sound" in st.session_state:
    play_sound(st.session_state.sound)
    del st.session_state.sound

# ────────────────────────────────────────────────
# 4. 게임 진행
# ────────────────────────────────────────────────
st.write(f"라운드 {st.session_state.round}")

# 채팅
html = '<div class="chat-wrap">'
for sp, txt in st.session_state.history:
    if sp=="AI":
        html += f'<div class="bubble-ai">{txt}</div>'
    else:
        html += f'<div class="bubble-user">{txt}</div>'
html += '</div>'
st.markdown(html, unsafe_allow_html=True)

# 입력
with st.form("input"):
    user = st.text_input("단어")
    submit = st.form_submit_button("전송")

    if submit and user:
        word = user.strip()

        starts = get_start_chars(st.session_state.last_word[-1])

        if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:

            # 🔥 입력 효과음
            st.session_state.sound = "input.mp3"

            st.session_state.used.add(word)
            st.session_state.history.append(("User",word))
            st.session_state.last_word = word

            # AI
            candidates=[]
            for ch in get_start_chars(word[-1]):
                if ch in st.session_state.index:
                    candidates += [w for w in st.session_state.index[ch] if w not in st.session_state.used]

            if not candidates:
                st.success("승리!")
                st.stop()

            ai = random.choice(candidates)

            # 🔥 AI 효과음
            st.session_state.sound = "ai.mp3"

            st.session_state.used.add(ai)
            st.session_state.history.append(("AI",ai))
            st.session_state.last_word = ai

            st.rerun()
        else:
            st.error("틀림")

# ────────────────────────────────────────────────
# 자동 새로고침
# ────────────────────────────────────────────────
time.sleep(0.2)
st.rerun()
