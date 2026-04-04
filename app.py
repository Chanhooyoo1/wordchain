import random
import time
import re
import streamlit as st
from collections import defaultdict

# ────────────────────────────────────────────────
# 1. 설정 및 JS 데이터 로드 함수
# ────────────────────────────────────────────────

def get_time_limit(chain: int) -> int:
    if chain < 10: return 15
    elif chain < 20: return 10
    elif chain < 30: return 7
    else: return 5

DUEUM = {
    '녀': '여', '뇨': '요', '뉴': '유', '니': '이',
    '랴': '야', '려': '여', '례': '예', '료': '요',
    '류': '유', '리': '이', '락': '낙', '래': '내',
    '랭': '냉', '략': '약', '량': '양', '령': '영',
    '로': '노', '뢰': '뇌', '룡': '용', '루': '누',
    '륙': '육', '륜': '윤', '률': '율', '릉': '능',
    '린': '인', '림': '임', '립': '입', '라': '나',
    '랄': '날', '람': '남', '랍': '납',
}

@st.cache_data(show_spinner=False)
def load_words_from_js(file_path="allNouns.js"):
    """JS 파일 내부의 따옴표 안 단어들을 정규식으로 추출합니다."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # JS 배열 내의 "단어" 또는 '단어' 추출 (2~4글자 한글)
        found_words = re.findall(r'["\']([가-힣]{2,4})["\']', content)
        
        words_frozen = frozenset(found_words)
        index = defaultdict(list)
        for word in words_frozen:
            index[word[0]].append(word)
            
        return words_frozen, dict(index), len(words_frozen)
    except FileNotFoundError:
        return None, None, 0

# ────────────────────────────────────────────────
# 2. 게임 로직
# ────────────────────────────────────────────────

def get_start_chars(last_char: str) -> list:
    chars = {last_char}
    if last_char in DUEUM:
        chars.add(DUEUM[last_char])
    for k, v in DUEUM.items():
        if v == last_char:
            chars.add(k)
    return list(chars)

def ai_pick(last_word, used, index):
    valid_starts = get_start_chars(last_word[-1])
    candidates = []
    for ch in valid_starts:
        if ch in index:
            candidates.extend([w for w in index[ch] if w not in used])
    if not candidates:
        return None
    return random.choice(candidates)

# ────────────────────────────────────────────────
# 3. UI 및 상태 초기화
# ────────────────────────────────────────────────

st.set_page_config(page_title="🎯 끝말잇기 PRO", layout="centered")

# CSS 스타일 (난이도 뱃지 및 타이머 디자인)
st.markdown("""
<style>
    .chat-wrap { background: #f8f9fa; border-radius: 15px; padding: 20px; height: 380px; overflow-y: auto; border: 1px solid #e9ecef; margin-bottom: 20px; }
    .bubble-ai { background: white; padding: 10px 15px; border-radius: 15px 15px 15px 5px; border: 1px solid #dee2e6; font-weight: 600; }
    .bubble-user { background: linear-gradient(135deg, #6e8efb, #a777e3); color: white; padding: 10px 15px; border-radius: 15px 15px 5px 15px; font-weight: 600; }
    .timer-bar-bg { background: #e9ecef; border-radius: 10px; height: 12px; overflow: hidden; margin: 10px 0; }
    .timer-bar-fill { height: 100%; transition: width 0.5s linear; }
    .stage-badge { padding: 4px 12px; border-radius: 20px; color: white; font-size: 0.85rem; font-weight: bold; margin-left: 10px; }
</style>
""", unsafe_allow_html=True)

if "initialized" not in st.session_state:
    # 파일명을 본인이 가진 js 파일명(예: allNouns.js)으로 맞춰주세요
    words, index, count = load_words_from_js("allNouns.js") 
    if words is None or count == 0:
        st.error("❌ JS 단어장 파일을 찾을 수 없거나 단어가 없습니다. (파일명 확인: allNouns.js)")
        st.stop()
    
    first_word = random.choice(list(words))
    st.session_state.update({
        "words": words, "index": index, "used": {first_word},
        "last_word": first_word, "history": [("AI", first_word)],
        "game_over": False, "chain": 1, "turn_start": time.time(),
        "input_key": 0, "initialized": True
    })

# ────────────────────────────────────────────────
# 4. 게임 화면
# ────────────────────────────────────────────────

st.title("🎯 끝말잇기 PRO (JS Data)")

# 난이도 및 색상 로직
chain = st.session_state.chain
if chain < 10: stage_label, stage_color = "🟢 일반", "#4caf50"
elif chain < 20: stage_label, stage_color = "🟡 빠름", "#ff9800"
elif chain < 30: stage_label, stage_color = "🟠 매우 빠름", "#ff5722"
else: stage_label, stage_color = "🔴 극한", "#f44336"

time_limit = get_time_limit(chain)

# 대시보드 및 타이머
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown(f"**체인:** {chain} | **제한시간:** {time_limit}s")
with c2:
    st.markdown(f'<div style="text-align:right;"><span class="stage-badge" style="background:{stage_color};">{stage_label}</span></div>', unsafe_allow_html=True)

if not st.session_state.game_over:
    elapsed = time.time() - st.session_state.turn_start
    remaining = max(0.0, time_limit - elapsed)
    ratio = remaining / time_limit
    if remaining <= 0:
        st.session_state.game_over = True
        st.rerun()
    st.markdown(f'<div class="timer-bar-bg"><div class="timer-bar-fill" style="width:{ratio*100}%; background:{stage_color};"></div></div>', unsafe_allow_html=True)

# 채팅 로그
chat_html = '<div class="chat-wrap">'
for who, word in st.session_state.history:
    side = "ai" if who == "AI" else "user"
    icon = "🤖" if who == "AI" else "👤"
    justify = "flex-start" if who == "AI" else "flex-end"
    chat_html += f'<div style="display:flex; justify-content:{justify}; margin-bottom:10px; align-items:center; gap:10px;">'
    chat_html += f'{icon if who=="AI" else ""} <div class="bubble-{side}">{word}</div> {icon if who=="👤" else ""}'
    chat_html += '</div>'
chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)

# 입력 폼
if not st.session_state.game_over:
    last = st.session_state.last_word
    starts = get_start_chars(last[-1])
    st.info(f"💡 **'{last}'** 다음 → **'{' 또는 '.join(starts)}'**")

    with st.form(key=f"input_{st.session_state.input_key}", clear_on_submit=True):
        user_input = st.text_input("단어 입력", label_visibility="collapsed")
        if st.form_submit_button("전송", use_container_width=True):
            word = user_input.strip()
            if len(word) >= 2 and word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                st.session_state.used.add(word)
                st.session_state.last_word = word
                st.session_state.history.append(("나", word))
                st.session_state.chain += 1
                
                ai_word = ai_pick(word, st.session_state.used, st.session_state.index)
                if ai_word:
                    st.session_state.used.add(ai_word)
                    st.session_state.last_word = ai_word
                    st.session_state.history.append(("AI", ai_word))
                    st.session_state.chain += 1
                    st.session_state.turn_start = time.time()
                    st.session_state.input_key += 1
                else:
                    st.session_state.game_over = True
                st.rerun()
            else:
                st.warning("유효하지 않은 단어입니다.")
    time.sleep(0.1)
    st.rerun()
else:
    st.error("🎮 GAME OVER")
    if st.button("다시 시작"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
