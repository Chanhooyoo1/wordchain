import random
import time
import re
import streamlit as st
from collections import defaultdict

# 🔊 base64 효과음 (짧은 클릭)
SOUND_BASE64 = "UklGRigAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA="

def play_sound(speed=1.0):
    st.components.v1.html(f"""
    <script>
    const audio = new Audio("data:audio/wav;base64,{SOUND_BASE64}");
    audio.playbackRate = {speed};
    audio.play().catch(()=>{{}});
    </script>
    """, height=0)

# ─────────────────────────────
# 두음법칙
# ─────────────────────────────
DUEUM = {
    '녀':'여','뇨':'요','뉴':'유','니':'이',
    '랴':'야','려':'여','례':'예','료':'요',
    '류':'유','리':'이','라':'나','래':'내',
    '로':'노','루':'누'
}

def get_start_chars(last):
    chars = {last}
    if last in DUEUM:
        chars.add(DUEUM[last])
    return list(chars)

# ─────────────────────────────
# 데이터
# ─────────────────────────────
@st.cache_data
def load_words():
    try:
        with open("words.js","r",encoding="utf-8") as f:
            txt = f.read()
        return list(set(re.findall(r'["\']([가-힣]{2,4})["\']',txt)))
    except:
        return ["가구","가방","가수","기차","나비","나무","라면","노트","도시","사람"]

# ─────────────────────────────
# UI
# ─────────────────────────────
st.set_page_config(page_title="끝말잇기", layout="centered")

st.markdown("""
<style>
.title {font-size:2.5rem;text-align:center;font-weight:800;}
.timer{height:12px;background:#eee;border-radius:10px;}
.bar{height:100%;border-radius:10px;}
.blink{animation:blink 0.5s infinite;}
@keyframes blink{0%{opacity:1;}50%{opacity:0.3;}100%{opacity:1;}}
@keyframes pop{
0%{transform:scale(0.5);opacity:0;}
50%{transform:scale(1.4);opacity:1;}
100%{transform:scale(1);opacity:0;}
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────
# 초기화
# ─────────────────────────────
TOTAL = {"150초":150,"120초":120,"90초":90,"60초":60}

if "init" not in st.session_state:
    st.markdown('<div class="title">끝말잇기</div>', unsafe_allow_html=True)
    diff = st.radio("전체 시간", list(TOTAL.keys()), horizontal=True)

    if st.button("시작"):
        words = load_words()
        index = defaultdict(list)
        for w in words:
            index[w[0]].append(w)

        first = random.choice(words)

        st.session_state.update({
            "words":words,
            "index":dict(index),
            "used":{first},
            "last":first,
            "chain":1,

            "game_start":time.time(),
            "turn_start":time.time(),
            "turn_limit":5,

            "total":TOTAL[diff],
            "over":False,

            "last_score":0,
            "pop":0,

            "init":True
        })
        st.rerun()
    st.stop()

# ─────────────────────────────
# 점수
# ─────────────────────────────
chain = st.session_state.chain
remaining = max(0, st.session_state.total-(time.time()-st.session_state.game_start))

mult = 1 if chain<10 else 2 if chain<20 else 3 if chain<30 else 5
score = chain*10*mult + int(remaining)

delta = score - st.session_state.last_score
if delta > 0:
    st.session_state.pop = delta
    st.session_state.last_score = score

# ─────────────────────────────
# 상단 UI
# ─────────────────────────────
st.markdown(f"<h2 style='text-align:center;'>🔥 체인 {chain}</h2>", unsafe_allow_html=True)
st.markdown(f"<h3 style='text-align:center;'>점수 {score}</h3>", unsafe_allow_html=True)

# 점수 팝
if st.session_state.pop > 0:
    st.markdown(f"""
    <div style="text-align:center;font-size:2rem;color:#FF0055;animation:pop 0.6s;">
    +{st.session_state.pop}
    </div>
    """, unsafe_allow_html=True)
    st.session_state.pop = 0

# ─────────────────────────────
# 타이머
# ─────────────────────────────
if not st.session_state.over:
    total_rem = st.session_state.total - (time.time() - st.session_state.game_start)
    turn_rem = st.session_state.turn_limit - (time.time() - st.session_state.turn_start)

    ratio = max(0, total_rem / st.session_state.total)

    # ⚠ 긴급 상태
    if turn_rem <= 3:
        st.markdown(f"<div class='blink' style='color:red;text-align:center;'>⚠ {turn_rem:.1f}s</div>", unsafe_allow_html=True)
        play_sound(1.8)
    else:
        st.markdown(f"<div style='text-align:center;'>⏱ {turn_rem:.1f}s</div>", unsafe_allow_html=True)

    color = "#28a745" if ratio>0.7 else "#ffc107" if ratio>0.4 else "#fd7e14" if ratio>0.2 else "#dc3545"

    st.markdown(f"<div class='timer'><div class='bar' style='width:{ratio*100}%;background:{color};'></div></div>", unsafe_allow_html=True)

    if total_rem <= 0 or turn_rem <= 0:
        st.session_state.over = True
        st.rerun()

# ─────────────────────────────
# 입력
# ─────────────────────────────
if not st.session_state.over:
    user = st.text_input("", placeholder="단어 입력")

    if user:
        word = user.strip()
        possible = get_start_chars(st.session_state.last[-1])

        if word in st.session_state.words and word not in st.session_state.used and word[0] in possible:

            st.session_state.used.add(word)
            st.session_state.chain += 1
            st.session_state.last = word
            st.session_state.turn_start = time.time()

            # 🔥 효과음 속도 4단계
            c = st.session_state.chain
            speed = 1 if c<10 else 1.2 if c<20 else 1.5 if c<30 else 2.0
            play_sound(speed)

            # AI
            candidates = []
            for ch in get_start_chars(word[-1]):
                if ch in st.session_state.index:
                    candidates += [
                        w for w in st.session_state.index[ch]
                        if w not in st.session_state.used
                    ]

            if candidates:
                ai = random.choice(candidates)
                st.session_state.used.add(ai)
                st.session_state.chain += 1
                st.session_state.last = ai
                st.session_state.turn_start = time.time()

            else:
                st.session_state.over = True

            st.rerun()
        else:
            st.warning("❌ 단어 오류")

# ─────────────────────────────
# 종료
# ─────────────────────────────
if st.session_state.over:
    st.error("💀 게임 종료")
    if st.button("다시 시작"):
        st.session_state.clear()
        st.rerun()

time.sleep(0.1)
st.rerun()
