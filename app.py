import random
import time
import re
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
# 2. 로직 및 두음법칙 매핑
# ────────────────────────────────────────────────
DUEUM = {
    '녀': '여', '뇨': '요', '뉴': '유', '니': '이', '랴': '야', '려': '여', '례': '예', '료': '요',
    '류': '유', '리': '이', '락': '낙', '래': '내', '랭': '냉', '략': '약', '량': '양', '령': '영',
    '로': '노', '뢰': '뇌', '룡': '용', '루': '누', '륙': '육', '륜': '윤', '률': '율', '릉': '능',
    '린': '인', '림': '임', '립': '입', '라': '나', '랄': '날', '람': '남', '랍': '납', '랑': '낭',
    '르': '느', '념': '염', '렴': '염',
}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM: chars.add(DUEUM[last_char])
    return list(chars)

# ────────────────────────────────────────────────
# 3. 커스텀 CSS
# ────────────────────────────────────────────────
st.set_page_config(page_title="끝말잇기", layout="centered")

st.markdown("""
<style>
    .grad-title {
        background: linear-gradient(90deg, #FF0000, #8A2BE2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 800; text-align: center; margin-bottom: 5px;
    }
    .chain-display {
        text-align: center; font-size: 1.5rem; font-weight: 700; color: #8A2BE2; margin-bottom: 10px;
    }
    .chat-wrap { 
        background: #f8f9fa; border-radius: 15px; padding: 20px; 
        height: 350px; overflow-y: auto; border: 1px solid #e9ecef; 
        margin-bottom: 10px; display: flex; flex-direction: column;
    }
    .msg-row-ai { display:flex; justify-content:flex-start; margin-bottom:12px; }
    .msg-row-user { display:flex; justify-content:flex-end; margin-bottom:12px; }
    .bubble-ai { background: #ffffff; color: #000000 !important; border: 1px solid #dee2e6; border-radius: 15px 15px 15px 2px; padding: 10px 15px; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .bubble-user { background: linear-gradient(135deg, #FF0055, #7000FF); color: white; border-radius: 15px 15px 2px 15px; padding: 10px 15px; font-weight: 500; }
    
    .timer-container { width: 100%; background-color: #eee; border-radius: 10px; margin: 10px 0; height: 14px; }
    .timer-bar { height: 100%; border-radius: 10px; transition: width 0.1s linear, background-color 0.3s ease; }
    .rule-hint { font-size: 0.9rem; color: #666; margin-bottom: 10px; text-align: center; background: #f0f2f6; padding: 5px; border-radius: 8px; }

    div.stButton > button {
        background: linear-gradient(135deg, #FF0000, #8A2BE2) !important;
        color: white !important; border: none !important; font-weight: 600 !important;
        border-radius: 8px !important; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 4. 세션 초기화
# ────────────────────────────────────────────────
# ────────────────────────────────────────────────
# 4. 세션 초기화 (끄투 모드)
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
    st.write("### 전체 시간을 선택해주세요.")

    diff = st.radio(
        "시간",
        ["쉬움 (150초)", "보통 (120초)", "어려움 (90초)", "지옥 (60초)"],
        horizontal=True
    )

    print("PC환경에서 실행을 권장합니다.")

    if st.button("끝말잇기 시작!"):
        words, _ = load_word_data()
        index = defaultdict(list)

        for w in words:
            index[w[0]].append(w)

        # 🔥 전체 시간 (끄투 방식)
        total_times = {
            "쉬움 (150초)": 150,
            "보통 (120초)": 120,
            "어려움 (90초)": 90,
            "지옥 (60초)": 60
        }

        first = random.choice(list(words))

        st.session_state.update({
            "words": words,
            "index": dict(index),
            "used": {first},
            "last_word": first,
            "history": [("AI", first)],
            "chain": 1,
            "game_start": time.time(),   # 🔥 핵심
            "game_over": False,
            "total_time": total_times[diff],  # 🔥 핵심
            "initialized": True,
            "winner": None
        })

        st.rerun()

    st.stop()

# ────────────────────────────────────────────────
# 5. 게임 로직 및 화면
# ────────────────────────────────────────────────
st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
st.markdown(f'<div class="chain-display">이은 단어 수: {st.session_state.chain}</div>', unsafe_allow_html=True)

if not st.session_state.game_over:
    # 🔥 전체 시간 계산 (끄투 방식)
    elapsed = time.time() - st.session_state.game_start
    total_time = st.session_state.total_time

    remaining = max(0.0, total_time - elapsed)
    ratio = remaining / total_time

    # 🔥 게임 오버 체크
    if remaining <= 0:
        st.session_state.game_over = True
        st.rerun()

    # 🔥 타이머 텍스트
    if remaining <= 10:
        st.markdown(f'<div class="danger blink">⏱ {remaining:.1f}초 (위험!)</div>', unsafe_allow_html=True)
    elif remaining <= 20:
        st.markdown(f'<div class="danger">⏱ {remaining:.1f}초</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"⏱ {remaining:.1f}초")

    # 🔥 타이머 색상
    if ratio > 0.7:
        t_color = "#28a745"
    elif ratio > 0.4:
        t_color = "#ffc107"
    elif ratio > 0.2:
        t_color = "#fd7e14"
    else:
        t_color = "#dc3545"

    # 🔥 타이머 바
    st.markdown(
        f'<div class="timer-container"><div class="timer-bar" style="width: {ratio*100}%; background-color: {t_color};"></div></div>',
        unsafe_allow_html=True
    )

# 🔥 힌트는 밖에 둬도 OK
starts = get_start_chars(st.session_state.last_word[-1])
hint_text = " 또는 ".join([f'<b>"{s}"</b>' for s in starts])
st.markdown(f'<div class="rule-hint">{hint_text}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="rule-hint">{hint_text}</div>', unsafe_allow_html=True)

# 채팅 출력
chat_html = f'<div class="chat-wrap" id="chat-container">'
for speaker, text in st.session_state.history:
    if speaker == "AI": chat_html += f'<div class="msg-row-ai"><div class="bubble-ai"> {text}</div></div>'
    else: chat_html += f'<div class="msg-row-user"><div class="bubble-user">{text} 👤</div></div>'
chat_html += '</div>'
st.markdown(chat_html, unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 6. 입력 및 자동화 (포커스/스크롤 고도화)
# ────────────────────────────────────────────────
if not st.session_state.game_over:
    with st.form(key="fixed_form", clear_on_submit=True):
            cols = st.columns([4, 1])
            user_input = cols[0].text_input("입력", placeholder="전송하려면 엔터를 누르세요..", label_visibility="collapsed")
            submit = cols[1].form_submit_button("전송")
    
        # 🔥 JS: 포커스와 스크롤을 무조건 잡을 때까지 반복 (MutationObserver급 신뢰도)
    st.components.v1.html("""
    <script>
    const fixUI = () => {
        const win = window.parent.document;
    
        const chat = win.querySelector('.chat-wrap');
        const input = win.querySelector('input');
    
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }
    
        if (input && win.activeElement !== input) {
            input.focus();
        }
    };
    
    // DOM 바뀔 때마다 실행
    const observer = new MutationObserver(fixUI);
    observer.observe(window.parent.document.body, {
        childList: true,
        subtree: true
    });
    
    // 반복 보정
    setInterval(fixUI, 400);
    
    // 초기 실행
    fixUI();
    </script>
    """, height=0)

    if submit and user_input:
        word = user_input.strip()
        possible_starts = get_start_chars(st.session_state.last_word[-1])
        
        if word in st.session_state.words and word not in st.session_state.used and word[0] in possible_starts:
            st.session_state.used.add(word)
            st.session_state.history.append(("User", word))
            st.session_state.chain += 1
            st.session_state.last_word = word
            st.components.v1.html("""
            <script>
            const audio = new Audio("https://cdn.pixabay.com/download/audio/2022/03/15/audio_115b9b3c1c.mp3?filename=mouse-click-153941.mp3");
            audio.play().catch(()=>{});
            </script>
            """, height=0)
            
            # 🔥 [랜덤 지연 시간] 체인이 높을수록 대기 시간을 '뺍니다'
            # 시작 대기 2.5초, 체인당 0.1초 차감, 최소 0.2초
            calc_wait = max(0.5, 3.5 - (st.session_state.chain * 0.1))
            wait_time = random.uniform(calc_wait * 0.85, calc_wait) # 70%~100% 사이의 랜덤초
            
            with st.spinner(f"AI가 고민 중..."):
                time.sleep(wait_time) 
            
            candidates = []
            for ch in get_start_chars(word[-1]):
                if ch in st.session_state.index:
                    valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                    candidates.extend(valid)
            
            if not candidates:
                st.session_state.game_over = True
                st.session_state.winner = "User"
                st.balloons()
                st.snow()
            else:
                ai_word = random.choice(candidates)
                st.session_state.used.add(ai_word)
                st.session_state.history.append(("AI", ai_word))
                st.session_state.last_word = ai_word
                st.session_state.chain += 1
                st.session_state.turn_start = time.time()
            st.rerun()
        else:
            st.toast("❌ 잘못되거나 이미 사용한 단어입니다.")

else:
    if st.session_state.get("winner") == "User":
        st.success("🎉 승리! AI를 이겼습니다!")
    else:
        st.error(f"💀 패배.. {st.session_state.chain}번 말을 이었습니다.")
    
    if st.button("🔄다시 시작"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

if not st.session_state.game_over:
    time.sleep(0.1)
    st.rerun()
