"""
끝말잇기 게임 - Streamlit 버전 (단어 자동 다운로드)
====================================================
실행 방법:
  pip install streamlit requests
  streamlit run 끝말잇기.py

단어 목록을 GitHub에서 자동으로 가져옵니다.
실패 시 내장 샘플 단어로 대체됩니다.
"""

import random
import time
import re
import streamlit as st
from collections import defaultdict

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ────────────────────────────────────────────────
# 타이머 설정
# ────────────────────────────────────────────────
def get_time_limit(chain: int) -> int:
    if chain < 10:
        return 15
    elif chain < 20:
        return 10
    elif chain < 30:
        return 7
    else:
        return 5

# ────────────────────────────────────────────────
# 두음법칙 매핑
# ────────────────────────────────────────────────
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

# ────────────────────────────────────────────────
# 내장 샘플 단어 (다운로드 실패 시 사용)
# ────────────────────────────────────────────────
SAMPLE_WORDS = [
    "가구", "가방", "가수", "가을", "가족", "가지", "각도", "간식", "간장",
    "갈비", "갈치", "감기", "감동", "감사", "감자", "강물", "강아지", "강의",
    "개구리", "개나리", "개미", "거리", "거북", "거울", "건강", "건물", "겨울",
    "결과", "결혼", "경기", "경제", "경찰", "계단", "계절", "고래", "고민",
    "고양이", "고추", "공원", "공장", "과자", "관계", "교육", "구름", "국가",
    "국민", "그림", "기계", "기념", "기억", "기차", "기회", "길이",
    "나라", "나무", "나비", "낙엽", "남자", "내년", "냉면", "냉장고",
    "노래", "노력", "노인", "논리", "농사", "누나", "눈물", "능력",
    "다리", "다음", "단계", "단풍", "달걀", "달력", "담배", "대학", "대화",
    "도로", "도서관", "도시", "독서", "동물", "동생", "두부", "드라마",
    "라디오", "라면", "레몬", "로봇", "리더", "리듬",
    "마음", "마지막", "막대", "만남", "만족", "말씀", "매력", "면접", "명예",
    "모임", "목표", "무기", "문명", "문제", "문화", "물질", "미래", "미소",
    "바다", "바람", "바위", "박사", "반대", "발전", "방법", "배경", "배움",
    "번영", "변화", "보람", "복지", "부담", "분야", "비교", "비용",
    "사고", "사랑", "사실", "사업", "사회", "상상", "생각", "생산", "선택",
    "설명", "성공", "성장", "세계", "소나무", "소통", "속도", "수준", "시간",
    "시작", "시장", "신뢰", "실력", "실천",
    "아이", "안전", "약속", "양심", "어머니", "역할", "연구", "열정", "예의",
    "오리", "완성", "용기", "우산", "운명", "원칙", "위기", "의미", "이해",
    "인간", "인내", "인식", "일상",
    "자격", "자연", "자전거", "장미", "재능", "전략", "전통", "절약", "정의",
    "조화", "존중", "주목", "중심", "지식", "진리", "진심",
    "창의", "창조", "책임", "철학", "체계", "최선", "추진", "출발",
    "탁월", "태도", "통합", "특징", "판단", "평등", "평화", "표현", "풍요",
    "학문", "학습", "한계", "해결", "행동", "행복", "협력", "화합", "환경",
    "활동", "효율", "희망",
    "가로수", "나침반", "낙하산", "다람쥐", "달팽이", "도토리", "동그라미",
    "마라톤", "망원경", "메아리", "바나나", "반딧불", "병아리", "보물섬",
    "소나기", "어린이", "오솔길", "올챙이", "자동차", "장난감", "지렁이",
    "청개구리", "코끼리", "크레파스", "파인애플", "해바라기", "호랑이",
]

# ────────────────────────────────────────────────
# GitHub에서 단어 목록 다운로드
# ────────────────────────────────────────────────

# 시도할 raw URL 목록 (ALL_NOUNS JS 파일 → 단어 파싱)
GITHUB_URLS = [
    # han-dle 저장소 직접 접근 시도
    "https://raw.githubusercontent.com/han-dle/pd-korean-noun-list-for-wordles/main/src/allNouns.js",
    "https://raw.githubusercontent.com/han-dle/pd-korean-noun-list-for-wordles/main/src/index.js",
    "https://raw.githubusercontent.com/han-dle/pd-korean-noun-list-for-wordles/main/src/all_nouns.js",
    # korean-word-game DB (원본 소스)
    "https://raw.githubusercontent.com/korean-word-game/db/master/nouns.txt",
    "https://raw.githubusercontent.com/korean-word-game/db/master/data/nouns.txt",
    "https://raw.githubusercontent.com/korean-word-game/db/master/words.txt",
]

@st.cache_data(show_spinner=False)
def fetch_words_from_github(max_len: int = 4) -> tuple:
    """GitHub에서 단어 목록 다운로드. (단어셋, 출처) 반환"""
    if not HAS_REQUESTS:
        return frozenset(w for w in SAMPLE_WORDS if 2 <= len(w) <= max_len), "내장 샘플 (requests 없음)"

    for url in GITHUB_URLS:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                continue

            text = resp.text

            # 한글 단어만 추출 (JS 파일이든 txt 파일이든 동일하게 처리)
            # JS 파일: "단어", '단어' 형태로 되어있음
            # txt 파일: 한 줄에 단어 하나
            words = set()

            # 방법1: 따옴표 안의 한글 단어 추출 (JS 배열)
            quoted = re.findall(r'["\']([가-힣]{2,' + str(max_len) + r'})["\']', text)
            if quoted:
                words.update(quoted)

            # 방법2: 줄 단위 한글 단어 추출 (txt)
            for line in text.splitlines():
                w = line.strip()
                if re.match(r'^[가-힣]{2,' + str(max_len) + r'}$', w):
                    words.add(w)

            if len(words) > 100:  # 충분히 많은 단어가 있으면 성공
                return frozenset(words), f"GitHub ({url.split('/')[-1]}), {len(words):,}개"

        except Exception:
            continue

    # 모두 실패 시 샘플 사용
    sample = frozenset(w for w in SAMPLE_WORDS if 2 <= len(w) <= max_len)
    return sample, f"내장 샘플 ({len(sample)}개)"


@st.cache_data
def build_index(words_frozen: frozenset) -> dict:
    index = defaultdict(list)
    for word in words_frozen:
        index[word[0]].append(word)
    return dict(index)


# ────────────────────────────────────────────────
# 핵심 게임 로직
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
    dead_ends = [
        w for w in candidates
        if not any(
            ch in index and any(x not in used and x != w for x in index[ch])
            for ch in get_start_chars(w[-1])
        )
    ]
    return random.choice(dead_ends if dead_ends else candidates)


# ────────────────────────────────────────────────
# 세션 상태 초기화
# ────────────────────────────────────────────────

def init_state():
    if "initialized" not in st.session_state:
        words, source = fetch_words_from_github()
        index = build_index(words)
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


def reset_game():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ────────────────────────────────────────────────
# UI
# ────────────────────────────────────────────────

st.set_page_config(page_title="끝말잇기", page_icon="🎯", layout="centered")

st.markdown("""
<style>
    .block-container { max-width: 680px; padding-top: 2rem; }
    .chat-wrap {
        background: #f5f7fa;
        border-radius: 16px;
        padding: 16px;
        height: 360px;
        overflow-y: auto;
        margin-bottom: 16px;
        border: 1px solid #e4e7ed;
    }
    .msg-row-ai   { display:flex; justify-content:flex-start; margin:8px 0; align-items:flex-end; gap:8px; }
    .msg-row-user { display:flex; justify-content:flex-end;   margin:8px 0; align-items:flex-end; gap:8px; }
    .avatar { font-size: 1.4rem; }
    .bubble-ai {
        background: #fff;
        border: 1px solid #dde1ea;
        border-radius: 18px 18px 18px 4px;
        padding: 10px 16px;
        font-size: 1.15rem; font-weight: 600; color: #2d2d2d;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    .bubble-user {
        background: linear-gradient(135deg, #4f8ef7, #6c63ff);
        color: #fff;
        border-radius: 18px 18px 4px 18px;
        padding: 10px 16px;
        font-size: 1.15rem; font-weight: 600;
        box-shadow: 0 1px 4px rgba(79,142,247,0.3);
    }
    .hint-banner {
        background: linear-gradient(90deg, #e8f4fd, #f0eaff);
        border-radius: 10px;
        padding: 10px 16px;
        font-size: 1rem;
        margin-bottom: 10px;
        border-left: 4px solid #4f8ef7;
    }
    .timer-wrap { margin-bottom: 10px; }
    .timer-label {
        font-size: 0.85rem; color: #555;
        margin-bottom: 4px;
        display: flex; justify-content: space-between;
    }
    .timer-bar-bg { background: #e4e7ed; border-radius: 999px; height: 14px; overflow: hidden; }
    .timer-bar-fill { height: 100%; border-radius: 999px; transition: width 0.5s linear; }
    .chain-badge {
        display: inline-block;
        padding: 3px 12px; border-radius: 999px;
        font-size: 0.85rem; font-weight: 700; margin-left: 8px;
    }
    .source-badge {
        font-size: 0.75rem; color: #888;
        background: #f0f0f0; border-radius: 6px;
        padding: 2px 8px; display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# 로딩 중 단어 다운로드
with st.spinner("단어 목록을 불러오는 중..."):
    init_state()

# ── 헤더 ──
st.title("🎯 끝말잇기")
st.markdown(
    f'<span class="source-badge">📚 {st.session_state.word_source}</span> '
    f'<span class="source-badge">사용된 단어: {len(st.session_state.used)}개</span>',
    unsafe_allow_html=True
)
st.markdown("")

# ── 통계 ──
chain = st.session_state.chain
time_limit = get_time_limit(chain)
turns = len(st.session_state.history)
user_turns = sum(1 for who, _ in st.session_state.history if who == "나")

c1, c2, c3, c4 = st.columns(4)
c1.metric("체인 🔗", chain)
c2.metric("제한 시간 ⏱", f"{time_limit}초")
c3.metric("내 턴", user_turns)
c4.metric("AI 턴", turns - user_turns)

st.divider()

# ── 타이머 ──
if not st.session_state.game_over:
    elapsed = time.time() - st.session_state.turn_start
    remaining = max(0.0, time_limit - elapsed)
    ratio = remaining / time_limit

    bar_color = "#4caf50" if ratio > 0.5 else "#ff9800" if ratio > 0.25 else "#f44336"
    pct = ratio * 100

    if chain < 10:
        stage_label, stage_color = "🟢 일반", "#4caf50"
    elif chain < 20:
        stage_label, stage_color = "🟡 빠름", "#ff9800"
    elif chain < 30:
        stage_label, stage_color = "🟠 매우 빠름", "#ff5722"
    else:
        stage_label, stage_color = "🔴 극한", "#f44336"

    st.markdown(f"""
    <div class="timer-wrap">
        <div class="timer-label">
            <span>⏱ 남은 시간: <b>{remaining:.1f}초</b>
                <span class="chain-badge" style="background:{stage_color}22;color:{stage_color};">{stage_label}</span>
            </span>
            <span>체인 {chain} → 제한 {time_limit}초</span>
        </div>
        <div class="timer-bar-bg">
            <div class="timer-bar-fill" style="width:{pct}%;background:{bar_color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if remaining <= 0:
        st.session_state.game_over = True
        st.session_state.winner = "ai"
        st.session_state.result_msg = f"⏰ 시간 초과! (제한 {time_limit}초) AI의 승리!"
        st.rerun()

# ── 힌트 ──
if not st.session_state.game_over:
    last = st.session_state.last_word
    starts = get_start_chars(last[-1])
    st.markdown(
        f'<div class="hint-banner">💡 <b>"{last}"</b> 다음 → '
        f'<b>"{" 또는 ".join(starts)}"</b> 으로 시작하는 단어</div>',
        unsafe_allow_html=True
    )

# ── 채팅창 ──
chat_html = '<div class="chat-wrap">'
for who, word in st.session_state.history:
    if who == "AI":
        chat_html += f'<div class="msg-row-ai"><span class="avatar">🤖</span><div class="bubble-ai">{word}</div></div>'
    else:
        chat_html += f'<div class="msg-row-user"><div class="bubble-user">{word}</div><span class="avatar">😊</span></div>'
chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)

# ── 결과 ──
if st.session_state.game_over:
    if st.session_state.winner == "user":
        st.success(st.session_state.result_msg)
    else:
        st.error(st.session_state.result_msg)
    st.info(f"🔗 최종 체인: **{chain}개** | 사용 단어: **{len(st.session_state.used)}개**")
    if st.button("🔄 다시 시작", use_container_width=True, type="primary"):
        reset_game()
        st.rerun()

# ── 입력 폼 ──
else:
    with st.form(key=f"word_form_{st.session_state.input_key}", clear_on_submit=True):
        col_in, col_btn = st.columns([5, 1])
        with col_in:
            user_input = st.text_input(
                "단어", placeholder="단어를 입력하고 Enter를 누르세요",
                label_visibility="collapsed"
            )
        with col_btn:
            submitted = st.form_submit_button("입력", use_container_width=True, type="primary")

    if submitted and user_input:
        word = user_input.strip()

        # 시간 초과 재확인
        if time.time() - st.session_state.turn_start > time_limit:
            st.session_state.game_over = True
            st.session_state.winner = "ai"
            st.session_state.result_msg = f"⏰ 시간 초과! AI의 승리!"
            st.rerun()

        valid, err = is_valid_word(word, st.session_state.last_word, st.session_state.used, st.session_state.words)
        if not valid:
            st.warning(f"❌ {err}")
        else:
            st.session_state.used.add(word)
            st.session_state.last_word = word
            st.session_state.history.append(("나", word))
            st.session_state.chain += 1
            st.session_state.input_key += 1

            ai_word = ai_pick(word, st.session_state.used, st.session_state.index)
            if ai_word is None:
                st.session_state.game_over = True
                st.session_state.winner = "user"
                st.session_state.result_msg = f"🎉 AI가 '{word[-1]}'(으)로 시작하는 단어를 찾지 못했어요! 당신의 승리!"
            else:
                st.session_state.used.add(ai_word)
                st.session_state.last_word = ai_word
                st.session_state.history.append(("AI", ai_word))
                st.session_state.chain += 1
                st.session_state.turn_start = time.time()

                next_starts = get_start_chars(ai_word[-1])
                if not any(
                    ch in st.session_state.index and
                    any(w not in st.session_state.used for w in st.session_state.index[ch])
                    for ch in next_starts
                ):
                    st.session_state.game_over = True
                    st.session_state.winner = "ai"
                    st.session_state.result_msg = f"😢 '{ai_word[-1]}'(으)로 시작하는 단어가 없어요. AI의 승리!"

            st.rerun()

    st.divider()
    if st.button("🔄 게임 초기화"):
        reset_game()
        st.rerun()

    # 1초마다 타이머 갱신
    if not st.session_state.game_over:
        time.sleep(1)
        st.rerun()
