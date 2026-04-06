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
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
    
    # 설정 UI: 3개의 컬럼으로 깔끔하게 배치
    col1, col2, col3 = st.columns(3)
    with col1: 
        total_rounds = st.number_input("총 라운드 수", 1, 10, 3)
    with col2: 
        time_choice = st.selectbox("전체 제한 시간 (초)", [180, 120, 90, 60], index=1)
    with col3: 
        difficulty = st.selectbox("AI 난이도", ["쉬움", "보통", "어려움"], index=1)
    if st.button("게임 입장하기"):
        # 단어 데이터 로드
        words_data = load_word_data()
        
        idx = defaultdict(list)
        valid_words = []
        for w in words_data:
            if w and len(w) >= 2:
                idx[w[0]].append(w)
                valid_words.append(w)
        
        # 단어 데이터가 없을 경우를 대비한 방어 코드
        if not valid_words:
            valid_words = ["기차", "나무", "나비", "우주", "주스"]
            for w in valid_words: idx[w[0]].append(w)

        # 첫 단어 랜덤 선정
        first = random.choice(valid_words)
        now = time.time()
        
        # 모든 설정값 세션 상태에 저장
        st.session_state.update({
            "initialized": True, 
            "difficulty": difficulty,      # 난이도 저장 (쉬움/보통/어려움)
            "words": frozenset(valid_words), 
            "index": dict(idx),
            "user_score": 0, 
            "ai_score": 0, 
            "current_round": 1, 
            "total_rounds": total_rounds,
            "game_start_time": now,        # 파란 바(전체 시간) 기준점
            "total_limit": float(time_choice),
            "turn_limit": 15.0,
            "turn_start": now,             # 노란 바(턴 시간) 기준점
            "used": {first}, 
            "last_word": first, 
            "history": [("AI", first)],
            "round_over": False, 
            "chain": 1, 
            "winner": None
        })
        st.rerun()
    st.stop() # 게임 시작 전에는 아래 로직 실행 방지
# ────────────────────────────────────────────────
# 4. 실시간 가속 엔진 (120초 시 15초 / 10초 시 3초 버전)
# ────────────────────────────────────────────────
# --- 4. 실시간 가속 엔진 부분에 추가 ---
now = time.time()
# 전체 뱅크 시간 계산
bank_rem = max(0.0, st.session_state.total_limit - (now - st.session_state.game_start_time))
bank_ratio = bank_rem / st.session_state.total_limit

# 턴 시간 계산 (가속 공식 적용)
dynamic_limit = min(15.0, 1.5 + (0.15 * bank_rem ** 0.85))
turn_elapsed = now - st.session_state.turn_start
actual_turn_rem = max(0.0, dynamic_limit - turn_elapsed)
actual_turn_ratio = actual_turn_rem / dynamic_limit

# 세션에 현재 값 저장 (나중을 위해)
st.session_state.bank_rem = bank_rem
st.session_state.actual_turn_rem = actual_turn_rem
# ────────────────────────────────────────────────
# 5. 게임 중 UI 및 입력 처리 (이 if문은 맨 왼쪽 벽에서 4칸 들여쓰기)
# ────────────────────────────────────────────────
if not st.session_state.get("round_over", False):
    # [A] 실시간 패배 판정 (4번 섹션의 가속 엔진 변수 연동)
    if bank_rem <= 0 or actual_turn_rem <= 0:
        st.session_state.round_over = True
        st.session_state.ai_score += 1
        st.session_state.winner = "AI"
        st.rerun()

    # [B] 상단 스코어 보드
    st.write(f"**라운드 {st.session_state.current_round} / {st.session_state.total_rounds}**")
    c1, c2 = st.columns(2)
    c1.metric("나 (User)", st.session_state.user_score)
    c2.metric("상대 (AI)", st.session_state.ai_score)

    # [C] 체인 및 다음 글자 상자 UI
    # last_word는 초기화 시 또는 AI 응답 시 세션에 저장됨
    starts = get_start_chars(st.session_state.last_word[-1])
    starts_display = " 또는 ".join(starts)
    st.markdown(f"""
        <div style="text-align: center; margin-top: 10px; margin-bottom: 15px;">
            <div style="display: inline-block; background: linear-gradient(135deg, #FF0055, #7000FF); color: white; padding: 4px 15px; border-radius: 20px; font-weight: bold; font-size: 1.1rem; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); border: 1px solid #fff;">
                이은 단어 수: {st.session_state.chain}
            </div>
            <div style="background: #ffffff; border: 2px solid #8A2BE2; border-radius: 12px; padding: 12px; box-shadow: inset 0 0 10px rgba(138,43,226,0.1);">
                <div style="color: #666; font-size: 0.85rem; margin-bottom: 3px;">다음 시작 글자</div>
                <div style="color: #FF0055; font-size: 1.5rem; font-weight: 900; letter-spacing: 2px;">{starts_display}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # [D] 실시간 이중 타이머 바 (4번 섹션 변수 연동)
    t_color = "#FF0055" if actual_turn_ratio < 0.3 else "#f1e05a"
    
    st.markdown(f"""
        <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 10px; border: 1px solid #444; margin-bottom: 10px;">
            <div style="margin-bottom:8px;">
                <p style="margin:0; font-size:11px; color:#3a86ff; font-weight:bold;">총 시간 ({bank_rem:.1f}s)</p>
                <div class="bank-container">
                    <div style="width:{bank_ratio*100}%; background:#3a86ff; height:100%; transition: width 0.1s linear;"></div>
                </div>
            </div>
            <div>
                <p style="margin:0; font-size:12px; color:{t_color}; font-weight:bold;">차례 제한시간 ({actual_turn_rem:.1f}s)</p>
                <div class="timer-container">
                    <div style="width:{actual_turn_ratio*100}%; background:{t_color}; height:100%; transition: width 0.1s linear;"></div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # [E] 채팅창 출력 (역순 출력 - 최신 메시지가 위로)
    chat_html = '<div class="chat-wrap">'
    # history는 [(스피커, 텍스트), ...] 구조
    for speaker, text in st.session_state.history:
        # 🔥 한방단어는 빨간색 굵게 표시
        style = "color: #FF0000; font-weight: bold; border: 2px solid #FF0000;" if "🔥" in text else ""
        chat_html += f'<div class="msg-row-{side}"><div class="{bub}" style="{style}">{text.replace("🔥","")}</div></div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # [F] 단어 입력 폼 및 AI 대응 로직
    # clear_on_submit=True로 전송 후 입력창 비움
    with st.form(key="game_input", clear_on_submit=True):
        user_input = st.text_input("단어 입력", label_visibility="collapsed", placeholder="단어를 입력해주세요...")
        submit = st.form_submit_button("전송")
        
        if submit and user_input:
            word = user_input.strip()
            # 단어 유효성 검사 (사전에 존재, 미사용, 시작 글자 일치)
            if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                
                # --- 1. 유저 정답 처리 ---
                st.session_state.used.add(word)
                st.session_state.history.append(("User", word))
                st.session_state.chain += 1
                st.session_state.last_word = word
                
                # --- 2. AI 대응 단어 서칭 ---
                candidates = []
                for ch in get_start_chars(word[-1]):
                    if ch in st.session_state.index:
                        # 아직 안 쓴 단어만 필터링
                        valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                        candidates.extend(valid)

                # --- 3. AI 결과 판정 및 등록 ---
                diff = st.session_state.get("difficulty", "보통")
                
                # 난이도별 기권 확률 (쉬움 15%, 보통 5%)
                give_up_chance = 0.15 if diff == "쉬움" else 0.05 if diff == "보통" else 0
                if candidates and random.random() < give_up_chance:
                    candidates = [] # 단어가 있어도 기권

                if not candidates:
                    # [유저 승리] AI가 단어를 못 찾음
                    st.session_state.history[-1] = ("User", f"🔥{word}")
                    st.session_state.user_score += 1
                    
                    if st.session_state.current_round >= st.session_state.total_rounds:
                        # 최종 승리
                        st.session_state.round_over = True
                        st.session_state.winner = "User"
                    else:
                        # 다음 라운드 이동 (타이머 리셋)
                        st.toast("🎊 AI 항복! 다음 라운드로 이동합니다.")
                        time.sleep(1.5)
                        new_f = random.choice(list(st.session_state.words))
                        now_res = time.time()
                        st.session_state.update({
                            "current_round": st.session_state.current_round + 1,
                            "game_start_time": now_res, # 전체 시간 리셋
                            "turn_start": now_res,      # 턴 시간 리셋
                            "used": {new_f}, "last_word": new_f,
                            "history": [("AI", new_f)], "chain": 1
                        })
                    st.rerun()
                
                else:
                    # [AI 응답] 단어 선택 및 등록
                    # 가속 턴 시간(dynamic_limit)의 40% 이내에서 고민 시간 설정
                    delay = random.uniform(0.5, max(0.6, dynamic_limit * 0.4))
                    with st.spinner("AI가 생각 중..."):
                        time.sleep(delay)
                    
                    # 난이도별 단어 선택 로직
                    if diff == "쉬움": ai_word = random.choice(candidates)
                    elif diff == "보통":
                        candidates.sort(key=len) # 길이순 정렬
                        # 중간 길이 이상의 단어 중 랜덤
                        idx_m = len(candidates)//2
                        ai_word = random.choice(candidates[idx_m:] if idx_m > 0 else candidates)
                    else: # 어려움: 가장 긴 단어
                        ai_word = max(candidates, key=len)

                    # AI 한방단어 체크 (유저가 이을 단어가 없는지 확인)
                    is_ai_killer = True
                    for next_ch in get_start_chars(ai_word[-1]):
                        if next_ch in st.session_state.index:
                            if any(w not in st.session_state.used and w != ai_word for w in st.session_state.index[next_ch]):
                                is_ai_killer = False
                                break
                    
                    final_msg = f"🔥{ai_word}" if is_ai_killer else ai_word
                    
                    # 세션 업데이트
                    st.session_state.used.add(ai_word)
                    st.session_state.history.append(("AI", final_msg))
                    st.session_state.last_word = ai_word
                    st.session_state.chain += 1
                    st.session_state.turn_start = time.time() # 유저 턴 시작 시간 리셋
                    st.rerun() # 화면 갱신
            
            else:
                # 유효하지 않은 단어
                st.toast("❌ 잘못되거나 이미 사용된 단어입니다!")

# ────────────────────────────────────────────────
# 6. 라운드 종료 화면 (307라인 SyntaxError 해결 지점)
# (이 else는 위의 'if not st.session_state.get(...)'와 수직 줄이 같아야 함)
# ────────────────────────────────────────────────
else:
    # 패배 변수 안전장치 (get 사용)
    b_rem = st.session_state.get("bank_rem", 0)
    t_rem = st.session_state.get("actual_turn_rem", 0)
    
    # 패배 원인 분석
    reason = "시간 초과!" if (b_rem <= 0 or t_rem <= 0) else "AI의 역습!"
    st.error(f"💀 패배.. {reason}")
    
    # [스코어 보드]
    c1, c2 = st.columns(2)
    c1.metric("최종 나 (User)", st.session_state.user_score)
    c2.metric("최종 상대 (AI)", st.session_state.ai_score)

    if st.session_state.current_round < st.session_state.total_rounds:
        # 다음 라운드 진행 버튼
        if st.button(f"🕐 다음 라운드({st.session_state.current_round + 1}) 시작하기"):
            new_first = random.choice(list(st.session_state.words))
            now_reset = time.time()
            st.session_state.update({
                "round_over": False, "winner": None,
                "game_start_time": now_reset, "turn_start": now_reset,      
                "used": {new_first}, "last_word": new_first,
                "history": [("AI", new_first)], "chain": 1,
                "current_round": st.session_state.current_round + 1
            })
            st.rerun()
    else:
        # 모든 게임 종료
        st.warning("🎮 모든 라운드가 종료되었습니다!")
        # 초기화 버튼
        if st.button("🔄 게임 초기화 및 처음부터 다시 시작", key="final_restart"):
            # 세션 모든 키 삭제
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
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
