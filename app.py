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
    return frozenset(["가구", "가방", "가수", "기차", "나비", "나무"]), "기본 샘플"


# ────────────────────────────────────────────────
# 2. 두음법칙
# ────────────────────────────────────────────────
DUEUM = {
    '녀': '여','뇨': '요','뉴': '유','니': '이',
    '랴': '야','려': '여','례': '예','료': '요',
    '류': '유','리': '이','라': '나','래': '내',
    '로': '노','루': '누'
}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM:
        chars.add(DUEUM[last_char])
    return list(chars)


# ────────────────────────────────────────────────
# 3. UI
# ────────────────────────────────────────────────
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
.chain-display {
    text-align:center;
    font-size:1.5rem;
    font-weight:700;
}
.timer-container { width:100%; background:#eee; border-radius:10px; height:14px;}
.timer-bar { height:100%; border-radius:10px;}
.danger {color:red;}
.blink {animation:blink 0.5s infinite;}
@keyframes blink {0%{opacity:1;}50%{opacity:0.3;}100%{opacity:1;}}
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────
# 4. 초기화
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)

    diff = st.radio("시간", ["쉬움 (20초)", "보통 (15초)", "어려움 (10초)", "지옥 (5초)"], horizontal=True)

    if st.button("끝말잇기 시작!"):
        words, _ = load_word_data()
        index = defaultdict(list)

        for w in words:
            index[w[0]].append(w)

        first = random.choice(list(words))

        base_times = {"쉬움 (20초)":20,"보통 (15초)":15,"어려움 (10초)":10,"지옥 (5초)":5}

        total_times = {"쉬움 (20초)":150,"보통 (15초)":120,"어려움 (10초)":90,"지옥 (5초)":60}

        st.session_state.update({
            "words": words,
            "index": dict(index),
            "used": {first},
            "last_word": first,
            "history": [("AI", first)],
            "chain": 1,

            "turn_start": time.time(),
            "game_start": time.time(),

            "base_time": base_times[diff],
            "total_time": total_times[diff],

            "game_over": False,
            "initialized": True,
            "winner": None
        })

        st.rerun()

    st.stop()


# ────────────────────────────────────────────────
# 5. 시간 계산
# ────────────────────────────────────────────────
base_time = st.session_state.base_time
current_max_time = base_time - (st.session_state.chain // 3)
current_max_time = max(2.0, current_max_time)

elapsed_turn = time.time() - st.session_state.turn_start
remaining_turn = max(0.0, current_max_time - elapsed_turn)

elapsed_total = time.time() - st.session_state.game_start
remaining_total = max(0.0, st.session_state.total_time - elapsed_total)

ratio = remaining_total / st.session_state.total_time


# ────────────────────────────────────────────────
# 6. UI
# ────────────────────────────────────────────────
st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
st.markdown(f'<div class="chain-display">이은 단어 수: {st.session_state.chain}</div>', unsafe_allow_html=True)

if not st.session_state.game_over:

    # 게임오버 체크
    if remaining_turn <= 0 or remaining_total <= 0:
        st.session_state.game_over = True
        st.rerun()

    # 텍스트
    st.markdown(f"⏳ 전체 시간: {remaining_total:.1f}초")
    
    if remaining_turn <= 2.5:
        st.markdown(f'<div class="danger blink">⚡ {remaining_turn:.1f}초</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"⚡ 입력 시간: {remaining_turn:.1f}초")

    # 타이머 바
    if ratio > 0.7:
        color = "#28a745"
    elif ratio > 0.4:
        color = "#ffc107"
    elif ratio > 0.2:
        color = "#fd7e14"
    else:
        color = "#dc3545"

    st.markdown(
        f'<div class="timer-container"><div class="timer-bar" style="width:{ratio*100}%;background:{color};"></div></div>',
        unsafe_allow_html=True
    )

# 힌트
starts = get_start_chars(st.session_state.last_word[-1])
st.markdown(" / ".join(starts))


# ────────────────────────────────────────────────
# 7. 입력
# ────────────────────────────────────────────────
if not st.session_state.game_over:
    user_input = st.text_input("단어 입력")

    if user_input:
        word = user_input.strip()
        possible = get_start_chars(st.session_state.last_word[-1])

        if word in st.session_state.words and word not in st.session_state.used and word[0] in possible:

            st.session_state.used.add(word)
            st.session_state.chain += 1
            st.session_state.last_word = word

            # AI
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
            st.warning("❌ 단어 오류")


# ────────────────────────────────────────────────
# 8. 종료
# ────────────────────────────────────────────────
if st.session_state.game_over:
    st.error("💀 게임 종료")

    if st.button("다시 시작"):
        st.session_state.clear()
        st.rerun()

time.sleep(0.1)
st.rerun()
