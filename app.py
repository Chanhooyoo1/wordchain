import random
import time
import re
import streamlit as st
from collections import defaultdict

# ─────────────────────────────
# 1. 데이터 로드
# ─────────────────────────────
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

# ─────────────────────────────
# 2. 두음법칙
# ─────────────────────────────
DUEUM = {
    '녀':'여','뇨':'요','뉴':'유','니':'이',
    '랴':'야','려':'여','례':'예','료':'요',
    '류':'유','리':'이','라':'나','래':'내',
    '로':'노','루':'누'
}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM:
        chars.add(DUEUM[last_char])
    return list(chars)

# ─────────────────────────────
# 3. UI
# ─────────────────────────────
st.set_page_config(page_title="끝말잇기", layout="centered")

st.markdown("""
<style>
.grad-title {
    background: linear-gradient(90deg, #FF0000, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 3rem;
    font-weight: 800;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────
# 4. 초기화 (🔥 핵심 수정)
# ─────────────────────────────
total_times = {
    "쉬움 (150초)":150,
    "보통 (120초)":120,
    "어려움 (90초)":90,
    "지옥 (60초)":60
}

if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)

    diff = st.radio("시간", list(total_times.keys()), horizontal=True)

    if st.button("끝말잇기 시작!"):
        words, _ = load_word_data()
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

            "game_start": time.time(),
            "turn_start": time.time(),
            "turn_limit": 5.0,

            "game_over": False,
            "total_time": total_times[diff],
            "initialized": True,
            "winner": None
        })

        st.rerun()

    st.stop()   # 🔥 여기 반드시 필요

# ─────────────────────────────
# 5. 점수 (🔥 위치 수정)
# ─────────────────────────────
chain = st.session_state.chain
remaining = max(0, st.session_state.total_time - (time.time() - st.session_state.game_start))

if chain < 10:
    multiplier = 1
elif chain < 20:
    multiplier = 2
elif chain < 30:
    multiplier = 3
else:
    multiplier = 5

score = chain * 10 * multiplier + int(remaining)

# ─────────────────────────────
# 6. UI
# ─────────────────────────────
st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
st.markdown(f"체인: {chain}")
st.markdown(f"점수: {score}")

# ─────────────────────────────
# 7. 타이머
# ─────────────────────────────
if not st.session_state.game_over:
    elapsed_total = time.time() - st.session_state.game_start
    remaining_total = st.session_state.total_time - elapsed_total

    elapsed_turn = time.time() - st.session_state.turn_start
    remaining_turn = st.session_state.turn_limit - elapsed_turn

    if remaining_total <= 0 or remaining_turn <= 0:
        st.session_state.game_over = True
        st.rerun()

    st.write(f"전체 시간: {remaining_total:.1f}초")
    st.write(f"입력 시간: {remaining_turn:.1f}초")

# ─────────────────────────────
# 8. 입력
# ─────────────────────────────
if not st.session_state.game_over:
    user_input = st.text_input("단어 입력")

    if user_input:
        word = user_input.strip()
        possible = get_start_chars(st.session_state.last_word[-1])

        if word in st.session_state.words and word not in st.session_state.used and word[0] in possible:

            st.session_state.used.add(word)
            st.session_state.chain += 1
            st.session_state.last_word = word

            candidates = []
            for ch in get_start_chars(word[-1]):
                if ch in st.session_state.index:
                    valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                    candidates.extend(valid)

            if not candidates:
                st.session_state.game_over = True
                st.session_state.winner = "User"
            else:
                ai_word = random.choice(candidates)
                st.session_state.used.add(ai_word)
                st.session_state.chain += 1
                st.session_state.last_word = ai_word
                st.session_state.turn_start = time.time()

            st.rerun()
        else:
            st.warning("❌ 잘못된 단어")

# ─────────────────────────────
# 9. 종료
# ─────────────────────────────
if st.session_state.game_over:
    st.error("💀 게임 종료")

    if st.button("다시 시작"):
        st.session_state.clear()
        st.rerun()
