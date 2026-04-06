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
# 3. 게임 초기화 (입장 전 화면)
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끄투 온라인 Lite</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1: 
        total_rounds = st.number_input("총 라운드 수", 1, 10, 3)
    with col2: 
        # 전체 판의 운명을 결정하는 시간 (파란 바의 총 길이)
        time_choice = st.selectbox("전체 제한 시간 (초)", [180, 120, 90, 60], index=1)
    
    if st.button("게임 입장하기"):
        words_data = load_word_data()
        
        idx = defaultdict(list)
        valid_words = []
        for w in words_data:
            if w and len(w) >= 2:
                idx[w[0]].append(w)
                valid_words.append(w)
        
        # 첫 단어 랜덤 선정
        first = random.choice(valid_words)
        now = time.time()
        
        st.session_state.update({
            "initialized": True, 
            "words": frozenset(valid_words), 
            "index": dict(idx),
            "user_score": 0, 
            "ai_score": 0, 
            "current_round": 1, 
            "total_rounds": total_rounds,
            "game_start_time": now,        # 파란 바 기준점
            "total_limit": float(time_choice), 
            "turn_start": now,             # 노란 바 기준점
            "used": {first}, 
            "last_word": first, 
            "history": [("AI", first)],
            "round_over": False, 
            "chain": 1, 
            "winner": None
        })
        st.rerun()
    st.stop() # 게임 시작 전에는 여기서 멈춤

# ────────────────────────────────────────────────
# 4. 실시간 가속 엔진 (중요: 에러 방지를 위해 if문 밖에서 계산)
# ────────────────────────────────────────────────
now = time.time()
# (1) 전체 게임 시간 계산 (파란 바)
total_elapsed = now - st.session_state.game_start_time
bank_rem = max(0.0, st.session_state.total_limit - total_elapsed)
bank_ratio = bank_rem / st.session_state.total_limit

# (2) 가속 로직: 전체 시간이 줄수록 턴당 부여 시간이 10초 -> 1.5초로 줄어듦
dynamic_limit = 1.5 + (8.5 * bank_ratio) 

# (3) 현재 턴 시간 계산 (노란 바)
turn_elapsed = now - st.session_state.turn_start
turn_rem = max(0.0, dynamic_limit - turn_elapsed)
turn_ratio = turn_rem / dynamic_limit

# ────────────────────────────────────────────────
# 5. 게임 중 UI 및 입력 처리
# ────────────────────────────────────────────────
if not st.session_state.get("round_over", False):
    # [시간 초과 체크]
    if bank_rem <= 0 or turn_rem <= 0:
        st.session_state.round_over = True
        st.session_state.ai_score += 1
        st.session_state.winner = "AI"
        st.rerun()

    # 상단 스코어 보드
    st.write(f"**Round {st.session_state.current_round} / {st.session_state.total_rounds}**")
    c1, c2 = st.columns(2)
    c1.metric("나 (User)", st.session_state.user_score)
    c2.metric("상대 (AI)", st.session_state.ai_score)

    # 체인 및 다음 글자 상자
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

    # 실시간 이중 타이머 바
    t_color = "#FF0055" if turn_ratio < 0.3 else "#f1e05a"
    st.markdown(f"""
        <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 10px; border: 1px solid #444;">
            <div style="margin-bottom:8px;">
                <p style="margin:0; font-size:11px; color:#3a86ff; font-weight:bold;">TOTAL TIME ({bank_rem:.1f}s)</p>
                <div class="bank-container"><div style="width:{bank_ratio*100}%; background:#3a86ff; height:100%; transition: width 0.1s linear;"></div></div>
            </div>
            <div>
                <p style="margin:0; font-size:12px; color:{t_color}; font-weight:bold;">TURN LIMIT ({turn_rem:.1f}s)</p>
                <div class="timer-container"><div style="width:{turn_ratio*100}%; background:{t_color}; height:100%; transition: width 0.1s linear;"></div></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 채팅창
    chat_html = '<div class="chat-wrap">'
    for speaker, text in st.session_state.history:
        side = "ai" if speaker == "AI" else "user"
        bub = "bubble-ai" if speaker == "AI" else "bubble-user"
        chat_html += f'<div class="msg-row-{side}"><div class="{bub}">{text}</div></div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # 단어 입력 폼
    with st.form(key="game_input", clear_on_submit=True):
        user_input = st.text_input("단어 입력", label_visibility="collapsed")
        if st.form_submit_button("전송") and user_input:
            word = user_input.strip()
            if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                st.session_state.used.add(word)
                st.session_state.history.append(("User", word))
                st.session_state.chain += 1
                
                # AI 서칭
                candidates = []
                for ch in get_start_chars(word[-1]):
                    if ch in st.session_state.index:
                        valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                        candidates.extend(valid)
                
                if not candidates:
                    st.success("🎊 AI가 단어를 찾지 못했습니다!")
                    time.sleep(1.5)
                    if st.session_state.current_round < st.session_state.total_rounds:
                        new_first = random.choice(list(st.session_state.words))
                        st.session_state.update({
                            "current_round": st.session_state.current_round + 1,
                            "user_score": st.session_state.user_score + 1,
                            "used": {new_first}, "last_word": new_first,
                            "history": [("AI", new_first)], "turn_start": time.time(), "chain": 1
                        })
                    else:
                        st.session_state.round_over = True
                        st.session_state.winner = "User"
                        st.session_state.user_score += 1
                    st.rerun()
                else:
                    ai_word = random.choice(candidates)
                    st.session_state.used.add(ai_word)
                    st.session_state.history.append(("AI", ai_word))
                    st.session_state.last_word = ai_word
                    st.session_state.chain += 1
                    st.session_state.turn_start = time.time() # 턴 시간만 리셋
                    st.rerun()
            else:
                st.toast("❌ 잘못된 단어입니다!")

# ────────────────────────────────────────────────
# 6. 라운드 종료 화면 (에러 완벽 방지 구역)
# ────────────────────────────────────────────────
else:
    # 1. 패배 메시지 표시
    st.error(f"💀 패배! {'시간 초과' if (bank_rem <= 0 or turn_rem <= 0) else 'AI의 역습'}")
    
    # 다음 라운드가 남아있는 경우
    if st.session_state.current_round < st.session_state.total_rounds:
        st.info(f"⏳ 3초 후 {st.session_state.current_round + 1}라운드가 자동으로 시작됩니다...")
        
        # [수정] 버튼 없이 자동으로 데이터 업데이트
        new_first = random.choice(list(st.session_state.words))
        st.session_state.update({
            "round_over": False, 
            "winner": None,
            "used": {new_first}, 
            "last_word": new_first,
            "history": [("AI", new_first)], 
            "turn_start": time.time(), 
            "chain": 1,
            "current_round": st.session_state.current_round + 1 # 라운드 번호 증가
        })
        
        time.sleep(3) # 사용자가 패배 원인을 볼 시간 확보
        st.rerun()    # 🚀 첫 번째 리런 (자동 실행)

    # 모든 라운드가 끝난 경우
    else:
        st.warning("🏁 모든 라운드가 종료되었습니다!")
        if st.button("🔄 처음부터 다시 시작하기", key="restart_btn"):
            for k in list(st.session_state.keys()): 
                del st.session_state[k]
            st.rerun() # 🚀 두 번째 리런 (버튼 클릭 시 실행)

# ────────────────────────────────────────────────
# 7. 실시간 무한 새로고침 (0.1초 단위)
# ────────────────────────────────────────────────
if not st.session_state.get("round_over", False):
    time.sleep(0.1)
    components.html("""
<script>
    const fixUI = () => {
        const win = window.parent.document;
        const chat = win.querySelector('.chat-wrap');
        const input = win.querySelector('input');

        // 1. 채팅창이 있으면 항상 맨 아래로 스크롤
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }

        // 2. 입력창이 있고, 현재 포커스가 다른 버튼 등에 가있지 않다면 강제 포커스
        // (사용자가 직접 다른 곳을 클릭한 게 아니라면 무조건 입력창으로 커서 복귀)
        if (input && win.activeElement.tagName !== 'INPUT' && win.activeElement.tagName !== 'TEXTAREA') {
            input.focus();
        }
    };

    // 화면 변화를 감지하여 실행 (MutationObserver)
    const observer = new MutationObserver(fixUI);
    observer.observe(window.parent.document.body, {
        childList: true,
        subtree: true
    });

    // 0.4초마다 반복적으로 보정 (강력한 포커스 유지)
    setInterval(fixUI, 400);
    
    // 즉시 실행
    fixUI();
</script>
""", height=0)
    st.rerun()
