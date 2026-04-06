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
    return frozenset(["가구", "가방", "가수", "기차", "나비", "나무", "무지개", "개미"]), "기본 샘플"

# ────────────────────────────────────────────────
# 2. 로직 및 두음법칙
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
# 3. 페이지 설정 및 CSS
# ────────────────────────────────────────────────
st.set_page_config(page_title="한판 붙자! 끝말잇기", layout="centered")

st.markdown("""
<style>
    .grad-title {
        background: linear-gradient(90deg, #FF0000, #8A2BE2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 800; text-align: center; margin-bottom: 5px;
    }
    .chain-display { text-align: center; font-size: 1.2rem; font-weight: 700; color: #8A2BE2; }
    .chat-wrap { 
        background: #f8f9fa; border-radius: 15px; padding: 15px; 
        height: 300px; overflow-y: auto; border: 1px solid #e9ecef; margin-bottom: 10px;
    }
    .msg-row-ai { display:flex; justify-content:flex-start; margin-bottom:8px; }
    .msg-row-user { display:flex; justify-content:flex-end; margin-bottom:8px; }
    .bubble-ai { background: white; border: 1px solid #ddd; border-radius: 12px; padding: 8px 12px; }
    .bubble-user { background: #8A2BE2; color: white; border-radius: 12px; padding: 8px 12px; }
    .timer-container { width: 100%; background: #eee; border-radius: 10px; height: 10px; margin: 10px 0; }
    .timer-bar { height: 100%; border-radius: 10px; transition: width 0.1s linear; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 4. 세션 초기화
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
    diff = st.select_slider("난이도 선택 (시작 제한시간)", options=["지옥 (5초)", "어려움 (10초)", "보통 (20초)", "쉬움 (30초)"], value="보통 (20초)")
    
    if st.button("게임 시작!"):
        words, _ = load_word_data()
        idx = defaultdict(list)
        for w in words: idx[w[0]].append(w)
        
        times = {"지옥 (5초)": 5, "어려움 (10초)": 10, "보통 (20초)": 20, "쉬움 (30초)": 30}
        first = random.choice(list(words))
        
        st.session_state.update({
            "words": words, "index": dict(idx), "used": {first},
            "last_word": first, "history": [("AI", first)],
            "chain": 1, "turn_start": time.time(), "game_over": False, 
            "base_time": times[diff], "initialized": True, "winner": None
        })
        st.rerun()
    st.stop()

# ────────────────────────────────────────────────
# 5. 게임 엔진 (타이머 및 난이도 감소 로직)
# ────────────────────────────────────────────────
# 체인 2회당 1초씩 감소, 최저 2초 보장
current_limit = max(2.0, st.session_state.base_time - (st.session_state.chain // 2))

if not st.session_state.game_over:
    elapsed = time.time() - st.session_state.turn_start
    remaining = max(0.0, current_limit - elapsed)
    
    if remaining <= 0:
        st.session_state.game_over = True
        st.session_state.winner = "AI"
        st.rerun()

    # UI 출력
    st.markdown(f'<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chain-display">연결 성공: {st.session_state.chain} | 남은 시간: {remaining:.1f}초</div>', unsafe_allow_html=True)
    
    # 타이머 바 색상 변경
    ratio = remaining / current_limit
    t_color = "#28a745" if ratio > 0.5 else "#ffc107" if ratio > 0.2 else "#dc3545"
    st.markdown(f'<div class="timer-container"><div class="timer-bar" style="width: {ratio*100}%; background-color: {t_color};"></div></div>', unsafe_allow_html=True)

    # 채팅창 출력
    chat_html = '<div class="chat-wrap">'
    for speaker, text in st.session_state.history:
        cls = "msg-row-ai" if speaker == "AI" else "msg-row-user"
        bubble = "bubble-ai" if speaker == "AI" else "bubble-user"
        chat_html += f'<div class="{cls}"><div class="{bubble}">{text}</div></div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # 입력창
    starts = get_start_chars(st.session_state.last_word[-1])
    with st.form(key="input_form", clear_on_submit=True):
        user_input = st.text_input(f"'{' or '.join(starts)}'로 시작하는 단어 입력:", key="input_field")
        submitted = st.form_submit_button("전송")

    if submitted and user_input:
        word = user_input.strip()
        if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
            # 유저 성공
            st.session_state.used.add(word)
            st.session_state.history.append(("User", word))
            st.session_state.chain += 1
            
            # AI 턴 계산
            ai_starts = get_start_chars(word[-1])
            candidates = []
            for s in ai_starts:
                candidates.extend([w for w in st.session_state.index.get(s, []) if w not in st.session_state.used])
            
            if not candidates:
                st.session_state.game_over = True
                st.session_state.winner = "User"
            else:
                ai_word = random.choice(candidates)
                st.session_state.used.add(ai_word)
                st.session_state.history.append(("AI", ai_word))
                st.session_state.last_word = ai_word
                st.session_state.chain += 1
                st.session_state.turn_start = time.time() # AI가 말한 직후부터 유저 타이머 리셋
            st.rerun()
        else:
            st.error("잘못된 단어입니다! (중복, 미존재, 혹은 첫 글자 불일치)")

    # 실시간 타이머 갱신을 위한 루프
    time.sleep(0.1)
    st.rerun()

else:
    # 게임 종료 화면
    if st.session_state.winner == "User":
        st.balloons()
        st.success(f"축하합니다! AI를 이겼습니다! (기록: {st.session_state.chain}단어)")
    else:
        st.error(f"시간 초과! 패배했습니다. (기록: {st.session_state.chain}단어)")
    
    if st.button("다시 도전하기"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
