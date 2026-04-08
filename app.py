import random
import time
import re
import base64
from collections import defaultdict

import streamlit as st
import streamlit.components.v1 as components


def load_b64(filepath: str) -> str:
    try:
        with open(filepath, "rb") as f:
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
  if (p.__kkutuAudio) return;

  p.__kkutuAudio = {
    bgm: null,
    bgmFading: false,
    tickInterval: null,
    lastTickTime: 0,

    _ctx: null,
    unlock: function() {
      if (p.__audioUnlocked) return;
      try {
        this._ctx = new (p.AudioContext || p.webkitAudioContext)();
        var buf = this._ctx.createBuffer(1,1,22050);
        var src = this._ctx.createBufferSource();
        src.buffer = buf;
        src.connect(this._ctx.destination);
        src.start(0);
        p.__audioUnlocked = true;
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

    playBGM: function(b64, vol, fadeMs) {
      var self = this;
      vol = vol || 0.4;
      fadeMs = fadeMs || 800;

      function startNew() {
        if (!b64) return;
        var a = new p.Audio('data:audio/mp3;base64,' + b64);
        a.loop = true;
        a.volume = 0;
        a.play().catch(function(){});
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
        a.play().catch(function(){});
      }
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
    }
  };

  p.document.addEventListener('click', function(){
    p.__kkutuAudio.unlock();
  });
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


def audio_stage_up(sfx_file: str, bgm_file: str, fade_ms: int = 800):
    sfx_b64 = load_b64(sfx_file)
    bgm_b64 = load_b64(bgm_file)
    _js(
        f"""
      am.sfxStageUp('{sfx_b64}');
      setTimeout(function(){{ am.playBGM('{bgm_b64}', 0.4, {fade_ms}); }}, 800);
    """
    )


def audio_input(sfx_file: str = "static/sfx_input.mp3"):
    _js(f"am.sfxInput('{load_b64(sfx_file)}');")


def audio_fail(sfx_file: str = "static/sfx_fail.mp3"):
    _js(f"am.sfxFail('{load_b64(sfx_file)}');")


def audio_killer(sfx_file: str = "static/sfx_killer.mp3"):
    _js(f"am.sfxKiller('{load_b64(sfx_file)}');")


def audio_win(sfx_file: str = "static/sfx_win.mp3"):
    _js(f"am.stopTick(); am.stopBGM(300); am.sfxWin('{load_b64(sfx_file)}');")


def audio_lose(sfx_file: str = "static/sfx_lose.mp3"):
    _js(f"am.stopTick(); am.stopBGM(300); am.sfxLose('{load_b64(sfx_file)}');")


def audio_tick_start(sfx_file: str = "static/sfx_tick.mp3"):
    _js(f"am.startTick('{load_b64(sfx_file)}');")


def audio_tick_stop():
    _js("am.stopTick();")


STAGES = [
    (35, 2.0, "stage5", "static/bgm5.mp3", "static/stage5_up.mp3"),
    (28, 5.0, "stage4", "static/bgm4.mp3", "static/stage4_up.mp3"),
    (18, 8.0, "stage3", "static/bgm3.mp3", "static/stage3_up.mp3"),
    (8, 12.0, "stage2", "static/bgm2.mp3", "static/stage2_up.mp3"),
    (0, 15.0, "stage1", "static/bgm1.mp3", ""),
]


def get_stage(chain: int):
    for min_chain, limit, name, bgm, sfx in STAGES:
        if chain >= min_chain:
            return limit, name, bgm, sfx
    return 15.0, "stage1", "static/bgm1.mp3", ""


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

prev_stage = st.session_state.get("current_stage", "stage1")

if not st.session_state.get("bgm_started", False):
    audio_play_bgm(new_bgm, fade_ms=1000)
    st.session_state.bgm_started = True
    st.session_state.current_stage = new_stage
elif prev_stage != new_stage:
    audio_stage_up(new_sfx, new_bgm)
    st.session_state.current_stage = new_stage

is_low_time = actual_turn_rem <= 3.0 and actual_turn_rem > 0
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
    audio_tick_stop()
    st.session_state.ticking = False


if not st.session_state.get("round_over", False):
    if bank_rem <= 0 or actual_turn_rem <= 0:
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

    with st.form(key="game_input", clear_on_submit=True):
        user_input = st.text_input(
            "단어 입력",
            label_visibility="collapsed",
            placeholder="단어를 입력해주세요...",
        )
        submit = st.form_submit_button("전송")

        if submit and user_input:
            word = user_input.strip()

            if word in st.session_state.words and word not in st.session_state.used and word[0] in starts:
                st.session_state.used.add(word)
                st.session_state.history.append(("User", word))
                st.session_state.chain += 1
                st.session_state.last_word = word
                st.session_state.ticking = False

                audio_input()
                audio_tick_stop()

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
                    audio_killer()
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
                                "ticking": False,
                            }
                        )
                    st.rerun()
                else:
                    delay = random.uniform(0.5, max(0.6, dynamic_limit * 0.4))
                    with st.spinner("AI가 생각 중..."):
                        time.sleep(delay)

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
                    if is_killer:
                        audio_killer()

                    st.session_state.used.add(ai_word)
                    st.session_state.history.append(("AI", final_msg))
                    st.session_state.last_word = ai_word
                    st.session_state.chain += 1
                    st.session_state.turn_start = time.time()
                    st.session_state.ticking = False
                    st.rerun()
            else:
                audio_fail()
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
                    "ticking": False,
                }
            )
            st.rerun()
    else:
        st.warning("🎮 모든 라운드가 종료되었습니다!")
        if st.button("🔄 게임 초기화 및 처음부터 다시 시작", key="final_restart"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


if not st.session_state.get("round_over", False):
    time.sleep(0.1)
    components.html(
        """
<script>
const fixUI = () => {
    const win = window.parent.document;
    const chat = win.querySelector('.chat-wrap');
    const input = win.querySelector('input');
    if (chat) chat.scrollTop = chat.scrollHeight;
    if (input && win.activeElement.tagName !== 'INPUT'
              && win.activeElement.tagName !== 'TEXTAREA') input.focus();
};
const obs = new MutationObserver(fixUI);
obs.observe(window.parent.document.body, { childList:true, subtree:true });
setInterval(fixUI, 400);
fixUI();
</script>
""",
        height=0,
    )
    st.rerun()
