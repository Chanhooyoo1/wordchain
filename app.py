import random
import time
import re
import streamlit as st
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
    '르': '느', '념': '염', '렴': '염',
}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM: chars.add(DUEUM[last_char])
    return list(chars)

# ────────────────────────────────────────────────
# 2. 페이지 설정 및 CSS
# ────────────────────────────────────────────────
st.set_page_config(page_title="끄투 온라인 Lite", layout="centered")

st.markdown("""
<style>
    .grad-title {
        background: linear-gradient(90deg, #FF0000, #8A2BE2);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 800; text-align: center; margin-bottom: 5px;
    }
    .chat-wrap { 
        background: #f8f9fa; border-radius: 15px; padding: 20px; 
        height: 300px; overflow-y: auto; border: 1px solid #e9ecef; 
        margin-bottom: 10px; display: flex; flex-direction: column;
    }
    .msg-row-ai { display:flex; justify-content:flex-start; margin-bottom:12px; }
    .msg-row-user { display:flex; justify-content:flex-end; margin-bottom:12px; }
    .bubble-ai { background: #ffffff; color: black; border: 1px solid #dee2e6; border-radius: 15px 15px 15px 2px; padding: 8px 12px; }
    .bubble-user { background: linear-gradient(135deg, #FF0055, #7000FF); color: white; border-radius: 15px 15px 2px 15px; padding: 8px 12px; }
    .timer-container { width: 100%; background-color: #333; border-radius: 10px; height: 18px; margin-bottom: 4px; overflow: hidden; }
    .bank-container { width: 100%; background-color: #222; border-radius: 5px; height: 8px; overflow: hidden; }
    div.stButton > button { background: linear-gradient(135deg, #FF0000, #8A2BE2) !important; color: white !important; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 3. 게임 초기화
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끄투 온라인 Lite</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: total_rounds = st.number_input("총 라운드 수", 1, 10, 3)
    with col2: time_choice = st.selectbox("턴 시간 제한 (초)", [120, 90, 60, 30, 10], index=3)
    
    if st.button("게임 입장하기"):
        bank_mapping = {120: 15.0, 90: 13.0, 60: 10.0, 30: 6.0, 10: 2.0}
        total_bank = bank_mapping.get(time_choice, 6.0)
        words_data = load_word_data()
        
        idx = defaultdict(list)
        valid_words = []
        for w in words_data:
            if w and len(w) >= 2:
                idx[w[0]].append(w)
                valid_words.append(w)
        
        first = random.choice(valid_words)
        st.session_state.update({
            "initialized": True, "words": frozenset(valid_words), "index": dict(idx),
            "user_score": 0, "ai_score": 0, "current_round": 1, "total_rounds": total_rounds,
            "turn_limit": float(time_choice), "total_bank_max": total_bank, "total_bank_current": total_bank,
            "used": {first}, "last_word": first, "history": [("AI", first)],
            "turn_start": time.time(), "round_over": False, "chain": 1, "winner": None
        })
        st.rerun()
    st.stop()

# ────────────────────────────────────────────────
# 4. 게임 엔진 및 UI 렌더링 (통합)
# ────────────────────────────────────────────────

if not st.session_state.get("game_over", False):
    # [1. 계산] 모든 변수를 출력보다 먼저 계산합니다.
    now = time.time()
    turn_elapsed = now - st.session_state.turn_start
    turn_rem = max(0.0, st.session_state.turn_limit - turn_elapsed)

    # 노란 바 다 닳으면 파란 바 차감
    if turn_rem <= 0:
        st.session_state.total_bank_current -= 0.1
        turn_rem = 0.0

    # 파란 바 다 닳으면 패배 처리
    if st.session_state.total_bank_current <= 0:
        st.session_state.total_bank_current = 0.0
        if not st.session_state.get("round_over", False):
            st.session_state.round_over = True
            st.session_state.ai_score += 1
            st.rerun()

    # [2. UI 데이터 준비]
    turn_ratio = turn_rem / st.session_state.turn_limit
    bank_ratio = st.session_state.total_bank_current / st.session_state.total_bank_max
    t_color = "#FF0055" if turn_rem < 3 else "#f1e05a"

    # [3. 실제 화면 출력]
    st.write(f"**Round {st.session_state.current_round} / {st.session_state.total_rounds}**")
    
    c1, c2 = st.columns(2)
    c1.metric("나 (User)", st.session_state.user_score)
    c2.metric("상대 (AI)", st.session_state.ai_score)

    # ────────────────────────────────────────────────
    # 🔥 [추가] 체인 및 시작 글자 안내 상자
    # ────────────────────────────────────────────────
    starts = get_start_chars(st.session_state.last_word[-1])
    starts_display = ", ".join(starts)
    
    st.markdown(f"""
        <div style="text-align: center; margin-top: 10px; margin-bottom: 15px;">
            <div style="display: inline-block; background: linear-gradient(135deg, #8A2BE2, #4B0082); color: white; padding: 4px 15px; border-radius: 20px; font-weight: bold; font-size: 1.1rem; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); border: 1px solid #fff;">
                🔥 {st.session_state.chain} CHAIN
            </div>
            <div style="background: #ffffff; border: 2px solid #8A2BE2; border-radius: 12px; padding: 12px; box-shadow: inset 0 0 10px rgba(138,43,226,0.1);">
                <div style="color: #666; font-size: 0.85rem; margin-bottom: 3px;">다음 시작 글자</div>
                <div style="color: #FF0055; font-size: 1.5rem; font-weight: 900; letter-spacing: 2px;">{starts_display}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # [4. 타이머 바]
    st.markdown(f"""
        <div style="width: 100%; background-color: #333; border-radius: 10px; height: 20px; overflow: hidden; margin-bottom: 5px; border: 1px solid #444;">
            <div style="width: {turn_ratio * 100}%; height: 100%; background: {t_color}; transition: width 0.11s linear;"></div>
        </div>
        <div style="width: 100%; background-color: #222; border-radius: 5px; height: 8px; overflow: hidden; border: 1px solid #333;">
            <div style="width: {bank_ratio * 100}%; height: 100%; background: #3a86ff; transition: width 0.11s linear;"></div>
        </div>
        <p style="text-align:right; font-size:12px; color:#888; margin-top:2px;">여유 시간: {st.session_state.total_bank_current:.1f}s</p>
    """, unsafe_allow_html=True)

    # [5. 채팅창]
    chat_html = '<div class="chat-wrap">'
    for speaker, text in st.session_state.history:
        side = "ai" if speaker == "AI" else "user"
        bub = "bubble-ai" if speaker == "AI" else "bubble-user"
        chat_html += f'<div class="msg-row-{side}"><div class="{bub}">{text}</div></div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)
# ────────────────────────────────────────────────
# 6. 입력 처리 및 AI 대응
# ────────────────────────────────────────────────
if not st.session_state.round_over:
    starts = get_start_chars(st.session_state.last_word[-1])
    st.caption(f"시작 글자: {', '.join(starts)}")
    
    with st.form(key="game_input", clear_on_submit=True):
        user_input = st.text_input("단어 입력", label_visibility="collapsed")
        if st.form_submit_button("전송") and user_input:
            word = user_input.strip()
            if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                # 유저 턴 성공
                st.session_state.used.add(word)
                st.session_state.history.append(("User", word))
                st.session_state.chain += 1
                
                # AI 즉시 대응
                candidates = []
                for ch in get_start_chars(word[-1]):
                    if ch in st.session_state.index:
                        valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                        candidates.extend(valid)
                
                if not candidates:
                    st.session_state.round_over = True
                    st.session_state.winner = "User"
                    st.session_state.user_score += 1
                else:
                    ai_word = random.choice(candidates)
                    st.session_state.used.add(ai_word)
                    st.session_state.history.append(("AI", ai_word))
                    st.session_state.last_word = ai_word
                    st.session_state.chain += 1
                    st.session_state.turn_start = time.time()
                st.rerun()
            else:
                st.toast("❌ 잘못된 단어입니다!")
else:
    # 결과 화면
    if st.session_state.winner == "User": st.success("🎉 승리! AI가 단어를 찾지 못했습니다.")
    else: st.error("💀 패배! 시간이 초과되었습니다.")
    
    if st.session_state.current_round < st.session_state.total_rounds:
        if st.button("다음 라운드 시작", key=f"next_{st.session_state.current_round}"):
            new_first = random.choice(list(st.session_state.words))
            st.session_state.update({
                "current_round": st.session_state.current_round + 1,
                "round_over": False, "used": {new_first}, "last_word": new_first,
                "history": [("AI", new_first)], "turn_start": time.time(), "winner": None
            })
            st.rerun()
    else:
        if st.button("🔄 전체 게임 재시작", key="restart"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

# 타이머 실시간 갱신
if not st.session_state.round_over:
    time.sleep(0.1)
    st.rerun()
