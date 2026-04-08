import random
import time
import re
import base64
import streamlit as st
import streamlit.components.v1 as components
from collections import defaultdict

# ────────────────────────────────────────────────
# 0. 사운드 로딩 및 JS 엔진 (중첩/유실 방지 강화)
# ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_b64(filepath: str) -> str:
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

def inject_sound_engine():
    """
    브라우저의 자동재생 차단을 해제하고, 소리 중첩을 방지하는 JS 매니저
    """
    components.html("""
<script>
(function(){
    var p = window.parent;
    if (p.__kkutuAudio) return;

    p.__kkutuAudio = {
        bgm: null,
        currentBgmB64: null,
        tickAudio: null,
        tickInterval: null,
        lastSfxTime: 0,

        // ── [1] 오디오 잠금 해제 ──
        unlock: function() {
            if (this._ctx && this._ctx.state === 'running') return;
            this._ctx = new (p.AudioContext || p.webkitAudioContext)();
            this._ctx.resume().then(() => console.log("Audio Engine Ready"));
        },

        // ── [2] BGM 제어 (중복 재생 원천 봉쇄) ──
        playBGM: function(b64, vol) {
            if (!b64 || this.currentBgmB64 === b64) return; // 같은 곡이면 무시
            
            if (this.bgm) { this.bgm.pause(); this.bgm = null; }
            
            this.currentBgmB64 = b64;
            var a = new p.Audio('data:audio/mp3;base64,' + b64);
            a.loop = true;
            a.volume = vol || 0.4;
            a.play().catch(e => console.log("BGM Play Error:", e));
            this.bgm = a;
        },

        stopBGM: function() {
            if (this.bgm) { this.bgm.pause(); this.bgm = null; this.currentBgmB64 = null; }
        },

        // ── [3] 효과음 제어 (너무 짧은 연속 재생 방지) ──
        playSFX: function(b64, vol) {
            if (!b64) return;
            var now = Date.now();
            if (now - this.lastSfxTime < 50) return; // 0.05초 내 중복 재생 방지
            
            var a = new p.Audio('data:audio/mp3;base64,' + b64);
            a.volume = vol || 0.7;
            a.play().catch(() => {});
            this.lastSfxTime = now;
        },

        // ── [4] 타이머 틱 (확실한 중지 보장) ──
        startTick: function(b64) {
            if (this.tickInterval) return;
            this.tickAudio = new p.Audio('data:audio/mp3;base64,' + b64);
            this.tickInterval = setInterval(() => {
                if (this.tickAudio) {
                    this.tickAudio.currentTime = 0;
                    this.tickAudio.play().catch(() => {});
                }
            }, 1000);
        },

        stopTick: function() {
            if (this.tickInterval) { clearInterval(this.tickInterval); this.tickInterval = null; }
            if (this.tickAudio) { this.tickAudio.pause(); this.tickAudio = null; }
        }
    };

    p.document.addEventListener('click', () => p.__kkutuAudio.unlock(), {once: true});
})();
</script>
""", height=0)

# ── 명령 전달용 헬퍼 함수 ──
def _send_js(cmd: str):
    components.html(f"<script>if(window.parent.__kkutuAudio) {{ {cmd} }}</script>", height=0)

# ────────────────────────────────────────────────
# 1. 게임 스테이지 및 데이터 설정
# ────────────────────────────────────────────────
STAGES = [
    (30, 3.0, "STAGE 4", "bgm4.mp3", "up4.mp3"),
    (15, 7.0, "STAGE 3", "bgm3.mp3", "up3.mp3"),
    (6, 11.0, "STAGE 2", "bgm2.mp3", "up2.mp3"),
    (0, 15.0, "STAGE 1", "bgm1.mp3", ""),
]

@st.cache_data
def load_words():
    # 실제 파일 로드 로직 (파일 없으면 기본 리스트)
    return frozenset(["기차", "나무", "나비", "우주", "주스", "스낵", "노을", "음악", "학교", "교실"])

# ────────────────────────────────────────────────
# 2. 게임 초기화 및 페이지 설정
# ────────────────────────────────────────────────
st.set_page_config(page_title="Speed 끝말잇기", layout="centered")
inject_sound_engine()

if "initialized" not in st.session_state:
    st.title("🎮 Speed 끝말잇기")
    if st.button("게임 시작 (소리 활성화)"):
        all_words = load_words()
        first = random.choice(list(all_words))
        st.session_state.update({
            "initialized": True, "words": all_words, "history": [("AI", first)],
            "last_word": first, "used": {first}, "chain": 1,
            "turn_start": time.time(), "round_over": False,
            "current_stage": None, "ticking": False
        })
        st.rerun()
    st.stop()

# ────────────────────────────────────────────────
# 3. 실시간 로직 (타이머 & 사운드 체크)
# ────────────────────────────────────────────────
now = time.time()
# 현재 스테이지 결정
limit, stage_name, bgm_file, sfx_file = next(s for s in STAGES if st.session_state.chain >= s[0])
rem = max(0.0, limit - (now - st.session_state.turn_start))

# 스테이지 변경 시 BGM 교체 및 효과음 (중복 실행 방지)
if st.session_state.current_stage != stage_name:
    if st.session_state.current_stage is not None: # 첫 스테이지가 아닐 때만 업그레이드 음
        _send_js(f"window.parent.__kkutuAudio.playSFX('{get_b64('static/'+sfx_file)}', 0.8);")
    _send_js(f"window.parent.__kkutuAudio.playBGM('{get_b64('static/'+bgm_file)}', 0.4);")
    st.session_state.current_stage = stage_name

# 타이머 틱 관리 (3초 이하)
if rem <= 3.0 and rem > 0 and not st.session_state.ticking:
    _send_js(f"window.parent.__kkutuAudio.startTick('{get_b64('static/tick.mp3')}');")
    st.session_state.ticking = True
elif rem > 3.0 and st.session_state.ticking:
    _send_js("window.parent.__kkutuAudio.stopTick();")
    st.session_state.ticking = False

# 패배 판정
if rem <= 0 and not st.session_state.round_over:
    st.session_state.round_over = True
    _send_js("window.parent.__kkutuAudio.stopBGM();")
    _send_js(f"window.parent.__kkutuAudio.playSFX('{get_b64('static/lose.mp3')}', 1.0);")
    st.rerun()

# ────────────────────────────────────────────────
# 4. UI 및 입력 처리
# ────────────────────────────────────────────────
st.subheader(f"[{stage_name}] 체인: {st.session_state.chain}")
st.progress(rem / limit)
st.write(f"남은 시간: **{rem:.1f}초**")

# 채팅창 구현 (간소화)
for speaker, text in st.session_state.history[-5:]:
    st.write(f"**{speaker}**: {text}")

if not st.session_state.round_over:
    with st.form("input_form", clear_on_submit=True):
        user_in = st.text_input("단어 입력:").strip()
        if st.form_submit_button("전송"):
            last_char = st.session_state.last_word[-1]
            if user_in and user_in.startswith(last_char) and user_in in st.session_state.words:
                # 유저 성공
                st.session_state.used.add(user_in)
                st.session_state.history.append(("User", user_in))
                st.session_state.chain += 1
                st.session_state.last_word = user_in
                st.session_state.turn_start = time.time()
                _send_js(f"window.parent.__kkutuAudio.playSFX('{get_b64('static/input.mp3')}', 0.7);")
                _send_js("window.parent.__kkutuAudio.stopTick();")
                st.session_state.ticking = False
                
                # AI 반격 (간단 로직)
                candidates = [w for w in st.session_state.words if w.startswith(user_in[-1]) and w not in st.session_state.used]
                if candidates:
                    ai_word = random.choice(candidates)
                    st.session_state.used.add(ai_word)
                    st.session_state.history.append(("AI", ai_word))
                    st.session_state.last_word = ai_word
                    st.session_state.chain += 1
                    st.session_state.turn_start = time.time()
                st.rerun()
            else:
                _send_js(f"window.parent.__kkutuAudio.playSFX('{get_b64('static/fail.mp3')}', 0.7);")
                st.error("오답입니다!")

    # 실시간 화면 갱신
    time.sleep(0.1)
    st.rerun()
else:
    st.error("GAME OVER")
    if st.button("다시 시작"):
        st.session_state.clear()
        st.rerun()
