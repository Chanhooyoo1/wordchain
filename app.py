import random
import time
import re
import base64
import streamlit as st
import streamlit.components.v1 as components
from collections import defaultdict

# ────────────────────────────────────────────────
# 0. 오디오 유틸리티 (window.parent 기반 - 리런 생존)
# ────────────────────────────────────────────────
def load_b64(filepath: str) -> str | None:
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def inject_audio_manager():
    """
    페이지에 단 한 번 오디오 매니저를 심는다.
    window.parent.__audioManager 에 붙여서 리런 후에도 유지.
    최초 클릭 시 AudioContext unlock → 이후 모든 재생 가능.
    """
    components.html("""
<script>
(function(){
  var p = window.parent;
  if (p.__audioManager) return;   // 이미 존재하면 스킵

  p.__audioManager = {
    bgm: null,

    // AudioContext unlock (브라우저 자동재생 차단 해제)
    unlock: function() {
      if (p.__audioUnlocked) return;
      try {
        var ctx = new (p.AudioContext || p.webkitAudioContext)();
        var buf = ctx.createBuffer(1, 1, 22050);
        var src = ctx.createBufferSource();
        src.buffer = buf;
        src.connect(ctx.destination);
        src.start(0);
        ctx.close();
        p.__audioUnlocked = true;
      } catch(e) {}
    },

    playBGM: function(b64, volume, delay) {
      var self = this;
      delay = delay || 0;
      // 기존 BGM 정지
      if (self.bgm) { self.bgm.pause(); self.bgm = null; }
      setTimeout(function(){
        var a = new p.Audio('data:audio/mp3;base64,' + b64);
        a.loop   = true;
        a.volume = volume || 0.45;
        a.play().catch(function(){});
        self.bgm = a;
      }, delay);
    },

    stopBGM: function() {
      if (this.bgm) { this.bgm.pause(); this.bgm = null; }
    },

    playSFX: function(b64, volume) {
      var a = new p.Audio('data:audio/mp3;base64,' + b64);
      a.volume = volume || 0.8;
      a.play().catch(function(){});
    }
  };

  // 부모 페이지의 모든 클릭에서 unlock 시도
  p.document.addEventListener('click', function(){
    p.__audioManager.unlock();
  }, { once: false });
})();
</script>
""", height=0)


def cmd_play_bgm(b64: str, volume: float = 0.45, delay_ms: int = 0):
    """BGM 교체 명령을 parent 오디오 매니저로 전달"""
    components.html(f"""
<script>
(function(){{
  var am = window.parent.__audioManager;
  if (!am) return;
  am.stopBGM();
  am.playBGM('{b64}', {volume}, {delay_ms});
}})();
</script>
""", height=0)


def cmd_play_sfx(b64: str, volume: float = 0.8):
    """효과음 재생 명령"""
    components.html(f"""
<script>
(function(){{
  var am = window.parent.__audioManager;
  if (!am) return;
  am.playSFX('{b64}', {volume});
}})();
</script>
""", height=0)


def play_stage_transition(sfx_file: str, bgm_file: str,
                           sfx_volume: float = 1.0,
                           bgm_volume: float = 0.45,
                           sfx_duration_ms: int = 3000):
    """전환 효과음 → (sfx_duration 후) 새 BGM"""
    sfx_b64 = load_b64(sfx_file)
    bgm_b64 = load_b64(bgm_file)
    sfx_src = sfx_b64 or ""
    bgm_src = bgm_b64 or ""
    components.html(f"""
<script>
(function(){{
  var am = window.parent.__audioManager;
  if (!am) return;

  am.stopBGM();

  // 전환 효과음
  if ('{sfx_src}') {{
    am.playSFX('{sfx_src}', {sfx_volume});
  }}

  // 효과음 끝난 뒤 BGM 시작
  if ('{bgm_src}') {{
    am.playBGM('{bgm_src}', {bgm_volume}, {sfx_duration_ms});
  }}
}})();
</script>
""", height=0)


def start_bgm_only(bgm_file: str, volume: float = 0.45):
    b64 = load_b64(bgm_file)
    if not b64:
        return
    cmd_play_bgm(b64, volume, delay_ms=0)


def play_sfx(sfx_file: str, volume: float = 0.8):
    b64 = load_b64(sfx_file)
    if not b64:
        return
    cmd_play_sfx(b64, volume)


# ────────────────────────────────────────────────
# 1. 스테이지 정의
# ────────────────────────────────────────────────
STAGES = [
    (35, 2.0,  "stage5", "static/bgm5.mp3", "static/stage5_start.mp3"),
    (28, 5.0,  "stage4", "static/bgm4.mp3", "static/stage4_start.mp3"),
    (18, 8.0,  "stage3", "static/bgm3.mp3", "static/stage3_start.mp3"),
    (8,  12.0, "stage2", "static/bgm2.mp3", "static/stage2_start.mp3"),
    (0,  15.0, "stage1", "static/bgm1.mp3", "static/stage1_start.mp3"),
]

def get_stage(chain: int) -> tuple:
    for min_chain, limit, name, bgm, sfx in STAGES:
        if chain >= min_chain:
            return limit, name, bgm, sfx
    return 15.0, "stage1", "static/bgm1.mp3", "static/stage1_start.mp3"


# ────────────────────────────────────────────────
# 2. 데이터 로드 및 두음법칙
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
    return frozenset(["가구","가방","가수","기차","나비","나무",
                      "우주","주스","스낵","노을","음악"])

DUEUM = {
    '녀':'여','뇨':'요','뉴':'유','니':'이','랴':'야','려':'여','례':'예','료':'요',
    '류':'유','리':'이','락':'낙','래':'내','랭':'냉','략':'약','량':'양','령':'영',
    '로':'노','뢰':'뇌','룡':'용','루':'누','륙':'육','륜':'윤','률':'율','릉':'능',
    '린':'인','림':'임','립':'입','라':'나','랄':'날','람':'남','랍':'납','랑':'낭',
    '르':'느','념':'염','렴':'염','름':'늠',
}

def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM:
        chars.add(DUEUM[last_char])
    return list(chars)


# ────────────────────────────────────────────────
# 3. 페이지 설정 및 CSS
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
    .msg-row-ai   { display:flex; justify-content:flex-start; margin-bottom:12px; }
    .msg-row-user { display:flex; justify-content:flex-end;   margin-bottom:12px; }
    .bubble-ai   { background:#ffffff; color:black; border:1px solid #dee2e6;
                   border-radius:15px 15px 15px 2px; padding:8px 12px; }
    .bubble-user { background:linear-gradient(135deg,#FF0055,#7000FF); color:white;
                   border-radius:15px 15px 2px 15px; padding:8px 12px; }
    .timer-container { width:100%; background-color:#333; border-radius:10px;
                       height:18px; margin-bottom:4px; overflow:hidden; }
    .bank-container  { width:100%; background-color:#222; border-radius:5px;
                       height:8px; overflow:hidden; }
    div.stButton > button {
        background: linear-gradient(135deg,#FF0000,#8A2BE2) !important;
        color: white !important; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 매 리런마다 오디오 매니저 inject (존재하면 스킵되므로 부담 없음)
inject_audio_manager()


# ────────────────────────────────────────────────
# 4. 게임 입장 전 화면
# ────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        total_rounds = st.number_input("총 라운드 수", 1, 10, 3)
    with col2:
        time_choice = st.selectbox("전체 제한 시간 (초)", [180, 120, 90, 60], index=1)
    with col3:
        difficulty = st.selectbox("AI 난이도", ["쉬움", "보통", "어려움"], index=1)

    if st.button("게임 입장하기"):  # ← 이 클릭이 AudioContext unlock 트리거
        words_data  = load_word_data()
        idx         = defaultdict(list)
        valid_words = []
        for w in words_data:
            if w and len(w) >= 2:
                idx[w[0]].append(w)
                valid_words.append(w)

        if not valid_words:
            valid_words = ["기차","나무","나비","우주","주스"]
            for w in valid_words:
                idx[w[0]].append(w)

        first = random.choice(valid_words)
        now   = time.time()

        st.session_state.update({
            "initialized":     True,
            "difficulty":      difficulty,
            "words":           frozenset(valid_words),
            "index":           dict(idx),
            "user_score":      0,
            "ai_score":        0,
            "current_round":   1,
            "total_rounds":    total_rounds,
            "game_start_time": now,
            "total_limit":     float(time_choice),
            "turn_start":      now,
            "used":            {first},
            "last_word":       first,
            "history":         [("AI", first)],
            "round_over":      False,
            "chain":           1,
            "winner":          None,
            "current_stage":   "stage1",
            "bgm_started":     False,
        })
        st.rerun()
    st.stop()


# ────────────────────────────────────────────────
# 5. 타이머 계산 + BGM/스테이지 관리
# ────────────────────────────────────────────────
now = time.time()

bank_rem    = max(0.0, st.session_state.total_limit
                       - (now - st.session_state.game_start_time))
bank_ratio  = bank_rem / st.session_state.total_limit

dynamic_limit, new_stage, new_bgm, new_sfx = get_stage(st.session_state.chain)
turn_elapsed      = now - st.session_state.turn_start
actual_turn_rem   = max(0.0, dynamic_limit - turn_elapsed)
actual_turn_ratio = actual_turn_rem / dynamic_limit

prev_stage = st.session_state.get("current_stage", "stage1")

if not st.session_state.get("bgm_started", False):
    # 최초 또는 라운드 리셋: 전환음 없이 BGM만
    start_bgm_only(new_bgm, volume=0.45)
    st.session_state.bgm_started   = True
    st.session_state.current_stage = new_stage

elif prev_stage != new_stage:
    # 스테이지 업: 전환음(3초) → 새 BGM
    play_stage_transition(new_sfx, new_bgm,
                          sfx_volume=1.0, bgm_volume=0.45,
                          sfx_duration_ms=3000)
    st.session_state.current_stage = new_stage

st.session_state.bank_rem        = bank_rem
st.session_state.actual_turn_rem = actual_turn_rem


# ────────────────────────────────────────────────
# 6. 게임 중 UI
# ────────────────────────────────────────────────
if not st.session_state.get("round_over", False):

    if bank_rem <= 0 or actual_turn_rem <= 0:
        st.session_state.round_over = True
        st.session_state.ai_score  += 1
        st.session_state.end_reason = "timeout"
        st.session_state.winner     = "AI"
        st.rerun()

    st.write(f"**라운드 {st.session_state.current_round} / {st.session_state.total_rounds}**")
    c1, c2 = st.columns(2)
    c1.metric("나 (User)", st.session_state.user_score)
    c2.metric("상대 (AI)",  st.session_state.ai_score)

    starts         = get_start_chars(st.session_state.last_word[-1])
    starts_display = " 또는 ".join(starts)
    st.markdown(f"""
        <div style="text-align:center; margin-top:10px; margin-bottom:15px;">
            <div style="display:inline-block;
                        background:linear-gradient(135deg,#FF0055,#7000FF);
                        color:white; padding:4px 15px; border-radius:20px;
                        font-weight:bold; font-size:1.1rem; margin-bottom:10px;
                        box-shadow:0 2px 5px rgba(0,0,0,0.2); border:1px solid #fff;">
                이은 단어 수: {st.session_state.chain} &nbsp;|&nbsp; {new_stage}
            </div>
            <div style="background:#ffffff; border:2px solid #8A2BE2;
                        border-radius:12px; padding:12px;
                        box-shadow:inset 0 0 10px rgba(138,43,226,0.1);">
                <div style="color:#666; font-size:0.85rem; margin-bottom:3px;">다음 시작 글자</div>
                <div style="color:#FF0055; font-size:1.5rem; font-weight:900;
                            letter-spacing:2px;">{starts_display}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    t_color = "#FF0055" if actual_turn_ratio < 0.3 else "#f1e05a"
    st.markdown(f"""
        <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:10px;
                    border:1px solid #444; margin-bottom:10px;">
            <div style="margin-bottom:8px;">
                <p style="margin:0; font-size:11px; color:#3a86ff; font-weight:bold;">
                    총 시간 ({bank_rem:.1f}s)</p>
                <div class="bank-container">
                    <div style="width:{bank_ratio*100:.1f}%; background:#3a86ff;
                                height:100%; transition:width 0.1s linear;"></div>
                </div>
            </div>
            <div>
                <p style="margin:0; font-size:12px; color:{t_color}; font-weight:bold;">
                    차례 제한시간 ({actual_turn_rem:.1f}s)</p>
                <div class="timer-container">
                    <div style="width:{actual_turn_ratio*100:.1f}%; background:{t_color};
                                height:100%; transition:width 0.1s linear;"></div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    chat_html    = '<div class="chat-wrap">'
    history_list = st.session_state.get("history", [])
    for speaker, text in history_list:
        side  = "ai"        if speaker == "AI" else "user"
        bub   = "bubble-ai" if speaker == "AI" else "bubble-user"
        style = ("color:#FF0000; font-weight:bold; border:2px solid #FF0000;"
                 "box-shadow:0 0 10px rgba(255,0,0,0.3);") if "🔥" in text else ""
        chat_html += (f'<div class="msg-row-{side}">'
                      f'<div class="{bub}" style="{style}">'
                      f'{text.replace("🔥","")}</div></div>')
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    with st.form(key="game_input", clear_on_submit=True):
        user_input = st.text_input("단어 입력", label_visibility="collapsed",
                                   placeholder="단어를 입력해주세요...")
        submit = st.form_submit_button("전송")

        if submit and user_input:
            word = user_input.strip()

            if (word in st.session_state.words
                    and word not in st.session_state.used
                    and word[0] in starts):

                st.session_state.used.add(word)
                st.session_state.history.append(("User", word))
                st.session_state.chain    += 1
                st.session_state.last_word = word

                # 전송 효과음 (폼 제출 = 사용자 제스처 → 바로 재생됨)
                play_sfx("static/input.mp3", volume=0.8)

                candidates = []
                for ch in get_start_chars(word[-1]):
                    if ch in st.session_state.index:
                        candidates.extend(
                            w for w in st.session_state.index[ch]
                            if w not in st.session_state.used
                        )

                diff    = st.session_state.get("difficulty", "보통")
                give_up = 0.15 if diff == "쉬움" else 0.05 if diff == "보통" else 0
                if candidates and random.random() < give_up:
                    candidates = []

                if not candidates:
                    st.session_state.history[-1] = ("User", f"🔥{word}")
                    st.session_state.user_score  += 1

                    if st.session_state.current_round >= st.session_state.total_rounds:
                        st.session_state.round_over = True
                        st.session_state.winner     = "User"
                    else:
                        st.toast("🎊 AI 항복! 다음 라운드로 이동합니다.")
                        time.sleep(1.5)
                        new_f   = random.choice(list(st.session_state.words))
                        now_res = time.time()
                        st.session_state.update({
                            "current_round":   st.session_state.current_round + 1,
                            "game_start_time": now_res,
                            "turn_start":      now_res,
                            "used":            {new_f},
                            "last_word":       new_f,
                            "history":         [("AI", new_f)],
                            "chain":           1,
                            "current_stage":   "stage1",
                            "bgm_started":     False,
                        })
                    st.rerun()

                else:
                    delay = random.uniform(0.5, max(0.6, dynamic_limit * 0.4))
                    with st.spinner("AI가 생각 중..."):
                        time.sleep(delay)

                    if diff == "쉬움":
                        ai_word = random.choice(candidates)
                    elif diff == "보통":
                        candidates.sort(key=len)
                        mid     = len(candidates) // 2
                        ai_word = random.choice(candidates[mid:] if mid > 0 else candidates)
                    else:
                        ai_word = max(candidates, key=len)

                    is_killer = True
                    for nch in get_start_chars(ai_word[-1]):
                        if nch in st.session_state.index:
                            if any(w not in st.session_state.used and w != ai_word
                                   for w in st.session_state.index[nch]):
                                is_killer = False
                                break

                    final_msg = f"🔥{ai_word}" if is_killer else ai_word
                    st.session_state.used.add(ai_word)
                    st.session_state.history.append(("AI", final_msg))
                    st.session_state.last_word  = ai_word
                    st.session_state.chain     += 1
                    st.session_state.turn_start = time.time()
                    st.rerun()

            else:
                st.toast("❌ 잘못되거나 이미 사용된 단어입니다!")

# ────────────────────────────────────────────────
# 7. 라운드 종료 화면
# ────────────────────────────────────────────────
else:
    b_rem  = st.session_state.get("bank_rem", 0)
    t_rem  = st.session_state.get("actual_turn_rem", 0)
    reason = "시간 초과!" if (b_rem <= 0 or t_rem <= 0) else "AI의 역습!"
    st.error(f"💀 패배.. {reason}")
    c1, c2 = st.columns(2)
    c1.metric("최종 나 (User)", st.session_state.user_score)
    c2.metric("최종 상대 (AI)",  st.session_state.ai_score)

# ────────────────────────────────────────────────
# 8. 다음 라운드 / 완전 종료
# ────────────────────────────────────────────────
if st.session_state.get("round_over", False):
    if st.session_state.current_round < st.session_state.total_rounds:
        if st.button(f"🕐 다음 라운드({st.session_state.current_round + 1}) 시작하기"):
            new_first = random.choice(list(st.session_state.words))
            now_reset = time.time()
            st.session_state.update({
                "round_over":      False,
                "winner":          None,
                "game_start_time": now_reset,
                "turn_start":      now_reset,
                "used":            {new_first},
                "last_word":       new_first,
                "history":         [("AI", new_first)],
                "chain":           1,
                "current_round":   st.session_state.current_round + 1,
                "current_stage":   "stage1",
                "bgm_started":     False,
            })
            st.rerun()
    else:
        st.warning("🎮 모든 라운드가 종료되었습니다!")
        if st.button("🔄 게임 초기화 및 처음부터 다시 시작", key="final_restart"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ────────────────────────────────────────────────
# 9. 실시간 자동 새로고침 + UI 보정
# ────────────────────────────────────────────────
if not st.session_state.get("round_over", False):
    time.sleep(0.1)
    components.html("""
<script>
const fixUI = () => {
    const win   = window.parent.document;
    const chat  = win.querySelector('.chat-wrap');
    const input = win.querySelector('input');
    if (chat) chat.scrollTop = chat.scrollHeight;
    if (input
        && win.activeElement.tagName !== 'INPUT'
        && win.activeElement.tagName !== 'TEXTAREA') {
        input.focus();
    }
};
const observer = new MutationObserver(fixUI);
observer.observe(window.parent.document.body, { childList: true, subtree: true });
setInterval(fixUI, 400);
fixUI();
</script>
""", height=0)
    st.rerun()
