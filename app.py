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
    # 기본 샘플 단어 확장
    return frozenset(["가구", "가방", "가수", "기차", "나비", "나무", "우주", "주스", "스낵", "노을", "음악"]), "기본 샘플"

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
    if last_char in DUEUM: 
        chars.add(DUEUM[last_char])
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
    .timer-bar { height: 100%; border-radius: 10px; transition: width 0.1s linear; }
    .rule-hint { font-size: 0.9rem; color: #666; margin-bottom: 10px; text-align: center; background: #f0f2f6; padding: 5px; border-radius: 8px; }

    div.stButton > button {
        background: linear-gradient(135deg, #FF0000, #8A2BE2) !important;
        color: white !important; border: none !important; font-weight: 600 !important;
        border-radius: 8px !important; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 4. 게임 초기화 및 라운드 설정
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끄투 온라인 Lite</div>', unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        total_rounds = st.number_input("총 라운드 수", min_value=1, max_value=10, value=3)
    with col2:
        turn_limit = st.slider("턴 시간 제한 (초)", min_value=3, max_value=20, value=10)
    
    if st.button("게임 입장하기"):
        words, _ = load_word_data()
        idx = defaultdict(list)
        for w in words: idx[w[0]].append(w)
        
        first_word = random.choice(list(words))
        st.session_state.update({
            "initialized": True,
            "words": words, "index": dict(idx),
            "total_rounds": total_rounds, "current_round": 1,
            "turn_limit": turn_limit,
            "user_score": 0, "ai_score": 0,
            "round_over": False, "game_complete": False,
            # 라운드별 데이터
            "used": {first_word}, "last_word": first_word,
            "history": [("AI", first_word)], "turn_start": time.time()
        })
        st.rerun()
    st.stop()

# ────────────────────────────────────────────────
# 5. 게임 로직 (라운드 및 턴 타이머)
# ────────────────────────────────────────────────
if not st.session_state.game_complete:
    # 턴 시간 계산
    elapsed = time.time() - st.session_state.turn_start
    remaining = max(0.0, st.session_state.turn_limit - elapsed)
    
    # 시간 초과 시 라운드 종료
    if remaining <= 0 and not st.session_state.round_over:
        st.session_state.round_over = True
        st.session_state.ai_score += 1
        st.rerun()

    # 상단 정보 표시
    st.markdown(f'<div class="round-info">Round {st.session_state.current_round} / {st.session_state.total_rounds}</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    cols[0].metric("나 (User)", st.session_state.user_score)
    cols[1].metric("상대 (AI)", st.session_state.ai_score)

    # 턴 타이머 바
    t_color = "#FF0055" if remaining < 3 else "#7000FF"
    ratio = remaining / st.session_state.turn_limit
    st.markdown(f"⏱ **나의 남은 시간: {remaining:.1f}초**")
    st.markdown(f'<div class="timer-container"><div class="timer-bar" style="width:{ratio*100}%; background:{t_color};"></div></div>', unsafe_allow_html=True)

    # 채팅창
    chat_html = '<div class="chat-wrap">'
    for speaker, text in st.session_state.history:
        cls = "msg-row-ai" if speaker == "AI" else "msg-row-user"
        bub = "bubble-ai" if speaker == "AI" else "bubble-user"
        chat_html += f'<div class="{cls}"><div class="{bub}">{text}</div></div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # 입력 폼
    if not st.session_state.round_over:
        starts = get_start_chars(st.session_state.last_word[-1])
        st.caption(f"다음 단어 시작: {', '.join(starts)}")
        
        with st.form(key="turn_form", clear_on_submit=True):
            user_word = st.text_input("단어를 입력하세요", label_visibility="collapsed")
            submitted = st.form_submit_button("전송")
            
        if submitted and user_word:
            word = user_word.strip()
            if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                # 유저 성공
                st.session_state.used.add(word)
                st.session_state.history.append(("User", word))
                
                # AI 즉시 대응
                candidates = []
                for ch in get_start_chars(word[-1]):
                    if ch in st.session_state.index:
                        valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                        candidates.extend(valid)
                
                if not candidates:
                    st.session_state.round_over = True
                    st.session_state.user_score += 1
                else:
                    ai_choice = random.choice(candidates)
                    st.session_state.used.add(ai_choice)
                    st.session_state.history.append(("AI", ai_choice))
                    st.session_state.last_word = ai_choice
                    st.session_state.turn_start = time.time() # 턴 시간 리셋
                st.rerun()
            else:
                st.toast("잘못된 단어입니다!")
    else:
        # 라운드 종료 화면
        st.warning("라운드가 종료되었습니다!")
        if st.session_state.current_round < st.session_state.total_rounds:
            if st.button("다음 라운드 시작"):
                # 단어 리스트 초기화 및 다음 라운드 설정
                new_first = random.choice(list(st.session_state.words))
                st.session_state.update({
                    "current_round": st.session_state.current_round + 1,
                    "round_over": False,
                    "used": {new_first}, "last_word": new_first,
                    "history": [("AI", new_first)], "turn_start": time.time()
                })
                st.rerun()
        else:
            st.session_state.game_complete = True
            st.rerun()

    # 실시간 타이머 갱신 (반복문 역할)
    if not st.session_state.round_over:
        time.sleep(0.1)
        st.rerun()

# ────────────────────────────────────────────────
# 6. 입력 및 처리
# ────────────────────────────────────────────────
