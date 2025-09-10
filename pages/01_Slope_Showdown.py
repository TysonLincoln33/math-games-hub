
# Slope Showdown – Graphs Only + Progress Logging + HUD + Auto-End @10
# v3.2: Tutorial Zero color fix (snapping tolerance) + category chips; keeps CSV-flex loader.
# Run: streamlit run slope_showdown_graphs_progress_v3_zeroFix.py

import streamlit as st
import numpy as np
import random
from io import BytesIO
import matplotlib.pyplot as plt
from datetime import datetime
import os, csv, threading, uuid
import pandas as pd

st.set_page_config(page_title="Slope Showdown – Graphs Only", page_icon="📈", layout="centered")

# ---------------- Config ----------------
SLOPE_TYPES = ["Positive", "Negative", "Zero", "Undefined"]
STATE_COLORS = {"Positive":"#22c55e","Negative":"#ef4444","Zero":"#3b82f6","Undefined":"#a855f7"}
NUM_QUESTIONS = 15
PROGRESS_CSV = "slope_showdown_progress.csv"     # per-question log
SUMMARY_CSV  = "slope_showdown_results.csv"      # final summary per game
MIN_SCORE_TO_WIN = 10                             # auto-end threshold
DEFAULT_PERIODS = ["1","2","3","4","5","6","7","8","9","Other…"]
_lock = threading.Lock()

# ---------------- Styling ----------------
st.markdown("""
<style>
.big {font-size:2rem;font-weight:800;margin:.2rem 0;}
.sub {color:#555;margin-bottom:.6rem;}
.card {background:#fff;border:1px solid #eee;border-radius:18px;padding:1rem 1.2rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);}
.choice {padding:.75rem 1rem;border-radius:12px;border:1px solid #e5e7eb;margin:.35rem 0;font-weight:600;}
.choice:hover {background:#f9fafb;border-color:#d1d5db;}
.choice.selected {background:#e0f2fe;border-color:#bae6fd;}
.choice.correct {background:#e8f5e9;border-color:#c8e6c9;}
.choice.incorrect {background:#ffebee;border-color:#ffcdd2;}
.hud {border-radius:16px; padding:.75rem 1rem; border:2px solid var(--hud-color); background:var(--hud-bg); display:flex; align-items:center; gap:14px; margin:.25rem 0 1rem 0;}
.hud .score {font-size:2.2rem; font-weight:900; color:var(--hud-color); line-height:1;}
.hud .label {font-weight:700; color:#111;}
.hud .meta {margin-left:auto; color:#444; font-weight:600;}
.badge {display:inline-block;padding:.3rem .6rem;border-radius:999px;color:#fff;font-weight:700;margin:.2rem .35rem 0 0;}
.small {color:#666;font-size:.92rem}
</style>
""", unsafe_allow_html=True)

def chip(text, ok=True):
    bg = "#e8f5e9" if ok else "#ffebee"
    bd = "#c8e6c9" if ok else "#ffcdd2"
    fg = "#2e7d32" if ok else "#c62828"
    st.markdown(f"<div style='display:inline-block;background:{bg};border:1px solid {bd};color:{fg};padding:.25rem .55rem;border-radius:999px;font-size:.9rem;margin:.2rem 0'>{text}</div>", unsafe_allow_html=True)

def hud():
    score = st.session_state.score
    streak = st.session_state.streak
    best   = st.session_state.best_streak
    i      = st.session_state.index + 1
    total  = len(st.session_state.questions)
    color  = "#22c55e" if score >= MIN_SCORE_TO_WIN else ("#2563eb" if score > 0 else ("#ef4444" if score < 0 else "#6b7280"))
    bg     = "rgba(34,197,94,.08)" if score >= MIN_SCORE_TO_WIN else "rgba(37,99,235,.07)" if score>0 else "rgba(239,68,68,.07)" if score<0 else "rgba(107,114,128,.07)"
    st.markdown(f"""
<div class="hud" style="--hud-color:{color}; --hud-bg:{bg}">
  <div class="score">{score}</div>
  <div class="label">points</div>
  <div class="meta">Q {i}/{total} • Streak {streak} (best {best})</div>
</div>
""", unsafe_allow_html=True)

# ---------------- Logging Helpers ----------------
def _append_row(path, header, row):
    file_exists = os.path.exists(path)
    with _lock:
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(header)
            w.writerow(row)

def log_progress(session_id, name, class_period, q_index, total, choice, answer, correct, score_after, streak_after, best_streak):
    _append_row(
        PROGRESS_CSV,
        ["timestamp","session_id","name","class_period","q_index","total_questions","choice","answer","correct","score_after","streak_after","best_streak"],
        [datetime.now().isoformat(timespec="seconds"), session_id, name, class_period, q_index, total, choice, answer, int(correct), score_after, streak_after, best_streak],
    )

def log_summary(session_id, name, class_period, score, best_streak, total, won):
    _append_row(
        SUMMARY_CSV,
        ["timestamp","session_id","name","class_period","score","best_streak","total_questions","won"],
        [datetime.now().isoformat(timespec="seconds"), session_id, name, class_period, score, best_streak, total, int(won)],
    )

# ---------------- Robust CSV loaders ----------------
PROGRESS_COLS = ["timestamp","session_id","name","class_period","q_index","total_questions","choice","answer","correct","score_after","streak_after","best_streak"]
PROGRESS_OLD_COLS = ["timestamp","session_id","name","q_index","total_questions","choice","answer","correct","score_after","streak_after","best_streak"]
SUMMARY_COLS = ["timestamp","session_id","name","class_period","score","best_streak","total_questions","won"]
SUMMARY_OLD_COLS = ["timestamp","session_id","name","score","best_streak","total_questions","won"]

def load_csv_flex(path, cols, old_cols, insert_index=3, fill_value="unknown"):
    if not os.path.exists(path): return None
    try:
        df = pd.read_csv(path, dtype=str)
        if all(c in df.columns for c in cols): return df[cols]
        if all(c in df.columns for c in old_cols):
            df.insert(insert_index, cols[insert_index], fill_value)
            return df[cols]
        raise ValueError("Mismatched columns")
    except Exception:
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) == len(cols)-1: row.insert(insert_index, fill_value)
                elif len(row) > len(cols): row = row[:len(cols)]
                elif len(row) < len(cols): row += [""]*(len(cols)-len(row))
                rows.append(row)
        return pd.DataFrame(rows, columns=cols)

# ---------------- Graph Generator ----------------
def generate_graph_question():
    x = np.linspace(-6, 6, 50)
    kind = random.choice(SLOPE_TYPES)
    if kind == "Undefined":
        k = random.randint(-4,4)
        fig, ax = plt.subplots(figsize=(4,4)); ax.plot([k,k],[-6,6],linewidth=3); answer="Undefined"
    elif kind == "Zero":
        b = random.randint(-4,4)
        fig, ax = plt.subplots(figsize=(4,4)); ax.plot(x, np.full_like(x,b), linewidth=3); answer="Zero"
    else:
        m = random.choice([1,2,3,0.5,2/3,1.5]); m = m if kind=="Positive" else -m
        b = random.randint(-2,2)
        fig, ax = plt.subplots(figsize=(4,4)); ax.plot(x, m*x+b, linewidth=3); answer= "Positive" if m>0 else "Negative"
    ax.set_xlim(-6,6); ax.set_ylim(-6,6)
    ax.axhline(0,color='black',linewidth=1); ax.axvline(0,color='black',linewidth=1)
    ax.set_xticks(range(-6,7,2)); ax.set_yticks(range(-6,7,2))
    ax.grid(True, alpha=0.3)
    buf = BytesIO(); plt.tight_layout(); fig.savefig(buf, format="png", dpi=180); plt.close(fig)
    return {"image": buf.getvalue(), "answer": answer, "choices": SLOPE_TYPES}

def build_graph_set(n=NUM_QUESTIONS, seed=None):
    if seed is not None:
        random.seed(seed); np.random.seed(seed % (2**32-1))
    return [generate_graph_question() for _ in range(n)]

# ---------------- State ----------------
def reset_game():
    st.session_state.questions   = build_graph_set()
    st.session_state.index       = 0
    st.session_state.score       = 0
    st.session_state.answered    = False
    st.session_state.selected    = None
    st.session_state.streak      = 0
    st.session_state.best_streak = 0
    st.session_state.auto_finished = False
    st.session_state.summary_logged = False

def init_state():
    st.session_state.stage = "tutorial"
    st.session_state.name  = ""
    st.session_state.class_period = ""
    st.session_state.session_id = ""
    reset_game()

if "stage" not in st.session_state:
    init_state()

# ---------------- Sidebar ----------------
stage_to_tab = {"tutorial":0, "signin":1, "game":1, "results":2}
with st.sidebar:
    st.header("Menu")
    tab_idx = stage_to_tab.get(st.session_state.stage, 0)
    dest = st.radio("Go to:", ["Tutorial","Play","Results"], index=tab_idx, key="nav")
    if dest == "Tutorial" and st.session_state.stage != "tutorial":
        st.session_state.stage = "tutorial"; st.rerun()
    elif dest == "Play" and st.session_state.stage not in ["signin","game"]:
        st.session_state.stage = "signin" if not st.session_state.get("name") else "game"; st.rerun()
    elif dest == "Results" and st.session_state.stage != "results":
        st.session_state.stage = "results"; st.rerun()

st.markdown("<div class='big'>📈 Slope Showdown</div>", unsafe_allow_html=True)

# ---------------- Tutorial (with tolerant snapping + chips) ----------------
if st.session_state.stage == "tutorial":
    st.markdown("<div class='sub'>Drag on the line to rotate it. Colors show: Positive (green), Negative (red), Zero (blue), Undefined (purple). Snaps within ±5° of horizontal/vertical.</div>", unsafe_allow_html=True)
    html = """
    <div style="display:flex;flex-direction:column;align-items:flex-start">
      <canvas id="c" width="560" height="420" style="border:1px solid #d9d9d9;border-radius:16px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,0.05)"></canvas>
      <div id="label" style="margin-top:10px;font-family:system-ui,Segoe UI,Roboto,Arial;font-size:14px;"></div>
      <div style="margin-top:6px">
        <span class="badge" style="background:__POS__">Positive</span>
        <span class="badge" style="background:__NEG__">Negative</span>
        <span class="badge" style="background:__ZERO__">Zero</span>
        <span class="badge" style="background:__UNDEF__">Undefined</span>
      </div>
    </div>
    <script>
      (function(){ function ready(fn){ if(document.readyState!='loading'){ fn(); } else { document.addEventListener('DOMContentLoaded', fn);}}
        ready(function(){
          const c=document.getElementById('c'); if(!c) return; const g=c.getContext('2d'); let a=Math.PI/8, drag=false;
          const COLORS={Positive:'__POS__',Negative:'__NEG__',Zero:'__ZERO__',Undefined:'__UNDEF__'};
          const EPS = Math.PI/36; // ~5 degrees snapping
          function state(){
            const absSin=Math.abs(Math.sin(a));
            const absCos=Math.abs(Math.cos(a));
            if (absCos < EPS) return ['Undefined', COLORS.Undefined];   // near vertical
            if (absSin < EPS) return ['Zero', COLORS.Zero];             // near horizontal
            return Math.tan(a) > 0 ? ['Positive', COLORS.Positive] : ['Negative', COLORS.Negative];
          }
          function draw(){
            g.clearRect(0,0,c.width,c.height);
            g.strokeStyle='rgba(0,0,0,0.10)'; g.lineWidth=1;
            for(let x=0;x<=c.width;x+=70){g.beginPath();g.moveTo(x,0);g.lineTo(x,c.height);g.stroke();}
            for(let y=0;y<=c.height;y+=70){g.beginPath();g.moveTo(0,y);g.lineTo(c.width,y);g.stroke();}
            g.strokeStyle='#444'; g.lineWidth=1.2;
            g.beginPath();g.moveTo(0,c.height/2);g.lineTo(c.width,c.height/2);g.stroke();
            g.beginPath();g.moveTo(c.width/2,0);g.lineTo(c.width/2,c.height);g.stroke();
            const [label,color]=state();
            const cx=c.width/2, cy=c.height/2, dx=Math.cos(a), dy=Math.sin(a), L=Math.max(c.width,c.height);
            g.strokeStyle=color; g.lineWidth=5;
            g.beginPath(); g.moveTo(cx-dx*L, cy+dy*L); g.lineTo(cx+dx*L, cy-dy*L); g.stroke();
            g.fillStyle=color; g.beginPath(); g.arc(cx+dx*120, cy-dy*120, 8, 0, Math.PI*2); g.fill();
            const badge=document.getElementById('label');
            if(badge){ const deg=((Math.round(a*180/Math.PI)%360)+360)%360;
              badge.innerHTML='<span class="badge" style="background:'+color+'">Current: '+label+'</span>' +
                              '<span style="color:#666;margin-left:10px">Angle '+deg+'°</span>'; }
          }
          function setAngle(e){ const r=c.getBoundingClientRect(); const mx=e.clientX-r.left, my=e.clientY-r.top; const cx=c.width/2, cy=c.height/2; a=Math.atan2(cy-my, mx-cx); }
          c.addEventListener('mousedown',e=>{drag=true;setAngle(e);draw();});
          c.addEventListener('mousemove',e=>{if(drag){setAngle(e);draw();}});
          window.addEventListener('mouseup',()=>{drag=false;});
          draw();
        }); })();
    </script>
    """
    html = (html.replace("__POS__", STATE_COLORS["Positive"])
                .replace("__NEG__", STATE_COLORS["Negative"])
                .replace("__ZERO__", STATE_COLORS["Zero"])
                .replace("__UNDEF__", STATE_COLORS["Undefined"]))
    st.components.v1.html(html, height=560)
    if st.button("Got it — Let’s Play →", type="primary"):
        st.session_state.stage = "signin"; st.rerun()

# ---------------- Sign-in (with Class Period) ----------------
elif st.session_state.stage == "signin":
    with st.form("signin"):
        name = st.text_input("Enter your name:", max_chars=40, placeholder="First & Last")
        period_choice = st.selectbox("Class Period:", DEFAULT_PERIODS, index=0)
        custom_period = ""
        if period_choice == "Other…":
            custom_period = st.text_input("Enter period / class (e.g., 'Advisory' or 'A2'):", max_chars=20)
        go = st.form_submit_button("Start Game →")
        if go:
            period_final = custom_period.strip() if period_choice == "Other…" else period_choice
            if not name.strip() or not period_final:
                st.warning("Please enter both your name and class period.")
            else:
                st.session_state.name = name.strip()
                st.session_state.class_period = period_final
                st.session_state.session_id = uuid.uuid4().hex[:12]
                reset_game()
                st.session_state.stage = "game"; st.rerun()

# ---------------- Game (unchanged from v3.1) ----------------
elif st.session_state.stage == "game":
    name = st.session_state.name or "Anon"
    sid  = st.session_state.session_id or "na"
    period = st.session_state.class_period or "unknown"
    qs   = st.session_state.questions
    i    = st.session_state.index
    score = st.session_state.score
    total = len(qs)

    st.caption(f"Player: **{name}** | Period: **{period}** | Session: {sid}")
    try:
        st.progress((i)/total if total>0 else 0.0, text=f"Q: {i}/{total}   |   Score: {score}   |   Streak: {st.session_state.streak} (Best: {st.session_state.best_streak})")
    except TypeError:
        st.progress((i)/total if total>0 else 0.0)

    hud()

    if i < total:
        q = qs[i]
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.image(q["image"], caption="What slope type is shown?", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        selected = st.radio("Pick one:", q["choices"], index=None, key=f"radio_{i}")
        st.session_state.selected = selected

        if st.button("Submit", type="primary"):
            if st.session_state.answered:
                st.stop()
            st.session_state.answered = True

            correct = (selected == q["answer"])
            if correct:
                st.session_state.streak += 1
                delta = int(round(1.5 * st.session_state.streak))
                st.session_state.score += delta
                st.session_state.best_streak = max(st.session_state.best_streak, st.session_state.streak)
                st.session_state.last_delta = delta
            else:
                st.session_state.streak = 0
                st.session_state.score -= 1
                st.session_state.last_delta = -1

            log_progress(
                sid, name, period, i+1, total,
                selected if selected is not None else "",
                q["answer"],
                int(correct),
                st.session_state.score,
                st.session_state.streak,
                st.session_state.best_streak,
            )

            if st.session_state.score >= MIN_SCORE_TO_WIN:
                st.session_state.auto_finished = True
                if not st.session_state.summary_logged:
                    log_summary(sid, name, period, st.session_state.score, st.session_state.best_streak, total, True)
                    st.session_state.summary_logged = True
                st.session_state.stage = "results"
                st.rerun()

        cols = st.columns(2)
        for idx, choice in enumerate(q["choices"]):
            css = "choice"
            if st.session_state.get("answered"):
                if choice == q["answer"]:
                    css += " correct"
                elif st.session_state.get("selected") == choice:
                    css += " incorrect"
            else:
                if st.session_state.get("selected") == choice:
                    css += " selected"
            with cols[idx % 2]:
                st.markdown(f"<div class='{css}'>{choice}</div>", unsafe_allow_html=True)

        if st.session_state.get("answered"):
            if st.session_state.selected == q["answer"]:
                chip(f"Correct! +{st.session_state.last_delta} (streak x{st.session_state.streak})", ok=True)
            else:
                chip("Incorrect. -1 point. Streak reset.", ok=False)
            if st.button("Next →", type="primary"):
                st.session_state.index += 1
                st.session_state.answered = False
                st.session_state.selected = None
                st.rerun()
    else:
        won = (score >= MIN_SCORE_TO_WIN)
        if not st.session_state.summary_logged:
            log_summary(st.session_state.session_id or "na", name, period, score, st.session_state.best_streak, total, won)
            st.session_state.summary_logged = True

        st.success("🎉 Finished!")
        st.metric("Final Score", f"{score} / {total} (best streak: {st.session_state.best_streak})")
        if won: chip(f"✅ Reached {MIN_SCORE_TO_WIN} points! Game complete.", ok=True)
        else: chip(f"Game complete. You need {MIN_SCORE_TO_WIN}+ to auto-finish.", ok=False)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Play Again", use_container_width=True):
                reset_game(); st.rerun()
        with c2:
            if st.button("View Results", use_container_width=True):
                st.session_state.stage = "results"; st.rerun()

# ---------------- Results (same as v3.1) ----------------
elif st.session_state.stage == "results":
    st.markdown("### 📊 Live Results")
    dfp = load_csv_flex(PROGRESS_CSV, PROGRESS_COLS, PROGRESS_OLD_COLS, insert_index=3, fill_value="unknown")
    if dfp is not None and not dfp.empty:
        cols = st.columns(3)
        with cols[0]:
            name_filter = st.text_input("Filter by name:", value="")
        with cols[1]:
            periods = ["(all)"] + sorted(dfp["class_period"].dropna().unique().tolist())
            period_filter = st.selectbox("Class Period filter:", periods, index=0)
        with cols[2]:
            st.write("")
        if name_filter.strip():
            dfp = dfp[dfp["name"].str.contains(name_filter.strip(), case=False, na=False)]
        if period_filter != "(all)":
            dfp = dfp[dfp["class_period"] == period_filter]
        st.write("Most recent 100 submissions:")
        st.dataframe(dfp.tail(100), use_container_width=True, hide_index=True)
        st.download_button("Download progress CSV", data=dfp.to_csv(index=False), file_name=PROGRESS_CSV, mime="text/csv")
    else:
        st.info("No question submissions logged yet.")

    st.markdown("### 🧾 Game Summaries")
    dfs = load_csv_flex(SUMMARY_CSV, SUMMARY_COLS, SUMMARY_OLD_COLS, insert_index=3, fill_value="unknown")
    if dfs is not None and not dfs.empty:
        periods2 = ["(all)"] + sorted(dfs["class_period"].dropna().unique().tolist())
        period_filter2 = st.selectbox("Summary period filter:", periods2, index=0)
        if period_filter2 != "(all)":
            dfs = dfs[dfs["class_period"] == period_filter2]
        st.dataframe(dfs, use_container_width=True, hide_index=True)
        st.download_button("Download summary CSV", data=dfs.to_csv(index=False), file_name=SUMMARY_CSV, mime="text/csv")
        st.write(f"Total games: **{len(dfs)}**, Winners (score ≥ {MIN_SCORE_TO_WIN}): **{int(pd.to_numeric(dfs['won'], errors='coerce').fillna(0).astype(int).sum())}**")
    else:
        st.info("No completed games yet.")
    if st.button("Back to Play"):
        st.session_state.stage = "signin" if not st.session_state.get("name") else "game"; st.rerun()
