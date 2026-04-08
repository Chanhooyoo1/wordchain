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
        # 실제 words.js가 없다면 기본 리스트 반환
        with open("words.js", "r", encoding="utf-8") as f:
            content = f.read()
        extracted = re.findall(r'["\']([가-힣]{2,4})["\']', content)
        if extracted: return frozenset(extracted)
    except: pass
    return frozenset(["가구", "가방", "기차", "나비", "나무", "우주", "주스", "스낵", "노을", "음악"])

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
# 2. 오디오 재생 시스템 (JS Bridge)
# ────────────────────────────────────────────────
def play_sfx(file_name):
    # 효과음 재생 (중복 실행 가능)
    components.html(f"""
        <script>
            var audio = new Audio('app/static/{file_name}');
            audio.play();
        </script>
    """, height=0)

def set_bgm(file_name):
    # 배경음 교체 (부모 창의 오디오 객체 제어)
    components.html(f"""
        <script>
            var bgm = window.parent.document.getElementById('game-bgm');
            if (bgm) {{
                var newSrc = 'app/static/{file_name}';
                if (!bgm.src.includes(newSrc)) {{
                    bgm.src = newSrc;
                    bgm.play();
                }}
            }}
        </script>
    """, height=0)

# ────────────────────────────────────────────────
# 3. 페이지 설정 및 디자인
# ────────────────────────────────────────────────
st.set_page_config(page_title="Speed 끝말잇기", layout="centered")

st.markdown("""
<style>
    .grad-title {
        background: linear-gradient(90deg, #FF0000, #8A2BE2);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 800; text-align: center;
    }
    .chat-wrap { 
        background: #f8f9fa; border-radius: 15px; padding: 20px; 
        height: 300px; overflow-y: auto; border: 1px solid #e9ecef; 
        display: flex; flex-direction: column-reverse; /* 최신 메시지 아래로 */
    }
    .bubble-ai { background: white; border: 1px solid #ddd; border-radius: 15px 15px 15px 2px; padding: 8px 12px; margin: 5px 0; align-self: flex-start; }
    .bubble-user { background: linear-gradient(135deg, #FF0055, #7000FF); color: white; border-radius: 15px 15px 2px 15px; padding: 8px 12px; margin: 5px 0; align-self: flex-end; }
    .timer-bar { height: 10px; border-radius: 5px; transition: width 0.1s linear; }
</style>
""", unsafe_allow_html=True)

# 배경음 유지를 위한 Hidden Audio 태그 (최초 1회 실행)
components.html("""<audio id="game-bgm" loop><source src="" type="audio/mp3"></audio>""", height=0)

# ────────────────────────────────────────────────
# 4. 게임 로직
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    t_rounds = col1.number_input("라운드", 1, 10, 3)
    t_limit = col2.selectbox("제한시간", [180, 120, 90, 60], index=1)
    diff = col3.selectbox("난이도", ["쉬움", "보통", "어려움"], index=1)
    
    if st.button("게임 시작"):
        words_data = load_word_data()
        idx = defaultdict(list)
        for w in words_data: idx[w[0]].append(w)
        first = random.choice(list(words_data))
        
        st.session_state.update({
            "initialized": True, "difficulty": diff, "words": words_data, "index": dict(idx),
            "user_score": 0, "ai_score": 0, "current_round": 1, "total_rounds": t_rounds,
            "game_start_time": time.time(), "total_limit": float(t_limit),
            "turn_start": time.time(), "used": {first}, "last_word": first,
            "history": [("AI", first)], "round_over": False, "chain": 1, "stage": "stage1"
        })
        st.rerun()
    st.stop()

# 시간 계산
now = time.time()
bank_rem = max(0.0, st.session_state.total_limit - (now - st.session_state.game_start_time))
dynamic_limits = { "stage1": 15.0, "stage2": 11.0, "stage3": 8.0, "stage4": 5.0, "stage5": 2.0 }

# 스테이지 결정
if st.session_state.chain >= 28: cur_st = "stage5"
elif st.session_state.chain >= 20: cur_st = "stage4"
elif st.session_state.chain >= 8: cur_st = "stage3"
elif st.session_state.chain >= 5: cur_st = "stage2"
else: cur_st = "stage1"

turn_limit = dynamic_limits[cur_st]
turn_elapsed = now - st.session_state.turn_start
turn_rem = max(0.0, turn_limit - turn_elapsed)

# BGM 변경 체크
if st.session_state.stage != cur_st:
    st.session_state.stage = cur_st
    set_bgm(f"bgm{cur_st[-1]}.mp3")

# 패배 판정
if (bank_rem <= 0 or turn_rem <= 0) and not st.session_state.round_over:
    st.session_state.round_over = True
    st.session_state.ai_score += 1
    st.rerun()

# ────────────────────────────────────────────────
# 5. UI 렌더링
# ────────────────────────────────────────────────
st.write(f"**Round {st.session_state.current_round} / {st.session_state.total_rounds}**")

# 타이머 바
st.caption(f"전체 시간: {bank_rem:.1f}s")
st.progress(bank_rem / st.session_state.total_limit)
st.caption(f"차례 시간: {turn_rem:.1f}s")
st.progress(turn_rem / turn_limit)

# 채팅 출력
chat_html = '<div class="chat-wrap">'
for speaker, text in reversed(st.session_state.history):
    cls = "bubble-ai" if speaker == "AI" else "bubble-user"
    chat_html += f'<div class="{cls}">{text}</div>'
chat_html += '</div>'
st.markdown(chat_html, unsafe_allow_html=True)

# 입력창
starts = get_start_chars(st.session_state.last_word[-1])
with st.form("input_form", clear_on_submit=True):
    user_in = st.text_input(f"'{', '.join(starts)}'로 시작하는 단어:")
    if st.form_submit_button("전송") and user_in:
        word = user_in.strip()
        if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
            # 유저 성공
            play_sfx("input.mp3")
            st.session_state.used.add(word)
            st.session_state.history.append(("User", word))
            st.session_state.chain += 1
            st.session_state.last_word = word
            
            # AI 반격
            candidates = []
            for ch in get_start_chars(word[-1]):
                if ch in st.session_state.index:
                    valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                    candidates.extend(valid)
            
            if not candidates: # AI 패배
                st.session_state.user_score += 1
                st.session_state.round_over = True
            else:
                ai_word = random.choice(candidates)
                st.session_state.used.add(ai_word)
                st.session_state.history.append(("AI", ai_word))
                st.session_state.last_word = ai_word
                st.session_state.chain += 1
                st.session_state.turn_start = time.time()
            st.rerun()
        else:
            st.error("오답입니다!")

# 자동 새로고침 (0.1초 단위)
if not st.session_state.round_over:
    time.sleep(0.1)
    st.rerun()
