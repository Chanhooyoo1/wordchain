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
        extracted = re.findall(r'["\']([가-힣]{2,5})["\']', content)
        if extracted:
            return frozenset(extracted), "words.js"
    except FileNotFoundError:
        pass
    return frozenset(["가구", "가방", "가수", "기차", "나비", "나무"]), "기본 샘플"

# ────────────────────────────────────────────────
# 2. 두음법칙
# ────────────────────────────────────────────────
DUEUM = {
    '녀': '여', '뇨': '요', '뉴': '유', '니': '이', '랴': '야', '려': '여', '례': '예', '료': '요',
    '류': '유', '리': '이', '락': '낙', '래': '내', '랭': '냉', '략': '약', '량': '양', '령': '영',
    '로': '노', '뢰': '뇌', '룡': '용', '루': '누', '륙': '육', '륜': '윤', '률': '율', '릉': '능',
    '린': '인', '림': '임', '립': '입', '라': '나', '랄': '날', '람': '남', '랍': '납',
}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM:
        chars.add(DUEUM[last_char])
    return list(chars)

# ────────────────────────────────────────────────
# 3. UI
# ────────────────────────────────────────────────
st.set_page_config(page_title="QUANTUM WORD BATTLE", layout="centered")

st.markdown("""
<style>
.grad-title {
    background: linear-gradient(90deg, #FF0000, #8A2BE2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 3rem; font-weight: 800; text-align: center;
}
.chat-wrap {
    background: #f8f9fa;
    border-radius: 15px;
    padding: 20px;
    height: 350px;
    overflow-y: auto;
}
.msg-row-ai { text-align:left; margin-bottom:10px; }
.msg-row-user { text-align:right; margin-bottom:10px; }
.bubble-ai { background:white; padding:10px; border-radius:10px; }
.bubble-user { background:linear-gradient(135deg,#FF0055,#7000FF); color:white; padding:10px; border-radius:10px; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 4. 초기화
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">QUANTUM WORD BATTLE</div>', unsafe_allow_html=True)
    
    if st.button("게임 시작"):
        words, _ = load_word_data()
        
        index = defaultdict(list)
        for w in words:
            index[w[0]].append(w)
        
        first = random.choice(list(words))
        
        st.session_state.update({
            "words": words,
            "index": dict(index),
            "used": {first},
            "last_word": first,
            "history": [("AI", first)],
            "chain": 1,
            "turn_start": time.time(),
            "game_over": False,
            "initialized": True
        })
        st.rerun()
    st.stop()

# ────────────────────────────────────────────────
# 5. 게임 UI
# ────────────────────────────────────────────────
st.markdown('<div class="grad-title">QUANTUM WORD BATTLE</div>', unsafe_allow_html=True)

st.write(f"🔗 체인: {st.session_state.chain}")

starts = get_start_chars(st.session_state.last_word[-1])
st.write(f"👉 시작 글자: {', '.join(starts)}")

# 채팅 출력
chat_html = '<div class="chat-wrap">'
for speaker, text in st.session_state.history:
    if speaker == "AI":
        chat_html += f'<div class="msg-row-ai"><div class="bubble-ai">🤖 {text}</div></div>'
    else:
        chat_html += f'<div class="msg-row-user"><div class="bubble-user">{text} 👤</div></div>'
chat_html += '</div>'
st.markdown(chat_html, unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 6. 입력 + AI
# ────────────────────────────────────────────────
if not st.session_state.game_over:
    with st.form(key="fixed_form", clear_on_submit=True):
        cols = st.columns([4,1])
        user_input = cols[0].text_input("", placeholder="단어 입력")
        submit = cols[1].form_submit_button("전송")

    if submit and user_input:
        word = user_input.strip()
        possible_starts = get_start_chars(st.session_state.last_word[-1])
        
        if word in st.session_state.words and word not in st.session_state.used and word[0] in possible_starts:
            st.session_state.used.add(word)
            st.session_state.history.append(("User", word))
            st.session_state.chain += 1
            st.session_state.last_word = word
            
            # AI 턴
            candidates = []
            for ch in get_start_chars(word[-1]):
                if ch in st.session_state.index:
                    valid = [w for w in st.session_state.index[ch] if w not in st.session_state.used]
                    candidates.extend(valid)
            
            if not candidates:
                st.session_state.game_over = True
                st.success("🎉 승리!")
            else:
                ai_word = random.choice(candidates)
                st.session_state.used.add(ai_word)
                st.session_state.history.append(("AI", ai_word))
                st.session_state.last_word = ai_word
                st.session_state.chain += 1
            
            st.rerun()
        else:
            st.toast("❌ 잘못된 단어!")

# ────────────────────────────────────────────────
# 7. 자동 스크롤 + 포커스
# ────────────────────────────────────────────────
st.components.v1.html("""
<script>
const fixUI = () => {
    const win = window.parent.document;

    const chat = win.querySelector('.chat-wrap');
    const input = win.querySelector('input[type="text"]');

    if (chat) chat.scrollTop = chat.scrollHeight;
    if (input) input.focus();
};

const observer = new MutationObserver(fixUI);
observer.observe(window.parent.document.body, {
    childList: true,
    subtree: true
});

fixUI();
setInterval(fixUI, 500);
</script>
""", height=0)
