import random
import time
import re
import streamlit as st
import streamlit.components.v1 as components
from collections import defaultdict

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
    except FileNotFoundError:
        pass
    return frozenset(["가구", "가방", "가수", "기차", "나비", "나무", "우주", "주스", "스낵", "노을", "음악"])

DUEUM = {
    '녀': '여', '뇨': '요', '뉴': '유', '니': '이', '랴': '야', '려': '여', '례': '예', '료': '요',
    '류': '유', '리': '이', '락': '낙', '래': '내', '랭': '냉', '략': '약', '량': '양', '령': '영',
    '로': '노', '뢰': '뇌', '룡': '용', '루': '누', '륙': '육', '륜': '윤', '률': '율', '릉': '능',
    '린': '인', '림': '임', '립': '입', '라': '나', '랄': '날', '람': '남', '랍': '납', '랑': '낭',
    '르': '느', '념': '염', '렴': '염', '름': '늠',
}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM: chars.add(DUEUM[last_char])
    return list(chars)

# ────────────────────────────────────────────────
# 2. 페이지 설정 및 CSS
# ────────────────────────────────────────────────
st.set_page_config(page_title="끝말잇기", layout="centered")

st.markdown("""
<style>
    .grad-title {
        background: linear-gradient(90deg, #FF0000, #8A2BE2);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 800; text-align: center; margin-bottom: 5px;
    }
    .chat-wrap { 
        background: #111; border-radius: 15px; padding: 20px; 
        height: 300px; overflow-y: auto; border: 1px solid #333; 
        margin-bottom: 10px; display: flex; flex-direction: column;
    }
    .msg-row-ai { display:flex; justify-content:flex-start; margin-bottom:12px; }
    .msg-row-user { display:flex; justify-content:flex-end; margin-bottom:12px; }
    .bubble-ai { background: #222; color: white; border: 1px solid #444; border-radius: 15px 15px 15px 2px; padding: 8px 12px; }
    .bubble-user { background: linear-gradient(135deg, #FF0055, #7000FF); color: white; border-radius: 15px 15px 2px 15px; padding: 8px 12px; }
    .timer-container { width: 100%; background-color: #333; border-radius: 10px; height: 18px; margin-bottom: 4px; overflow: hidden; }
    .bank-container { width: 100%; background-color: #222; border-radius: 5px; height: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 3. 게임 엔진 로직 (분리형 구조)
# ────────────────────────────────────────────────

# [A] 게임 입장 전 (초기화 화면)
if "initialized" not in st.session_state or not st.session_state.initialized:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1: total_rounds = st.number_input("총 라운드 수", 1, 10, 3)
    with col2: time_choice = st.selectbox("전체 제한 시간 (초)", [180, 120, 90, 60], index=1)
    with col3: difficulty = st.selectbox("AI 난이도", ["쉬움", "보통", "어려움"], index=1)
    
    if st.button("게임 입장하기"):
        words_data = load_word_data()
        valid_words = [w for w in words_data if len(w) >= 2]
        idx = defaultdict(list)
        for w in valid_words: idx[w[0]].append(w)
        
        first = random.choice(valid_words)
        now = time.time()
        
        st.session_state.update({
            "initialized": True,
            "difficulty": difficulty,
            "words": frozenset(valid_words),
            "index": dict(idx),
            "user_score": 0, "ai_score": 0,
            "current_round": 1, "total_rounds": total_rounds,
            "game_start_time": now, "total_limit": float(time_choice),
            "turn_start": now, "used": {first}, "last_word": first,
            "history": [("AI", first)], "round_over": False, "chain": 1
        })
        st.rerun()

# [B] 게임 진행 중 (화면 겹침 방지를 위해 else 사용)
else:
    # 4. 실시간 시간 계산
    now = time.time()
    total_limit = st.session_state.get("total_limit", 120.0)
    game_start_time = st.session_state.get("game_start_time", now)
    turn_start = st.session_state.get("turn_start", now)

    bank_rem = max(0.0, total_limit - (now - game_start_time))
    bank_ratio = bank_rem / total_limit
    dynamic_limit = min(20.0, 1.0 + (0.235 * (bank_rem ** 0.85)))
    turn_elapsed = now - turn_start
    actual_turn_rem = max(0.0, dynamic_limit - turn_elapsed)
    actual_turn_ratio = actual_turn_rem / dynamic_limit

    # 판정 로직을 위한 세션 동기화
    st.session_state.bank_rem = bank_rem
    st.session_state.actual_turn_rem = actual_turn_rem

    if not st.session_state.get("round_over", False):
        # 실시간 패배 판정
        if bank_rem <= 0 or actual_turn_rem <= 0:
            st.session_state.round_over = True
            st.session_state.ai_score += 1
            st.session_state.winner = "AI"
            st.rerun()

        # UI 출력
        st.write(f"### 🏎️ 라운드 {st.session_state.current_round} / {st.session_state.total_rounds}")
        
        # 타이머 바 시각화
        t_color = "#FF0055" if actual_turn_ratio < 0.3 else "#f1e05a"
        st.markdown(f"""
            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; border: 1px solid #444; margin-bottom: 20px;">
                <p style="margin:0; font-size:12px; color:#3a86ff; font-weight:bold;">🏦 전체 뱅크 타임 ({bank_rem:.1f}s)</p>
                <div class="bank-container"><div style="width:{bank_ratio*100}%; background:#3a86ff; height:100%;"></div></div>
                <p style="margin:12px 0 0 0; font-size:14px; color:{t_color}; font-weight:bold;">⚡ 차례 제한시간 ({actual_turn_rem:.1f}s)</p>
                <div class="timer-container"><div style="width:{actual_turn_ratio*100}%; background:{t_color}; height:100%;"></div></div>
            </div>
        """, unsafe_allow_html=True)

        # 채팅창 출력
        chat_html = '<div class="chat-wrap">'
        for speaker, text in st.session_state.history:
            side, bub = ("ai", "bubble-ai") if speaker == "AI" else ("user", "bubble-user")
            style = "color: #FF0000; font-weight: bold; border: 1px solid #FF0000;" if "🔥" in text else ""
            chat_html += f'<div class="msg-row-{side}"><div class="{bub}" style="{style}">{text.replace("🔥","")}</div></div>'
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)

        # 단어 입력 폼
        with st.form(key=f"input_form_{st.session_state.chain}", clear_on_submit=True):
            user_input = st.text_input("단어를 입력하세요:", placeholder=f"'{st.session_state.last_word[-1]}'로 시작하는 단어")
            submit = st.form_submit_button("전송")
            
            if submit and user_input:
                word = user_input.strip()
                # [핵심 추가] 두음법칙 포함 시작 가능 문자 리스트
                starts = get_start_chars(st.session_state.last_word[-1])
                
                if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                    st.session_state.used.add(word)
                    st.session_state.history.append(("User", word))
                    st.session_state.last_word = word
                    
                    # AI 대응
                    candidates = []
                    for ch in get_start_chars(word[-1]):
                        if ch in st.session_state.index:
                            valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                            candidates.extend(valid)
                    
                    diff = st.session_state.get("difficulty", "보통")
                    give_up = (diff == "쉬움" and random.random() < 0.15) or (diff == "보통" and random.random() < 0.05)
                    
                    if not candidates or give_up:
                        st.session_state.history[-1] = ("User", f"🔥{word}")
                        st.session_state.user_score += 1
                        st.session_state.round_over = True
                        st.session_state.winner = "User"
                    else:
                        ai_word = random.choice(candidates) # 간단히 랜덤 선택
                        st.session_state.used.add(ai_word)
                        st.session_state.history.append(("AI", ai_word))
                        st.session_state.last_word = ai_word
                        st.session_state.turn_start = time.time()
                        st.session_state.chain += 1
                    st.rerun()
                else:
                    st.error("❌ 유효하지 않은 단어입니다!")

        # 무한 새로고침 및 자동 포커스
        time.sleep(0.1)
        components.html("<script>window.parent.document.querySelector('input').focus();</script>", height=0)
        st.rerun()

    else:
        # [C] 라운드 종료 화면
        if st.session_state.winner == "AI":
            st.error(f"⏰ {st.session_state.current_round} 라운드 종료! AI 승리")
        else:
            st.success(f"🎊 {st.session_state.current_round} 라운드 종료! 유저 승리")
            
        if st.session_state.current_round < st.session_state.total_rounds:
            if st.button("다음 라운드 시작"):
                new_f = random.choice(list(st.session_state.words))
                now_reset = time.time()
                st.session_state.update({
                    "round_over": False, "current_round": st.session_state.current_round + 1,
                    "game_start_time": now_reset, "turn_start": now_reset,
                    "used": {new_f}, "last_word": new_f, "history": [("AI", new_f)], "chain": 1
                })
                st.rerun()
        else:
            st.balloons()
            st.write("### 🏁 모든 라운드 종료!")
            st.metric("최종 스코어", f"나 {st.session_state.user_score} : {st.session_state.ai_score} AI")
            if st.button("🔄 처음부터 다시 하기"):
                st.session_state.clear()
                st.rerun()
