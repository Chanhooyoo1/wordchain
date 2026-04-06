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
# 3. 게임 초기화 (입장 전 화면)
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
    
    # 설정 UI: 3개의 컬럼으로 깔끔하게 배치 (카드 스타일 컨테이너)
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1: 
            total_rounds = st.number_input("🏁 총 라운드 수", 1, 10, 3)
        with col2: 
            time_choice = st.selectbox("⏱️ 전체 제한 시간", [180, 120, 90, 60], index=1)
        with col3: 
            difficulty = st.selectbox("🤖 AI 난이도", ["쉬움", "보통", "어려움"], index=1)
        
        # 버튼에 마우스를 올리면 scale up 되는 럭셔리 버튼
        if st.button("🚀 게임 입장하기 (Enter)"):
            # 단어 데이터 로드
            words_data = load_word_data()
            
            idx = defaultdict(list)
            valid_words = []
            for w in words_data:
                if w and len(w) >= 2:
                    idx[w[0]].append(w)
                    valid_words.append(w)
            
            # 방어 코드
            if not valid_words:
                valid_words = ["기차", "나무", "나비", "우주", "주스"]
                for w in valid_words: idx[w[0]].append(w)

            first = random.choice(valid_words)
            now = time.time()
            
            st.session_state.update({
                "initialized": True, 
                "difficulty": difficulty, 
                "words": frozenset(valid_words), 
                "index": dict(idx),
                "user_score": 0, 
                "ai_score": 0, 
                "current_round": 1, 
                "total_rounds": total_rounds,
                "game_start_time": now,
                "total_limit": float(time_choice),
                "turn_start": now,
                "used": {first}, 
                "last_word": first, 
                "history": [("AI", first)],
                "round_over": False, 
                "chain": 1, 
                "winner": None
            })
            st.rerun()
            st.stop()

# ────────────────────────────────────────────────
# 4. 실시간 가속 엔진 (물리 기반 타이머)
# ────────────────────────────────────────────────
now = time.time()
total_limit = st.session_state.get("total_limit", 120.0)
start_time = st.session_state.get("game_start_time", now)

# 1. 뱅크 타임 계산
bank_rem = max(0.0, total_limit - (now - start_time))
bank_ratio = bank_rem / total_limit

# 2. 턴 가속 공식 (시간이 흐를수록 촉박해짐)
dynamic_limit = min(20.0, 1.0 + (0.235 * (bank_rem ** 0.85)))
turn_start = st.session_state.get("turn_start", now)
actual_turn_rem = max(0.0, dynamic_limit - (now - turn_start))
actual_turn_ratio = actual_turn_rem / dynamic_limit

st.session_state.bank_rem = bank_rem
st.session_state.actual_turn_rem = actual_turn_rem

# ────────────────────────────────────────────────
# 5. 게임 중 UI 및 입력 처리 (하이엔드 레이아웃)
# ────────────────────────────────────────────────
if st.session_state.get("initialized") and not st.session_state.get("round_over", False):
    # [A] 패배 판정
    if bank_rem <= 0 or actual_turn_rem <= 0:
        st.session_state.round_over = True
        st.session_state.ai_score += 1
        st.session_state.winner = "AI"
        st.rerun()

    # [B] 상단 스코어 보드 (네온 스타일)
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 15px;">
            <div style="text-align: left;"><span style="color:#aaa;">ROUND</span> <b style="font-size:1.2rem; color:#fff;">{st.session_state.current_round} / {st.session_state.total_rounds}</b></div>
            <div style="text-align: right;"><b style="color:#00D4FF;">USER {st.session_state.user_score}</b> <span style="color:#444;">:</span> <b style="color:#FF0055;">{st.session_state.ai_score} AI</b></div>
        </div>
    """, unsafe_allow_html=True)

    # [C] 타겟 단어 & 체인 표시 (하이라이트 박스)
    starts = get_start_chars(st.session_state.last_word[-1])
    starts_display = " · ".join(starts)
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="display: inline-block; background: linear-gradient(135deg, #FF0055, #7000FF); color: white; padding: 4px 18px; border-radius: 50px; font-weight: 800; font-size: 0.9rem; margin-bottom: 12px; box-shadow: 0 4px 15px rgba(255,0,85,0.3);">
                CHAIN {st.session_state.chain}
            </div>
            <div style="background: #ffffff; border: 2px solid #8A2BE2; border-radius: 18px; padding: 15px; box-shadow: 0 10px 25px rgba(138,43,226,0.15);">
                <div style="color: #888; font-size: 0.8rem; font-weight: bold; margin-bottom: 5px; letter-spacing: 1px;">NEXT START</div>
                <div style="color: #FF0055; font-size: 2.2rem; font-weight: 900; letter-spacing: 5px;">{starts_display}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # [D] 이중 타이머 바 (그라데이션 복구)
    t_color = "#FF0055" if actual_turn_ratio < 0.3 else "#f1e05a"
    st.markdown(f"""
        <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px;">
            <div style="margin-bottom:10px;">
                <p style="margin:0; font-size:11px; color:#3a86ff; font-weight:bold; letter-spacing:1px;">BANK TIME ({bank_rem:.1f}s)</p>
                <div class="timer-container" style="height:8px; background:#111;"><div style="width:{bank_ratio*100}%; background:linear-gradient(90deg, #3a86ff, #00d4ff); height:100%; transition: width 0.1s linear;"></div></div>
            </div>
            <div>
                <p style="margin:0; font-size:12px; color:{t_color}; font-weight:bold; letter-spacing:1px;">TURN LIMIT ({actual_turn_rem:.1f}s)</p>
                <div class="timer-container" style="height:14px; background:#111; border: 1px solid #444;"><div style="width:{actual_turn_ratio*100}%; background:{t_color}; height:100%; transition: width 0.1s linear; box-shadow: 0 0 10px {t_color}66;"></div></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # [E] 채팅창 (고급스러운 다크 글래스 모프)
    chat_html = '<div class="chat-wrap">'
    for speaker, text in st.session_state.history:
        side, bub = ("ai", "bubble-ai") if speaker == "AI" else ("user", "bubble-user")
        is_killer = "🔥" in text
        style = "border: 2px solid #FF0000; box-shadow: 0 0 10px rgba(255,0,0,0.4); font-weight: 900;" if is_killer else ""
        chat_html += f'<div class="msg-row-{side}"><div class="{bub}" style="{style}">{text.replace("🔥","")}</div></div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # [F] 입력 폼 및 AI 로직
    with st.form(key=f"game_input_{st.session_state.chain}", clear_on_submit=True):
        user_input = st.text_input("단어 입력", label_visibility="collapsed", placeholder="여기에 단어를 입력하고 Enter!")
        submit = st.form_submit_button("SEND →")
        
        if submit and user_input:
            word = user_input.strip()
            if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                # 1. 유저 성공
                st.session_state.used.add(word)
                st.session_state.history.append(("User", word))
                st.session_state.chain += 1
                st.session_state.last_word = word
                
                # 2. AI 서칭
                candidates = []
                for ch in get_start_chars(word[-1]):
                    if ch in st.session_state.index:
                        valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                        candidates.extend(valid)
                
                # 3. AI 응답 처리
                diff = st.session_state.difficulty
                give_up = 0.15 if diff == "쉬움" else 0.05 if diff == "보통" else 0
                
                if not candidates or random.random() < give_up:
                    # 유저 승리 (AI 기권)
                    st.session_state.history[-1] = ("User", f"🔥{word}")
                    st.session_state.user_score += 1
                    st.session_state.round_over = True
                    st.session_state.winner = "User"
                    st.rerun()
                else:
                    # AI 단어 선택 및 턴 종료
                    if diff == "쉬움": ai_word = random.choice(candidates)
                    elif diff == "보통": ai_word = random.choice(candidates[len(candidates)//2:] if len(candidates)>1 else candidates)
                    else: ai_word = max(candidates, key=len)
                    
                    st.session_state.used.add(ai_word)
                    st.session_state.history.append(("AI", ai_word))
                    st.session_state.last_word = ai_word
                    st.session_state.chain += 1
                    st.session_state.turn_start = time.time()
                    st.rerun()
            else:
                st.toast("❌ 유효하지 않거나 이미 사용된 단어입니다!")

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
