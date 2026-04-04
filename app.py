import random
import time
import re
import json
import streamlit as st
from collections import defaultdict

# ────────────────────────────────────────────────
# 1. 설정 및 데이터 로드 함수
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
def load_words_from_json(file_path="words.json", max_len=4):
    """로컬 JSON 파일을 읽어 단어 셋과 인덱스를 생성합니다."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_words = json.load(f)
        
        # 2~max_len 글자 사이의 한글 단어만 필터링 및 공백 제거
        filtered_words = [
            w.strip() for w in raw_words 
            if re.match(r'^[가-힣]{2,' + str(max_len) + r'}$', w.strip())
        ]
        
        words_frozen = frozenset(filtered_words)
        
        # 첫 글자 기준 인덱싱
        index = defaultdict(list)
        for word in words_frozen:
            index[word[0]].append(word)
            
        return words_frozen, dict(index), f"로컬 파일 ({file_path})"
    except FileNotFoundError:
        return None, None, "파일 없음"
    except Exception as e:
        return None, None, f"오류 발생: {e}"

# ────────────────────────────────────────────────
# 2. 게임 로직 함수
# ────────────────────────────────────────────────

def get_start_chars(last_char: str) -> list:
    chars = {last_char}
    if last_char in DUEUM:
        chars.add(DUEUM[last_char])
    for k, v in DUEUM.items():
        if v == last_char:
            chars.add(k)
    return list(chars)

def is_valid_word(word, last_word, used, word_set):
    if len(word) < 2:
        return False, "두 글자 이상의 단어를 입력하세요."
    if word not in word_set:
        return False, f"'{word}'는 단어 목록에 없는 단어예요."
    if word in used:
        return False, f"'{word}'는 이미 사용한 단어예요."
    valid_starts = get_start_chars(last_word[-1])
    if word[0] not in valid_starts:
        return False, f"'{last_word[-1]}'(으)로 이어지는 단어가 아니에요."
    return True, ""

def ai_pick(last_word, used, index):
    valid_starts = get_start_chars(last_word[-1])
    candidates = []
    for ch in valid_starts:
        if ch in index:
            candidates.extend([w for w in index[ch] if w not in used])
    if not candidates:
        return None
    
    # 상대방이 대답할 수 없는 단어(한방 단어 등)를 우선 탐색
    dead_ends = [
        w for w in candidates
        if not any(
            ch in index and any(x not in used and x != w for x in index[ch])
            for ch in get_start_chars(w[-1])
        )
    ]
    return random.choice(dead_ends if dead_ends else candidates)

# ────────────────────────────────────────────────
# 3. 세션 상태 및 UI 초기화
# ────────────────────────────────────────────────

def reset_game():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def init_state():
    if "initialized" not in st.session_state:
        words, index, source = load_words_from_json()
        
        if words is None:
            st.error(f"❌ 단어장을 불러올 수 없습니다. ({source})")
            st.info("같은 폴더에 'words.json' 파일이 있는지 확인해주세요.")
            st.stop()

        first_word = random.choice(list(words))
        st.session_state.words = words
        st.session_state.word_source = source
        st.session_state.index = index
        st.session_state.used = {first_word}
        st.session_state.last_word = first_word
        st.session_state.history = [("AI", first_word)]
        st.session_state.game_over = False
        st.session_state.result_msg = ""
        st.session_state.winner = None
        st.session_state.initialized = True
        st.session_state.input_key = 0
        st.session_state.chain = 1
        st.session_state.turn_start = time.time()

# ────────────────────────────────────────────────
# 4. 메인 UI 및 게임 루프
# ────────────────────────────────────────────────

st.set_page_config(page_title="🎯 끝말잇기 PRO", layout="centered")

# 스타일 적용
st.markdown("""
<style>
    .chat-wrap { background: #f5f7fa; border-radius: 16px; padding: 16px; height: 350px; overflow-y: auto; margin-bottom: 16px; border: 1px solid #e4e7ed; }
    .msg-row-ai { display:flex; justify-content:flex-start; margin:8px 0; align-items:flex-end; gap:8px; }
    .msg-row-user { display:flex; justify-content:flex-end; margin:8px 0; align-items:flex-end; gap:8px; }
    .bubble-ai { background: #fff; border: 1px solid #dde1ea; border-radius: 18px 18px 18px 4px; padding: 10px 16px; font-weight: 600; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
    .bubble-user { background: linear-gradient(135deg, #4f8ef7, #6c63ff); color: #fff; border-radius: 18px 18px 4px 18px; padding: 10px 16px; font-weight: 600; }
    .timer-bar-bg { background: #e4e7ed; border-radius: 10px; height: 10px; overflow: hidden; margin-top: 5px; }
    .timer-bar-fill { height: 100%; transition: width 0.5s linear; }
</style>
""", unsafe_allow_html=True)

init_state()

st.title("🎯 끝말잇기 PRO")
st.caption(f"📚 {st.session_state.word_source} | 현재 단어수: {len(st.session_state.words):,}개")

# 대시보드
chain = st.session_state.chain
time_limit = get_time_limit(chain)
c1, c2, c3 = st.columns(3)
c1.metric("체인 🔗", f"{chain}개")
c2.metric("제한 시간 ⏱", f"{time_limit}초")
c3.metric("누적 단어", f"{len(st.session_state.used)}개")

# 타이머 로직
if not st.session_state.game_over:
    elapsed = time.time() - st.session_state.turn_start
    remaining = max(0.0, time_limit - elapsed)
    ratio = remaining / time_limit
    
    if remaining <= 0:
        st.session_state.game_over = True
        st.session_state.winner = "ai"
        st.session_state.result_msg = f"⏰ 시간 초과! (제한 {time_limit}초) AI 승리!"
        st.rerun()

    bar_color = "#4caf50" if ratio > 0.5 else "#ff9800" if ratio > 0.25 else "#f44336"
    st.markdown(f"⏱ **남은 시간: {remaining:.1f}초**")
    st.markdown(f'<div class="timer-bar-bg"><div class="timer-bar-fill" style="width:{ratio*100}%;background:{bar_color};"></div></div>', unsafe_allow_html=True)

# 채팅 로그 표시
chat_html = '<div class="chat-wrap">'
for who, word in st.session_state.history:
    if who == "AI":
        chat_html += f'<div class="msg-row-ai">🤖<div class="bubble-ai">{word}</div></div>'
    else:
        chat_html += f'<div class="msg-row-user"><div class="bubble-user">{word}</div>👤</div>'
chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)

# 게임 결과 또는 입력 폼
if st.session_state.game_over:
    if st.session_state.winner == "user": st.success(st.session_state.result_msg)
    else: st.error(st.session_state.result_msg)
    if st.button("🔄 다시 시작", use_container_width=True):
        reset_game()
else:
    last = st.session_state.last_word
    starts = get_start_chars(last[-1])
    st.info(f"💡 **'{last}'** 다음 → **'{' 또는 '.join(starts)}'** (으)로 시작하세요.")

    with st.form(key=f"input_{st.session_state.input_key}", clear_on_submit=True):
        user_input = st.text_input("단어 입력", label_visibility="collapsed", placeholder="여기에 단어를 입력하세요")
        submitted = st.form_submit_button("전송", use_container_width=True)

    if submitted and user_input:
        word = user_input.strip()
        valid, err = is_valid_word(word, st.session_state.last_word, st.session_state.used, st.session_state.words)
        
        if not valid:
            st.warning(f"❌ {err}")
        else:
            # 유저 턴 처리
            st.session_state.used.add(word)
            st.session_state.last_word = word
            st.session_state.history.append(("나", word))
            st.session_state.chain += 1
            st.session_state.input_key += 1
            
            # AI 턴 처리
            ai_word = ai_pick(word, st.session_state.used, st.session_state.index)
            if ai_word is None:
                st.session_state.game_over = True
                st.session_state.winner = "user"
                st.session_state.result_msg = f"🎉 AI가 단어를 찾지 못했습니다! 당신의 승리!"
            else:
                st.session_state.used.add(ai_word)
                st.session_state.last_word = ai_word
                st.session_state.history.append(("AI", ai_word))
                st.session_state.chain += 1
                st.session_state.turn_start = time.time()
            st.rerun()

    # 타이머 갱신용 리프레시
    time.sleep(0.5)
    st.rerun()