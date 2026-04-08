import random
import time
import re
import base64
from collections import defaultdict
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


BASE_DIR = Path(__file__).resolve().parent


SFX_FILES = {
    "input": "sfx_input.mp3",
    "fail": "sfx_fail.mp3",
    "killer": "sfx_killer.mp3",
    "win": "sfx_win.mp3",
    "lose": "sfx_lose.mp3",
    "tick": "sfx_tick.mp3",
    "stage_start": "stage2_start.mp3",
}

AUDIO_EVENT_DELAY_MS = 180
ROUND_START_BGM_DELAY_MS = 260


def resolve_asset_path(filepath: str) -> Path:
    p = Path(filepath)
    if p.is_absolute():
        return p
    return BASE_DIR / p


def load_b64(filepath: str) -> str:
    try:
        with open(resolve_asset_path(filepath), "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def inject_kkutu_audio():
    """
    끄투 스타일 오디오 매니저를 window.parent에 한 번만 심는다.
    - BGM : 페이드 인/아웃 지원, 루프
    - SFX : 이벤트별 효과음
    - TICK: 타이머 3초 이하 자동 틱
    - FALLBACK: 파일 없으면 Web Audio API로 비프음 생성
    """
    components.html(
        """
<script>
(function(){
  var p = window.parent;
  if (p.__kkutuAudio) {
    if (p.__kkutuStartClicked) p.__kkutuAudio.unlock();
    return;
  }

  p.__kkutuAudio = {
    bgm: null,
    bgmFading: false,
    sfxList: [],
    pendingEventTimer: null,
    keepAliveInterval: null,
    tickInterval: null,
    lastTickTime: 0,

    _ctx: null,
    _retryOnce: false,
    unlock: function() {
      try {
        if (!this._ctx) this._ctx = new (p.AudioContext || p.webkitAudioContext)();
        if (this._ctx.state === 'suspended') this._ctx.resume();
        var buf = this._ctx.createBuffer(1,1,22050);
        var src = this._ctx.createBufferSource();
        src.buffer = buf;
        src.connect(this._ctx.destination);
        src.start(0);
        p.__audioUnlocked = true;
        this.startKeepAlive();
      } catch(e){}
    },

    _beep: function(freq, dur, vol, type) {
      try {
        var ctx = new (p.AudioContext || p.webkitAudioContext)();
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = freq || 440;
        osc.type = type || 'sine';
        gain.gain.setValueAtTime(vol || 0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (dur || 0.15));
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + (dur || 0.15));
      } catch(e){}
    },

    _playAudioElement: function(a) {
      var self = this;
      this.unlock();
      a.play().catch(function(){
        // 자동재생 차단 시 다음 사용자 클릭에서 1회 재시도
        if (self._retryOnce) return;
        self._retryOnce = true;
        var retry = function() {
          self._retryOnce = false;
          try { a.play().catch(function(){}); } catch(e){}
          p.document.removeEventListener('click', retry, true);
        };
        p.document.addEventListener('click', retry, true);
      });
    },

    playBGM: function(b64, vol, fadeMs) {
      var self = this;
      vol = vol || 0.4;
      fadeMs = fadeMs || 800;

      function startNew() {
        if (!b64) return;
        var a = new p.Audio('data:audio/mp3;base64,' + b64);
        a.loop = true;
        a.volume = 0;
        self._playAudioElement(a);
        self.bgm = a;
        var step = vol / (fadeMs / 50);
        var fi = setInterval(function(){
          if (!self.bgm) {
            clearInterval(fi);
            return;
          }
          self.bgm.volume = Math.min(self.bgm.volume + step, vol);
          if (self.bgm.volume >= vol) clearInterval(fi);
        }, 50);
      }

      if (this.bgm && !this.bgmFading) {
        this.bgmFading = true;
        var old = this.bgm;
        var step = old.volume / (fadeMs / 50);
        var fo = setInterval(function(){
          old.volume = Math.max(old.volume - step, 0);
          if (old.volume <= 0) {
            clearInterval(fo);
            old.pause();
            self.bgmFading = false;
            startNew();
          }
        }, 50);
      } else {
        if (this.bgm) {
          this.bgm.pause();
          this.bgm = null;
        }
        startNew();
      }
    },

    // 현재 BGM을 즉시 끊고 새 BGM으로 바로 교체
    cutAndPlayBGM: function(b64, vol) {
      vol = vol || 0.4;
      if (this.bgm) {
        try { this.bgm.pause(); } catch(e){}
        this.bgm = null;
      }
      this.bgmFading = false;
      if (!b64) return;
      var a = new p.Audio('data:audio/mp3;base64,' + b64);
      a.loop = true;
      a.volume = vol;
      this._playAudioElement(a);
      this.bgm = a;
    },

    stopBGM: function(fadeMs) {
      if (!this.bgm) return;
      var self = this;
      fadeMs = fadeMs || 500;
      var old = this.bgm;
      var step = old.volume / (fadeMs / 50);
      var fo = setInterval(function(){
        old.volume = Math.max(old.volume - step, 0);
        if (old.volume <= 0) {
          clearInterval(fo);
          old.pause();
          self.bgm = null;
        }
      }, 50);
    },

    playSFX: function(b64, vol) {
      if (b64) {
        var a = new p.Audio('data:audio/mp3;base64,' + b64);
        a.volume = vol || 0.8;
        this.sfxList.push(a);
        a.onended = function() {
          var idx = p.__kkutuAudio.sfxList.indexOf(a);
          if (idx > -1) p.__kkutuAudio.sfxList.splice(idx, 1);
        };
        this._playAudioElement(a);
      }
    },

    stopSFX: function() {
      if (!this.sfxList || !this.sfxList.length) return;
      this.sfxList.forEach(function(a){
        try { a.pause(); a.currentTime = 0; } catch(e){}
      });
      this.sfxList = [];
    },

    clearPendingEvent: function() {
      if (this.pendingEventTimer) {
        clearTimeout(this.pendingEventTimer);
        this.pendingEventTimer = null;
      }
    },

    startKeepAlive: function() {
      var self = this;
      if (this.keepAliveInterval) return;
      this.keepAliveInterval = setInterval(function(){
        try {
          if (!self._ctx) return;
          if (self._ctx.state === 'suspended') self._ctx.resume();
          var osc = self._ctx.createOscillator();
          var gain = self._ctx.createGain();
          osc.connect(gain);
          gain.connect(self._ctx.destination);
          osc.frequency.value = 25;
          osc.type = 'sine';
          gain.gain.setValueAtTime(0.00001, self._ctx.currentTime);
          osc.start(self._ctx.currentTime);
          osc.stop(self._ctx.currentTime + 0.02);
        } catch(e){}
      }, 12000);
    },
    stopKeepAlive: function() {
      if (!this.keepAliveInterval) return;
      clearInterval(this.keepAliveInterval);
      this.keepAliveInterval = null;
    },

    sfxInput: function(b64) {
      if (b64) {
        this.playSFX(b64, 0.7);
      } else {
        this._beep(880, 0.08, 0.25, 'sine');
      }
    },
    sfxFail: function(b64) {
      if (b64) {
        this.playSFX(b64, 0.7);
      } else {
        this._beep(220, 0.15, 0.3, 'sawtooth');
        var self = this;
        setTimeout(function(){ self._beep(180, 0.2, 0.3, 'sawtooth'); }, 120);
      }
    },
    sfxKiller: function(b64) {
      if (b64) {
        this.playSFX(b64, 1.0);
      } else {
        var self = this;
        [0, 100, 200].forEach(function(d, i){
          setTimeout(function(){ self._beep(1200 - i*200, 0.12, 0.4, 'square'); }, d);
        });
      }
    },
    sfxWin: function(b64) {
      if (b64) {
        this.playSFX(b64, 0.9);
      } else {
        var self = this;
        [523,659,784,1047].forEach(function(f,i){
          setTimeout(function(){ self._beep(f, 0.18, 0.35, 'sine'); }, i*120);
        });
      }
    },
    sfxLose: function(b64) {
      if (b64) {
        this.playSFX(b64, 0.9);
      } else {
        var self = this;
        [400,320,260,200].forEach(function(f,i){
          setTimeout(function(){ self._beep(f, 0.25, 0.3, 'sawtooth'); }, i*150);
        });
      }
    },
    sfxStageUp: function(b64) {
      if (b64) {
        this.playSFX(b64, 1.0);
      } else {
        var self = this;
        [440,554,659,880].forEach(function(f,i){
          setTimeout(function(){ self._beep(f, 0.1, 0.4, 'sine'); }, i*80);
        });
      }
    },

    startTick: function(b64) {
      var self = this;
      if (this.tickInterval) return;
      this.tickInterval = setInterval(function(){
        var now = Date.now();
        if (now - self.lastTickTime < 900) return;
        self.lastTickTime = now;
        if (b64) {
          self.playSFX(b64, 0.6);
        } else {
          self._beep(1000, 0.05, 0.35, 'square');
        }
      }, 1000);
    },
    stopTick: function() {
      if (this.tickInterval) {
        clearInterval(this.tickInterval);
        this.tickInterval = null;
      }
    },

    // 라운드/스테이지 종료 시 오디오 잔재를 남기지 않도록 전체 정지
    stopAll: function() {
      this.clearPendingEvent();
      this.stopTick();
      this.stopSFX();
      if (this.bgm) {
        try { this.bgm.pause(); } catch(e){}
        this.bgm = null;
      }
      this.bgmFading = false;
    }
  };

  p.document.addEventListener('click', function(){
    p.__kkutuAudio.unlock();
  });

  // 게임 시작 버튼 클릭 직후 리런되어도 unlock 상태를 유지
  if (p.__kkutuStartClicked) {
    p.__kkutuAudio.unlock();
  }
})();
</script>
""",
        height=0,
    )


def inject_start_button_audio_bootstrap():
    """
    로비 화면의 '게임 입장하기' 버튼 클릭을 가로채서
    오디오 unlock 플래그를 먼저 올린다.
    """
    components.html(
        """
<script>
(function(){
  var p = window.parent;
  var d = p.document;
  function bind() {
    var btns = d.querySelectorAll('div.stButton > button');
    btns.forEach(function(btn){
      if (btn.__kkutuBound) return;
      if ((btn.innerText || '').trim() !== '게임 입장하기') return;
      btn.__kkutuBound = true;
      btn.addEventListener('click', function(){
        p.__kkutuStartClicked = true;
        if (p.__kkutuAudio) p.__kkutuAudio.unlock();
      }, {capture:true});
    });
  }
  bind();
  setTimeout(bind, 100);
})();
</script>
""",
        height=0,
    )


def _js(script: str):
    components.html(
        f"""
<script>
(function(){{
  var tries = 0;
  function run(){{
    var am = window.parent.__kkutuAudio;
    if (!am) {{
      tries += 1;
      if (tries < 30) setTimeout(run, 60);
      return;
    }}
    {script}
  }}
  run();
}})();
</script>
""",
        height=0,
    )


def audio_play_bgm(bgm_file: str, fade_ms: int = 800):
    b64 = load_b64(bgm_file)
    _js(f"am.playBGM('{b64}', 0.4, {fade_ms});")


def audio_stage_start_then_bgm(
    start_sfx_file: str = SFX_FILES["stage_start"],
    bgm_file: str = "bgm1.mp3",
    delay_ms: int = 0,
):
    start_b64 = load_b64(start_sfx_file)
    bgm_b64 = load_b64(bgm_file)
    _js(
        f"""
      am.stopAll();
      am.sfxStageUp('{start_b64}');
      setTimeout(function(){{
        am.cutAndPlayBGM('{bgm_b64}', 0.4);
      }}, {delay_ms});
    """
    )


def audio_stage_up(sfx_file: str, bgm_file: str, fade_ms: int = 800):
    sfx_b64 = load_b64(sfx_file)
    bgm_b64 = load_b64(bgm_file)
    _js(
        f"""
      am.sfxStageUp('{sfx_b64}');
      am.cutAndPlayBGM('{bgm_b64}', 0.4);
    """
    )


def audio_input(sfx_file: str = SFX_FILES["input"]):
    _js(f"am.sfxInput('{load_b64(sfx_file)}');")


def audio_fail(sfx_file: str = SFX_FILES["fail"]):
    _js(f"am.sfxFail('{load_b64(sfx_file)}');")


def audio_killer(sfx_file: str = SFX_FILES["killer"]):
    _js(f"am.sfxKiller('{load_b64(sfx_file)}');")


def audio_win(sfx_file: str = SFX_FILES["win"]):
    _js(f"am.stopTick(); am.stopBGM(300); am.sfxWin('{load_b64(sfx_file)}');")


def audio_lose(sfx_file: str = SFX_FILES["lose"]):
    _js(f"am.stopTick(); am.stopBGM(300); am.sfxLose('{load_b64(sfx_file)}');")


def audio_tick_start(sfx_file: str = SFX_FILES["tick"]):
    _js(f"am.startTick('{load_b64(sfx_file)}');")


def audio_tick_stop():
    _js("am.stopTick();")


def audio_stop_all():
    _js("am.stopAll();")


def audio_delayed_event(event: str, bgm_file: str = "", delay_ms: int = 1000):
    input_b64 = load_b64(SFX_FILES["input"])
    fail_b64 = load_b64(SFX_FILES["fail"])
    killer_b64 = load_b64(SFX_FILES["killer"])
    stage_start_b64 = load_b64(SFX_FILES["stage_start"])
    bgm_b64 = load_b64(bgm_file) if bgm_file else ""
    _js(
        f"""
      am.clearPendingEvent();
      am.pendingEventTimer = setTimeout(function(){{
        am.pendingEventTimer = null;
        am.stopSFX();
        if ('{event}' === 'input') am.sfxInput('{input_b64}');
        else if ('{event}' === 'fail') am.sfxFail('{fail_b64}');
        else if ('{event}' === 'killer') am.sfxKiller('{killer_b64}');
        else if ('{event}' === 'stage_start') am.sfxStageUp('{stage_start_b64}');
        if ('{bgm_b64}') {{
          if ('{event}' === 'stage_start') {{
            setTimeout(function(){{ am.cutAndPlayBGM('{bgm_b64}', 0.4); }}, {ROUND_START_BGM_DELAY_MS});
          }} else {{
            am.cutAndPlayBGM('{bgm_b64}', 0.4);
          }}
        }}
      }}, {delay_ms});
    """
    )


STAGES = [
    (35, 2.0, "stage5", "bgm5.mp3", "stage5_up.mp3"),
    (28, 5.0, "stage4", "bgm4.mp3", "stage4_up.mp3"),
    (18, 8.0, "stage3", "bgm3.mp3", "stage3_up.mp3"),
    (8, 12.0, "stage2", "bgm2.mp3", "stage2_up.mp3"),
    (0, 15.0, "stage1", "bgm1.mp3", ""),
]


def get_stage(chain: int):
    for min_chain, limit, name, bgm, sfx in STAGES:
        if chain >= min_chain:
            return limit, name, bgm, sfx
    return 15.0, "stage1", "bgm1.mp3", ""


@st.cache_data(show_spinner=False)
def load_word_data():
    try:
        with open(resolve_asset_path("words.js"), "r", encoding="utf-8") as f:
            content = f.read()
        extracted = re.findall(r'["\']([가-힣]{2,4})["\']', content)
        if extracted:
            return frozenset(extracted)
    except FileNotFoundError:
        pass
    return frozenset(
        ["가구", "가방", "가수", "기차", "나비", "나무", "우주", "주스", "스낵", "노을", "음악"]
    )


DUEUM = {
    "녀": "여",
    "뇨": "요",
    "뉴": "유",
    "니": "이",
    "랴": "야",
    "려": "여",
    "례": "예",
    "료": "요",
    "류": "유",
    "리": "이",
    "락": "낙",
    "래": "내",
    "랭": "냉",
    "략": "약",
    "량": "양",
    "령": "영",
    "로": "노",
    "뢰": "뇌",
    "룡": "용",
    "루": "누",
    "륙": "육",
    "륜": "윤",
    "률": "율",
    "릉": "능",
    "린": "인",
    "림": "임",
    "립": "입",
    "라": "나",
    "랄": "날",
    "람": "남",
    "랍": "납",
    "랑": "낭",
    "르": "느",
    "념": "염",
    "렴": "염",
    "름": "늠",
}


def get_start_chars(last_char):
    chars = {last_char}
    if last_char in DUEUM:
        chars.add(DUEUM[last_char])
    return list(chars)


st.set_page_config(page_title="끝말잇기", layout="centered")
st.markdown(
    """
<style>
    .grad-title {
        background: linear-gradient(90deg,#FF0000,#8A2BE2);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        font-size:3rem; font-weight:800; text-align:center; margin-bottom:5px;
    }
    .chat-wrap {
        background:#f8f9fa; border-radius:15px; padding:20px;
        height:300px; overflow-y:auto; border:1px solid #e9ecef;
        margin-bottom:10px; display:flex; flex-direction:column;
    }
    .msg-row-ai   { display:flex; justify-content:flex-start; margin-bottom:12px; }
    .msg-row-user { display:flex; justify-content:flex-end;   margin-bottom:12px; }
    .bubble-ai   { background:#fff; color:black; border:1px solid #dee2e6;
                   border-radius:15px 15px 15px 2px; padding:8px 12px; }
    .bubble-user { background:linear-gradient(135deg,#FF0055,#7000FF); color:white;
                   border-radius:15px 15px 2px 15px; padding:8px 12px; }
    .timer-container { width:100%; background:#333; border-radius:10px;
                       height:18px; margin-bottom:4px; overflow:hidden; }
    .bank-container  { width:100%; background:#222; border-radius:5px;
                       height:8px; overflow:hidden; }
    div.stButton > button {
        background:linear-gradient(135deg,#FF0000,#8A2BE2) !important;
        color:white !important; width:100%;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 오디오 모듈은 게임 입장 버튼 이후에만 활성화
if st.session_state.get("audio_enabled", False):
    inject_kkutu_audio()

if "initialized" not in st.session_state:
    inject_start_button_audio_bootstrap()
    st.markdown('<div class="grad-title">끝말잇기</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        total_rounds = st.number_input("총 라운드 수", 1, 10, 3)
    with col2:
        time_choice = st.selectbox("전체 제한 시간 (초)", [180, 120, 90, 60], index=1)
    with col3:
        difficulty = st.selectbox("AI 난이도", ["쉬움", "보통", "어려움"], index=1)

    if st.button("게임 입장하기"):
        words_data = load_word_data()
        idx = defaultdict(list)
        valid_words = []
        for w in words_data:
            if w and len(w) >= 2:
                idx[w[0]].append(w)
                valid_words.append(w)

        if not valid_words:
            valid_words = ["기차", "나무", "나비", "우주", "주스"]
            for w in valid_words:
                idx[w[0]].append(w)

        first = random.choice(valid_words)
        now = time.time()
        st.session_state.update(
            {
                "audio_enabled": True,
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
                "winner": None,
                "current_stage": "stage1",
                "bgm_started": False,
                "round_audio_started_for": 0,
                "pending_ai": False,
                "pending_ai_phase": 0,
                "pending_ai_due_at": 0.0,
                "pending_ai_candidates": [],
                "ticking": False,
            }
        )
        st.rerun()
    st.stop()


now = time.time()
bank_rem = max(0.0, st.session_state.total_limit - (now - st.session_state.game_start_time))
bank_ratio = bank_rem / st.session_state.total_limit

dynamic_limit, new_stage, new_bgm, new_sfx = get_stage(st.session_state.chain)
turn_elapsed = now - st.session_state.turn_start
actual_turn_rem = max(0.0, dynamic_limit - turn_elapsed)
actual_turn_ratio = actual_turn_rem / dynamic_limit
pending_ai = st.session_state.get("pending_ai", False)

prev_stage = st.session_state.get("current_stage", "stage1")

if st.session_state.get("round_audio_started_for", 0) != st.session_state.current_round:
    audio_stop_all()
    audio_delayed_event("stage_start", new_bgm, delay_ms=0)
    st.session_state.round_audio_started_for = st.session_state.current_round
    st.session_state.bgm_started = True
    st.session_state.current_stage = new_stage
elif prev_stage != new_stage:
    st.session_state.current_stage = new_stage

is_low_time = (not pending_ai) and actual_turn_rem <= 3.0 and actual_turn_rem > 0
if is_low_time and not st.session_state.get("ticking", False):
    audio_tick_start()
    st.session_state.ticking = True
elif not is_low_time and st.session_state.get("ticking", False):
    audio_tick_stop()
    st.session_state.ticking = False

st.session_state.bank_rem = bank_rem
st.session_state.actual_turn_rem = actual_turn_rem

# 라운드 종료 상태에서는 틱 사운드가 남지 않도록 강제 정지
if st.session_state.get("round_over", False):
    audio_stop_all()
    st.session_state.ticking = False
    st.session_state.bgm_started = False
    st.session_state.pending_ai = False
    st.session_state.pending_ai_phase = 0
    st.session_state.pending_ai_due_at = 0.0
    st.session_state.pending_ai_candidates = []


if not st.session_state.get("round_over", False):
    if bank_rem <= 0 or ((not pending_ai) and actual_turn_rem <= 0):
        audio_lose()
        st.session_state.round_over = True
        st.session_state.ai_score += 1
        st.session_state.end_reason = "timeout"
        st.session_state.winner = "AI"
        st.rerun()

    st.write(f"**라운드 {st.session_state.current_round} / {st.session_state.total_rounds}**")
    c1, c2 = st.columns(2)
    c1.metric("나 (User)", st.session_state.user_score)
    c2.metric("상대 (AI)", st.session_state.ai_score)

    starts = get_start_chars(st.session_state.last_word[-1])
    starts_display = " 또는 ".join(starts)
    st.markdown(
        f"""
        <div style="text-align:center; margin-top:10px; margin-bottom:15px;">
            <div style="display:inline-block;
                        background:linear-gradient(135deg,#FF0055,#7000FF);
                        color:white; padding:4px 15px; border-radius:20px;
                        font-weight:bold; font-size:1.1rem; margin-bottom:10px;
                        box-shadow:0 2px 5px rgba(0,0,0,0.2); border:1px solid #fff;">
                이은 단어 수: {st.session_state.chain} &nbsp;|&nbsp; {new_stage}
            </div>
            <div style="background:#fff; border:2px solid #8A2BE2; border-radius:12px;
                        padding:12px; box-shadow:inset 0 0 10px rgba(138,43,226,0.1);">
                <div style="color:#666; font-size:0.85rem; margin-bottom:3px;">다음 시작 글자</div>
                <div style="color:#FF0055; font-size:1.5rem; font-weight:900;
                            letter-spacing:2px;">{starts_display}</div>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    t_color = "#FF0055" if actual_turn_ratio < 0.3 else "#f1e05a"
    st.markdown(
        f"""
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
    """,
        unsafe_allow_html=True,
    )

    chat_html = '<div class="chat-wrap">'
    for speaker, text in st.session_state.get("history", []):
        side = "ai" if speaker == "AI" else "user"
        bub = "bubble-ai" if speaker == "AI" else "bubble-user"
        style = (
            "color:#FF0000;font-weight:bold;border:2px solid #FF0000;"
            "box-shadow:0 0 10px rgba(255,0,0,0.3);"
        ) if "🔥" in text else ""
        chat_html += (
            f'<div class="msg-row-{side}"><div class="{bub}" style="{style}">'
            f'{text.replace("🔥", "")}</div></div>'
        )
    chat_html += "</div>"
    st.markdown(chat_html, unsafe_allow_html=True)

    if st.session_state.get("pending_ai", False):
        due_at = st.session_state.get("pending_ai_due_at", 0.0)
        phase = st.session_state.get("pending_ai_phase", 0)
        if phase == 0:
            # 사용자 메시지가 단독으로 한 프레임은 보이도록 강제
            st.session_state.pending_ai_phase = 1
            st.info("AI가 생각 중...")
            st.rerun()
        elif time.time() < due_at:
            st.info("AI가 생각 중...")
        else:
            candidates = list(st.session_state.get("pending_ai_candidates", []))
            st.session_state.pending_ai = False
            st.session_state.pending_ai_phase = 0
            st.session_state.pending_ai_due_at = 0.0
            st.session_state.pending_ai_candidates = []

            if candidates:
                diff = st.session_state.get("difficulty", "보통")
                if diff == "쉬움":
                    ai_word = random.choice(candidates)
                elif diff == "보통":
                    candidates.sort(key=len)
                    mid = len(candidates) // 2
                    ai_word = random.choice(candidates[mid:] if mid > 0 else candidates)
                else:
                    ai_word = max(candidates, key=len)

                is_killer = True
                for nch in get_start_chars(ai_word[-1]):
                    if nch in st.session_state.index:
                        if any(
                            w not in st.session_state.used and w != ai_word
                            for w in st.session_state.index[nch]
                        ):
                            is_killer = False
                            break

                final_msg = f"🔥{ai_word}" if is_killer else ai_word
                next_ai_bgm = get_stage(st.session_state.chain + 1)[2]
                audio_stop_all()
                if is_killer:
                    audio_delayed_event("killer", next_ai_bgm, delay_ms=AUDIO_EVENT_DELAY_MS)
                else:
                    audio_delayed_event("input", next_ai_bgm, delay_ms=AUDIO_EVENT_DELAY_MS)

                st.session_state.used.add(ai_word)
                st.session_state.history.append(("AI", final_msg))
                st.session_state.last_word = ai_word
                st.session_state.chain += 1
                st.session_state.turn_start = time.time()
                st.session_state.ticking = False
            st.rerun()
    else:
        input_mount = st.empty()
        with input_mount.form(key="game_input", clear_on_submit=True):
            user_input = st.text_input(
                "단어 입력",
                key="word_input_main",
                label_visibility="collapsed",
                placeholder="단어를 입력해주세요...",
            )
            submit = st.form_submit_button("전송")

        if submit and user_input:
            # 전송 버튼 즉시: 현재 재생 중인 소리 전체 중단
            audio_stop_all()
            word = user_input.strip()

            if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                st.session_state.used.add(word)
                st.session_state.history.append(("User", word))
                st.session_state.chain += 1
                st.session_state.last_word = word
                st.session_state.ticking = False

                user_bgm = get_stage(st.session_state.chain)[2]
                audio_delayed_event("input", user_bgm, delay_ms=AUDIO_EVENT_DELAY_MS)

                candidates = []
                for ch in get_start_chars(word[-1]):
                    if ch in st.session_state.index:
                        candidates.extend(
                            w for w in st.session_state.index[ch] if w not in st.session_state.used
                        )

                diff = st.session_state.get("difficulty", "보통")
                give_up = 0.15 if diff == "쉬움" else 0.05 if diff == "보통" else 0
                if candidates and random.random() < give_up:
                    candidates = []

                if not candidates:
                    st.session_state.history[-1] = ("User", f"🔥{word}")
                    st.session_state.user_score += 1
                    audio_delayed_event("killer", "", delay_ms=AUDIO_EVENT_DELAY_MS)
                    audio_win()

                    if st.session_state.current_round >= st.session_state.total_rounds:
                        st.session_state.round_over = True
                        st.session_state.winner = "User"
                    else:
                        st.toast("🎊 AI 항복! 다음 라운드로 이동합니다.")
                        time.sleep(1.5)
                        new_f = random.choice(list(st.session_state.words))
                        now_res = time.time()
                        st.session_state.update(
                            {
                                "current_round": st.session_state.current_round + 1,
                                "game_start_time": now_res,
                                "turn_start": now_res,
                                "used": {new_f},
                                "last_word": new_f,
                                "history": [("AI", new_f)],
                                "chain": 1,
                                "current_stage": "stage1",
                                "bgm_started": False,
                                "round_audio_started_for": 0,
                                "pending_ai": False,
                                "pending_ai_phase": 0,
                                "pending_ai_due_at": 0.0,
                                "pending_ai_candidates": [],
                                "ticking": False,
                            }
                        )
                        audio_stop_all()
                    st.rerun()
                else:
                    delay = random.uniform(0.5, max(0.6, dynamic_limit * 0.4))
                    st.session_state.pending_ai = True
                    st.session_state.pending_ai_phase = 0
                    st.session_state.pending_ai_due_at = time.time() + delay
                    st.session_state.pending_ai_candidates = candidates
                    st.rerun()
            else:
                audio_delayed_event("fail", new_bgm, delay_ms=AUDIO_EVENT_DELAY_MS)
                st.toast("❌ 잘못되거나 이미 사용된 단어입니다!")
else:
    b_rem = st.session_state.get("bank_rem", 0)
    t_rem = st.session_state.get("actual_turn_rem", 0)
    reason = "시간 초과!" if (b_rem <= 0 or t_rem <= 0) else "AI의 역습!"
    st.error(f"💀 패배.. {reason}")
    c1, c2 = st.columns(2)
    c1.metric("최종 나 (User)", st.session_state.user_score)
    c2.metric("최종 상대 (AI)", st.session_state.ai_score)


if st.session_state.get("round_over", False):
    if st.session_state.current_round < st.session_state.total_rounds:
        if st.button(f"🕐 다음 라운드({st.session_state.current_round + 1}) 시작하기"):
            audio_stop_all()
            new_first = random.choice(list(st.session_state.words))
            now_reset = time.time()
            st.session_state.update(
                {
                    "round_over": False,
                    "winner": None,
                    "game_start_time": now_reset,
                    "turn_start": now_reset,
                    "used": {new_first},
                    "last_word": new_first,
                    "history": [("AI", new_first)],
                    "chain": 1,
                    "current_round": st.session_state.current_round + 1,
                    "current_stage": "stage1",
                    "bgm_started": False,
                    "round_audio_started_for": 0,
                    "pending_ai": False,
                    "pending_ai_phase": 0,
                    "pending_ai_due_at": 0.0,
                    "pending_ai_candidates": [],
                    "ticking": False,
                }
            )
            st.rerun()
    else:
        st.warning("🎮 모든 라운드가 종료되었습니다!")
        if st.button("🔄 게임 초기화 및 처음부터 다시 시작", key="final_restart"):
            audio_stop_all()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


if not st.session_state.get("round_over", False):
    time.sleep(0.1)
    components.html(
        """
<script>
(function(){
    const p = window.parent;
    const d = p.document;
    const fixUI = () => {
        const chat = d.querySelector('.chat-wrap');
        const input = d.querySelector('input[aria-label="단어 입력"]');
        if (chat) chat.scrollTop = chat.scrollHeight;
        if (input && d.activeElement.tagName !== 'INPUT' && d.activeElement.tagName !== 'TEXTAREA') input.focus();
    };
    if (!p.__kkutuUiFixBound) {
        p.__kkutuUiFixBound = true;
        const obs = new MutationObserver(fixUI);
        obs.observe(d.body, { childList:true, subtree:true });
        p.__kkutuUiFixInterval = setInterval(fixUI, 400);
    }
    fixUI();
})();
</script>
""",
        height=0,
    )
    st.rerun()
