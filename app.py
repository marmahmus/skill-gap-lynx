"""Skill Gap Lynx: AI-powered resume screening and live voice interview.

A single-page Streamlit app that:
  1. Extracts text from an uploaded PDF resume.
  2. Analyses it against a job description (match %, skills, roadmap).
  3. Suggests YouTube learning resources for missing skills.
  4. Runs a personalised, bilingual voice/text mock interview with scoring.
"""
import base64
import hashlib
import io
import time

import gtts
import streamlit as st
import streamlit.components.v1 as components
from modules.voice_player import player_html
from modules.resume_reader import read_resume
from streamlit_mic_recorder import mic_recorder

from modules import config
from modules.groq_analyzer import analyze_profile
from modules.interview import (
    evaluate_answer,
    generate_final_report,
    generate_questions,
    transcribe_answer,
)
from modules.youtube import get_learning_videos

# --------------------------------------------------------------------------
# Page setup & styling
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Skill Gap Lynx",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, .stTextArea, .stButton {
    font-family: 'Inter', sans-serif !important;
}
.stApp {
    background:
        radial-gradient(1200px 600px at 15% -10%, rgba(139,92,246,.18), transparent 60%),
        radial-gradient(1000px 500px at 100% 0%, rgba(6,182,212,.14), transparent 55%),
        #0b0b17;
}
.block-container { padding-top: 1rem; max-width: 1180px; }

/* Hero */
.hero { text-align:center; margin: 0 0 .6rem; }
.hero h1 {
    font-size: 2.1rem; font-weight: 800; margin: 0; line-height: 1.1;
    background: linear-gradient(120deg,#a78bfa 0%,#8b5cf6 35%,#06b6d4 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.hero p { color:#a5a5c0; font-size:.92rem; margin:.3rem 0 0; }
.pill-row { display:flex; gap:.4rem; justify-content:center; flex-wrap:wrap; margin-top:.6rem; }
.pill { font-size:.72rem; color:#c4b5fd; background:rgba(139,92,246,.12);
        border:1px solid rgba(139,92,246,.35); padding:.22rem .65rem; border-radius:999px; }

/* Glass cards */
.card {
    background: rgba(255,255,255,.035);
    border: 1px solid rgba(139,92,246,.18);
    border-radius: 16px; padding: 1.3rem 1.4rem; margin-bottom: 1rem;
    backdrop-filter: blur(8px); box-shadow: 0 8px 30px rgba(0,0,0,.25);
}
.section-title { font-size:1rem; font-weight:700; color:#e9e9f5; margin:0 0 .15rem; }
.section-sub  { font-size:.82rem; color:#9494b0; margin:0 0 .6rem; }

/* Score */
.score-wrap { display:flex; align-items:center; gap:1.2rem; }
.score-num { font-size:3.1rem; font-weight:800; line-height:1; }
.score-track { flex:1; height:16px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; }
.score-fill { height:100%; border-radius:999px; transition:width .6s ease; }
.score-label { font-size:.8rem; color:#9494b0; text-transform:uppercase; letter-spacing:.06em; }

/* Chips */
.chips { display:flex; flex-wrap:wrap; gap:.45rem; }
.chip { font-size:.82rem; padding:.34rem .75rem; border-radius:999px; font-weight:500; }
.chip.good { color:#86efac; background:rgba(34,197,94,.12); border:1px solid rgba(34,197,94,.35); }
.chip.miss { color:#fcd34d; background:rgba(245,158,11,.12); border:1px solid rgba(245,158,11,.35); }
.muted { color:#77778f; font-size:.9rem; }

/* Roadmap */
.road { display:flex; gap:.7rem; align-items:flex-start; padding:.7rem 0; border-bottom:1px solid rgba(255,255,255,.06); }
.road:last-child { border-bottom:none; }
.badge { font-size:.68rem; font-weight:700; padding:.2rem .55rem; border-radius:6px; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; }
.badge.high { color:#fca5a5; background:rgba(239,68,68,.14); border:1px solid rgba(239,68,68,.4); }
.badge.medium { color:#fcd34d; background:rgba(245,158,11,.14); border:1px solid rgba(245,158,11,.4); }
.badge.low { color:#86efac; background:rgba(34,197,94,.14); border:1px solid rgba(34,197,94,.4); }
.road b { color:#e9e9f5; } .road span.act { color:#a5a5c0; font-size:.9rem; }

/* Interview */
.q-bubble { background:linear-gradient(135deg, rgba(139,92,246,.16), rgba(6,182,212,.10));
    border:1px solid rgba(139,92,246,.3); border-radius:14px; padding:1.1rem 1.3rem; font-size:1.08rem;
    color:#f0f0fa; line-height:1.5; }
.q-label { font-size:.7rem; text-transform:uppercase; letter-spacing:.08em; color:#a5a5c0; display:block; margin-bottom:.35rem; }
.rec-badge { display:inline-block; font-size:1rem; font-weight:700; padding:.5rem 1.1rem; border-radius:10px; }
.eval-row { padding:.6rem 0; border-bottom:1px solid rgba(255,255,255,.06); }

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg,#6366f1,#8b5cf6) !important; color:#fff !important;
    font-weight:600; border:none; border-radius:10px; height:3rem; width:100%;
    transition: transform .15s ease, box-shadow .15s ease;
}
.stButton>button:hover { transform: translateY(-1px); box-shadow:0 8px 22px rgba(139,92,246,.35); }
#MainMenu, footer, header { visibility:hidden; }

/* Step 1 input cards */
.step-badge { display:inline-flex; align-items:center; justify-content:center; width:24px; height:24px;
    border-radius:50%; background:linear-gradient(135deg,#8b5cf6,#6366f1); color:#fff; font-weight:700;
    font-size:.75rem; margin-right:.5rem; vertical-align:middle; }
.input-card-header { display:flex; align-items:flex-start; gap:.55rem; margin-bottom:.55rem; }
.input-card-icon { font-size:1.3rem; line-height:1; margin-top:.05rem; }
.input-card-title { font-weight:700; color:#e9e9f5; font-size:.95rem; margin:0; }
.input-card-sub { font-size:.75rem; color:#9494b0; margin:.1rem 0 0; line-height:1.35; }
.char-count { text-align:right; font-size:.7rem; color:#77778f; margin-top:.25rem; }

/* Equal-height side-by-side cards for Step 1. */
div[data-testid="stHorizontalBlock"] { align-items: stretch; }
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { display:flex; }
div[data-testid="stVerticalBlockBorderWrapper"] {
    height:100%; min-height: 190px; display:flex; flex-direction:column;
    border-color: rgba(139,92,246,.22) !important;
    background: rgba(255,255,255,.02) !important;
    border-radius: 14px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    flex:1; display:flex; flex-direction:column; height:100%; padding:.85rem 1rem !important;
}
/* Stretch the uploader/textarea container to fill the card, no gap below it. */
div[data-testid="stVerticalBlockBorderWrapper"] > div > div.element-container:has([data-testid="stFileUploader"]),
div[data-testid="stVerticalBlockBorderWrapper"] > div > div.element-container:has([data-testid="stTextArea"]) {
    flex:1; display:flex; flex-direction:column;
}
[data-testid="stFileUploader"] { flex:1; display:flex; flex-direction:column; }
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section { flex:1; }
[data-testid="stTextArea"] { flex:1; display:flex; flex-direction:column; }
[data-testid="stTextArea"] textarea { flex:1 !important; height:100% !important; min-height:60px !important; }

/* Compact resume input; content can grow without an inner scrollbar. */
.st-key-resume_input_card .input-card-header { margin-bottom:.75rem; }
.st-key-resume_input_card [data-testid="stVerticalBlock"] { gap:.35rem !important; }
.st-key-resume_input_card [data-testid="stFileUploader"] { flex:initial; }
.st-key-resume_input_card [data-testid="stFileUploaderDropzone"],
.st-key-resume_input_card [data-testid="stFileUploader"] section {
    flex:initial; min-height:0; padding:.65rem .85rem !important; gap:.5rem;
}
.st-key-resume_input_card [data-testid="stFileUploaderFile"] { padding:.25rem 0 !important; margin:0 !important; }
.resume-loaded { margin-bottom:16px; width:100%; min-height:52px; padding:12px 16px; display:flex; align-items:center; justify-content:center; text-align:center; background:rgba(34,197,94,.2); color:#4ade80; border-radius:8px; font-size:.8rem; line-height:1.4; }
.st-key-resume_input_card [data-testid="stAlert"] { padding:.55rem .65rem !important; display:flex; align-items:center; justify-content:center; }
.st-key-resume_input_card [data-testid="stAlert"] p { margin:0 !important; padding:0 !important; font-size:.8rem; line-height:1.4; text-align:center; }
.st-key-resume_input_card [data-testid="stAlert"] [data-testid="stMarkdownContainer"] { width:100%; margin:0 !important; padding:0 !important; }
.st-key-resume_input_card [data-testid="stAlert"] > div { align-items:center !important; margin:0 !important; padding-top:0 !important; padding-bottom:0 !important; }

/* Themed drag-and-drop dropzone. */
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section {
    background: rgba(139,92,246,.04) !important;
    border: 1px dashed rgba(139,92,246,.4) !important;
    border-radius: 12px !important;
    transition: border-color .15s ease, background .15s ease;
}
[data-testid="stFileUploaderDropzone"]:hover, [data-testid="stFileUploader"] section:hover {
    border-color: rgba(139,92,246,.75) !important;
    background: rgba(139,92,246,.08) !important;
}

/* Analyse Profile button, scoped via marker + :has() on its column. */
div[data-testid="stColumn"]:has(#analyse-btn-marker) [data-testid="stButton"]>button {
    height:3rem; min-height:3rem; font-size:1rem; font-weight:600; letter-spacing:.01em; margin-top:.3rem;
}
div[data-testid="stColumn"]:has(#start-interview-marker) [data-testid="stButton"]>button {
    height:3rem; min-height:3rem; font-size:1rem; font-weight:600; letter-spacing:.01em;
}
div[data-testid="stColumn"]:has(#analyse-btn-marker) [data-testid="stButton"]>button:hover,
div[data-testid="stColumn"]:has(#start-interview-marker) [data-testid="stButton"]>button:hover {
    transform:translateY(-2px); filter:brightness(1.08); box-shadow:0 6px 18px rgba(139,92,246,.35);
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
DEFAULTS = {
    "input_signature": None,
    "interview_language": "English",
    "results": None,
    "cv_text": "",
    "jd_text": "",
    "videos": None,
    "videos_error": None,
    "iv_active": False,
    "iv_questions": [],
    "iv_index": 0,
    "iv_answers": [],
    "iv_done": False,
    "iv_report": None,
    "report_error": None,
    "voice_on": True,
    "spoken_idx": -1,
    "tts_audio": None,
    "tts_identity": None,
    "last_audio_id": None,
    "transcription_error": None,
    "tts_last_error": None,
    "last_tts_call_ts": 0.0,
}


def _default_copy(value):
    """Return an independent copy of mutable defaults so a reset never
    shares (or mutates) the module-level DEFAULTS objects."""
    if isinstance(value, (list, dict)):
        return value.copy()
    return value


for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, _default_copy(value))


def _clear_dynamic_answer_keys():
    """Clear the per-question answer_0, answer_1, ... keys, which are
    created on the fly and are not part of DEFAULTS."""
    for k in [k for k in st.session_state.keys() if k.startswith(("answer_", "mic_"))]:
        del st.session_state[k]


def reset_all():
    for key, value in DEFAULTS.items():
        st.session_state[key] = _default_copy(value)
    _clear_dynamic_answer_keys()


def reset_interview():
    for key in ("iv_active", "iv_questions", "iv_index", "iv_answers",
                "iv_done", "iv_report", "report_error", "spoken_idx", "tts_audio", "tts_identity", "last_audio_id", "transcription_error",
                "tts_last_error", "last_tts_call_ts"):
        st.session_state[key] = _default_copy(DEFAULTS[key])
    _clear_dynamic_answer_keys()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def speak(text, retries=2, backoff_seconds=1.5):
    """Cache audio by question and render the same player on every rerun."""
    if not text or not st.session_state.voice_on:
        return False
    identity = hashlib.sha256((str(st.session_state.iv_index) + "\0" + st.session_state.interview_language + "\0" + text).encode()).hexdigest()
    if st.session_state.tts_identity != identity:
        st.session_state.tts_audio = None
        st.session_state.tts_identity = identity
        st.session_state.tts_last_error = None
        elapsed = time.time() - st.session_state.last_tts_call_ts
        if elapsed < 2:
            time.sleep(2 - elapsed)
        for attempt in range(retries + 1):
            try:
                stream = io.BytesIO()
                gtts.gTTS(text=text, lang="ur" if st.session_state.interview_language == "Urdu" else "en", timeout=15).write_to_fp(stream)
                st.session_state.tts_audio = base64.b64encode(stream.getvalue()).decode()
                st.session_state.tts_last_error = None
                break
            except Exception:
                st.session_state.tts_last_error = "Voice service is temporarily unavailable."
                if attempt < retries:
                    time.sleep(backoff_seconds)
        st.session_state.last_tts_call_ts = time.time()
    if st.session_state.tts_audio:
        components.html(player_html(st.session_state.tts_audio, identity), height=66, scrolling=False)
        return True
    return False


def match_tier(pct):
    """Single source of truth for score color and label, so the color bar
    and the text label never contradict each other."""
    if pct >= 75:
        return "#22c55e", "Excellent match"
    if pct >= 60:
        return "#22c55e", "Strong match"
    if pct >= 40:
        return "#f59e0b", "Fair match"
    return "#ef4444", "Low match"


def score_color(pct):
    return match_tier(pct)[0]


def score_word(pct):
    return match_tier(pct)[1]


def rec_style(rec):
    r = rec.lower()
    if "strong" in r:
        return "#22c55e", "rgba(34,197,94,.15)"
    if "not" in r or "no" in r:
        return "#ef4444", "rgba(239,68,68,.15)"
    if "hire" in r:
        return "#06b6d4", "rgba(6,182,212,.15)"
    return "#f59e0b", "rgba(245,158,11,.15)"


def chips(items, kind):
    if not items:
        return '<span class="muted">None identified.</span>'
    return '<div class="chips">' + "".join(
        f'<span class="chip {kind}">{st_escape(i)}</span>' for i in items
    ) + "</div>"


def st_escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def section(step_number, title):
    st.markdown(
        f'<div class="section-title"><span class="step-badge">{step_number}</span>{st_escape(title)}</div>',
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False, ttl=1800, max_entries=32)
def extract_resume_text(file_bytes, filename):
    return read_resume(file_bytes, filename)


# --------------------------------------------------------------------------
# Hero
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <h1>Skill Gap Lynx</h1>
      <p>AI-powered resume screening &amp; live voice interview, for <b>any</b> job, any field.</p>
      <div class="pill-row">
        <span class="pill">Smart match scoring</span>
        <span class="pill">Learning roadmap</span>
        <span class="pill">Video resources</span>
        <span class="pill">Live AI interview</span>
        <span class="pill">Urdu / English</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Configuration guard.
missing = config.missing_keys()
if missing:
    st.error(
        f"Missing configuration: **{', '.join(missing)}**. "
        "Add it to a `.env` file in the project root, then restart the app."
    )
    st.stop()
if not config.youtube_enabled():
    st.info("YouTube resources are disabled (no `YOUTUBE_API_KEY`). Everything else works.")


# --------------------------------------------------------------------------
# Step 1: Input
# --------------------------------------------------------------------------
st.markdown(
    '<div class="section-title"><span class="step-badge">1</span>Provide your resume &amp; target job</div>'
    '<div class="section-sub">Upload your resume and paste the job description.</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True, height="stretch", gap="xsmall", key="resume_input_card"):
        st.markdown(
            '<div class="input-card-header"><span class="input-card-icon"></span>'
            '<div><p class="input-card-title">Upload Resume</p>'
            '<p class="input-card-sub">PDF / Word • Max 10MB</p></div></div>',
            unsafe_allow_html=True,
        )
        # st.file_uploader already supports native browser drag-and-drop by
        # default, this just themes the dropzone.
        uploaded = st.file_uploader("Resume (PDF or Word)", type=["pdf", "docx"], label_visibility="collapsed")
        cv_text = ""
        if uploaded:
            try:
                if uploaded.size > 10 * 1024 * 1024:
                    raise ValueError("Resume must be smaller than 10MB.")
                cv_text = extract_resume_text(uploaded.getvalue(), uploaded.name)
                if cv_text.strip():
                    st.markdown(f'<div class="resume-loaded" role="status">Resume loaded ({len(cv_text):,} characters extracted).</div>', unsafe_allow_html=True)
                else:
                    st.warning("Could not extract text. This appears to be a scanned/image PDF. Export a text-based PDF from Word or Google Docs and upload it.")
            except Exception as exc:
                st.error(f"Error reading resume: {exc}")
with col2:
    with st.container(border=True, height="stretch", gap="xsmall", key="job_input_card"):
        st.markdown(
            '<div class="input-card-header"><span class="input-card-icon"></span>'
            '<div><p class="input-card-title">Job Description</p>'
            '<p class="input-card-sub">Paste the target job description here (any field)...</p></div></div>',
            unsafe_allow_html=True,
        )
        jd_text = st.text_area(
            "Job description", height=90, max_chars=10000, label_visibility="collapsed",
            placeholder="Write a Job description",
        )
        st.markdown(f'<div class="char-count">{len(jd_text):,}/10000</div>', unsafe_allow_html=True)

signature = hashlib.sha256((cv_text + "\0" + jd_text).encode()).hexdigest()
if st.session_state.input_signature and st.session_state.input_signature != signature:
    reset_all()
    st.info("Inputs changed. Analyse the updated resume and job description again.")

btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
with btn_col2:
    st.markdown('<div id="analyse-btn-marker"></div>', unsafe_allow_html=True)
    analyse_clicked = st.button("Analyse Profile", use_container_width=True)

if analyse_clicked:
    if cv_text.strip() and jd_text.strip():
        with st.spinner("Analysing profile alignment with Groq..."):
            res = analyze_profile(cv_text, jd_text)
        if "error" in res:
            st.error(f"Analysis failed: {res['error']}")
        else:
            # Reconcile the skill gap before storing.
            st.session_state.input_signature = signature
            st.session_state.results = res
            st.session_state.cv_text = cv_text
            st.session_state.jd_text = jd_text
            st.session_state.videos = None
            st.session_state.videos_error = None
            reset_interview()
            st.rerun()
    else:
        st.warning("Please provide both a valid PDF or Word resume and a job description.")


# --------------------------------------------------------------------------
# Step 2: Results
# --------------------------------------------------------------------------
res = st.session_state.results
if res:
    pct = res["match_percentage"]
    color, label = match_tier(pct)
    st.markdown("<hr style='border-color:rgba(255,255,255,.08)'>", unsafe_allow_html=True)
    section("2", f"Results for {res['candidate_name']}")

    # Match score bar
    st.markdown(
        f"""
        <div class="card">
          <div class="score-label">Match score</div>
          <div class="score-wrap">
            <div class="score-num" style="color:{color}">{pct}%</div>
            <div class="score-track"><div class="score-fill"
                 style="width:{pct}%;background:linear-gradient(90deg,{color},#8b5cf6)"></div></div>
          </div>
          <div class="score-label" style="margin-top:.6rem">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="card"><div class="section-title">Matching skills</div>'
            f'{chips(res["matching_skills"], "good")}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="card"><div class="section-title">Missing skills</div>'
            f'{chips(res["missing_skills"], "miss")}</div>', unsafe_allow_html=True)

    if res.get("feedback"):
        st.info(f"**Recruiter feedback:** {res['feedback']}")

    # Learning roadmap
    if res.get("roadmap"):
        rows = ""
        for item in res["roadmap"]:
            pr = item["priority"].lower()
            pr = pr if pr in ("high", "medium", "low") else "medium"
            rows += (
                f'<div class="road"><span class="badge {pr}">{st_escape(item["priority"])}</span>'
                f'<div><b>{st_escape(item["skill"])}</b><br>'
                f'<span class="act">{st_escape(item["action"])}</span></div></div>'
            )
        st.markdown(
            f'<div class="card"><div class="section-title">Learning roadmap</div>'
            f'<div class="section-sub">Priority-ordered plan to close the gaps.</div>{rows}</div>',
            unsafe_allow_html=True,
        )

    # YouTube resources
    # Wrapped in error handling with a visible retry option.
    practice_videos = not res["missing_skills"]
    video_skills = res["missing_skills"] or res["matching_skills"]
    if config.youtube_enabled() and video_skills:
        need_fetch = st.session_state.videos is None and st.session_state.videos_error is None
        if need_fetch:
            with st.spinner("Finding learning videos..."):
                try:
                    st.session_state.videos = get_learning_videos(video_skills, practice=practice_videos)
                    st.session_state.videos_error = None
                except Exception as exc:
                    st.session_state.videos = None
                    st.session_state.videos_error = str(exc)

        if st.session_state.videos_error:
            st.warning(f"Couldn't load learning videos right now: {st.session_state.videos_error}")
            if st.button("Retry loading videos"):
                st.session_state.videos_error = None
                st.rerun()
        else:
            videos = st.session_state.videos or []
            if not videos:
                st.caption("No learning videos found for these skills.")
            if videos:
                section("", "Recommended practice videos" if practice_videos else "Recommended learning videos")
                if practice_videos:
                    st.caption("You match the assessed requirements. Use these videos to practice and strengthen your existing skills.")
                vcols = st.columns(min(3, len(videos)))
                for i, vid in enumerate(videos):
                    with vcols[i % len(vcols)]:
                        st.video(vid["url"])
                        # Plain markdown link syntax handles escaping safely.
                        st.markdown(f"**{st_escape(vid['skill'])}** · [{st_escape(vid['title'][:55])}]({vid['url']})")
                        st.caption(vid["channel"])


# --------------------------------------------------------------------------
# Step 3: Live interview
# --------------------------------------------------------------------------
if res:
    st.markdown("<hr style='border-color:rgba(255,255,255,.08)'>", unsafe_allow_html=True)
    section("3", "Live AI interview")
    st.markdown('<div class="section-sub">Personalised questions from your CV &amp; JD. '
                'Answer by voice or text, in English or Urdu.</div>', unsafe_allow_html=True)

    # Not started yet
    if not st.session_state.iv_active:
        st.session_state.interview_language = st.selectbox("Interview language", ["English", "Urdu"], index=0 if st.session_state.interview_language == "English" else 1)
        st.session_state.voice_on = st.toggle("Voice questions", value=st.session_state.voice_on)
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            st.markdown('<div id="start-interview-marker"></div>', unsafe_allow_html=True)
            start_clicked = st.button("Start Interview", use_container_width=True)
        if start_clicked:
            # Guarantee `questions` is always defined, even if
            # generate_questions() raises an unexpected exception.
            questions = None
            try:
                with st.spinner("Preparing your interview questions..."):
                    questions = generate_questions(
                        st.session_state.cv_text, st.session_state.jd_text,
                        res["matching_skills"], res["missing_skills"],
                        language=st.session_state.interview_language,
                    )
            except Exception as exc:
                st.error(f"Interview preparation failed: {exc}")
                questions = None
            # Guard against an empty/None question list.
            if not questions:
                st.error("Couldn't generate interview questions. Please try again.")
            else:
                st.session_state.iv_questions = questions
                st.session_state.iv_active = True
                st.session_state.iv_index = 0
                st.session_state.iv_answers = []
                st.session_state.iv_done = False
                st.session_state.spoken_idx = -1
                st.session_state.tts_last_error = None
                st.rerun()

    # Interview finished: show report
    elif st.session_state.iv_done:
        if st.session_state.report_error:
            st.warning("Report feedback is unavailable. The displayed score is based on your evaluated answers.")
            if st.button("Retry report feedback"):
                with st.spinner("Compiling your interview report..."):
                    try:
                        st.session_state.iv_report = generate_final_report(st.session_state.iv_answers, res["match_percentage"], st.session_state.jd_text)
                        st.session_state.report_error = st.session_state.iv_report.get("error")
                    except Exception as exc:
                        st.session_state.report_error = str(exc)
                st.rerun()
        report = st.session_state.iv_report or {}
        ov = report.get("overall_score", 0)
        rec = report.get("recommendation", "Maybe")
        col, bg = rec_style(rec)

        st.markdown(
            f"""
            <div class="card">
              <div class="score-label">Interview result</div>
              <div class="score-wrap">
                <div class="score-num" style="color:{score_color(ov)}">{ov}<span style="font-size:1.2rem">/100</span></div>
                <div class="score-track"><div class="score-fill"
                     style="width:{ov}%;background:linear-gradient(90deg,{score_color(ov)},#8b5cf6)"></div></div>
                <span class="rec-badge" style="color:{col};background:{bg};border:1px solid {col}">{st_escape(rec)}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if report.get("summary"):
            st.info(f"**Verdict:** {report['summary']}")

        s1, s2 = st.columns(2)
        with s1:
            items = "".join(f"<li>{st_escape(x)}</li>" for x in report.get("strengths", [])) \
                or "<li class='muted'>-</li>"
            st.markdown(f'<div class="card"><div class="section-title">Strengths</div><ul>{items}</ul></div>',
                        unsafe_allow_html=True)
        with s2:
            items = "".join(f"<li>{st_escape(x)}</li>" for x in report.get("improvements", [])) \
                or "<li class='muted'>-</li>"
            st.markdown(f'<div class="card"><div class="section-title">Improvements</div><ul>{items}</ul></div>',
                        unsafe_allow_html=True)

        with st.expander("Per-question breakdown"):
            for i, ans in enumerate(st.session_state.iv_answers, 1):
                ev = ans.get("eval", {})
                st.markdown(f"**Q{i}. {st_escape(ans['question'])}**")
                st.markdown(f"<span class='muted'>Your answer:</span> {st_escape(ans.get('answer', '-'))}",
                            unsafe_allow_html=True)
                st.markdown(f"**Score: {ev.get('score', 0)}/10** · _{st_escape(ev.get('language', ''))}_")
                st.markdown(f"**Strengths:** {st_escape(ev.get('strengths', '-'))}")
                st.markdown(f"**Improvements:** {st_escape(ev.get('improvements', '-'))}")
                st.markdown("---")

        if st.button("Start Over"):
            reset_all()
            st.rerun()

    # Interview in progress
    else:
        questions = st.session_state.iv_questions
        idx = st.session_state.iv_index
        total = len(questions)

        # Defensive guard in case session state is ever corrupted.
        if total == 0 or idx >= total:
            st.error("Interview state is invalid. Please restart the interview.")
            if st.button("Restart interview"):
                reset_interview()
                st.rerun()
            st.stop()

        question = questions[idx]

        st.progress((idx) / total, text=f"Question {idx + 1} of {total}")
        st.markdown(
            f'<div class="q-bubble"><span class="q-label">Interviewer</span>{st_escape(question)}</div>',
            unsafe_allow_html=True,
        )

        # The player occupies a stable slot, cleared before advancing.
        voice_slot = st.empty()
        with voice_slot.container():
            speak(question)

        # Make TTS failures visible with a one-click retry option.
        if st.session_state.voice_on and st.session_state.tts_last_error:
            st.warning(
                "Couldn't play the question audio for this one "
                f"({st.session_state.tts_last_error}). You can still read and "
                "answer it below, or retry the audio."
            )
            if st.button("Retry question audio", key=f"retry_tts_{idx}"):
                st.session_state.tts_identity = None
                st.rerun()

        answer_key = f"answer_{idx}"
        st.session_state.setdefault(answer_key, "")

        st.write("")
        mcol, _ = st.columns([1, 2])
        with mcol:
            audio = mic_recorder(
                start_prompt="Record answer", stop_prompt="Stop & transcribe",
                just_once=False, key=f"mic_{idx}",
            )

        # New recording -> transcribe into the editable answer box.
        if audio and audio.get("bytes") and st.session_state.last_audio_id != audio.get("id"):
            st.session_state.last_audio_id = audio.get("id")
            st.session_state.transcription_error = None
            with st.spinner("Transcribing your answer..."):
                try:
                    text, err = transcribe_answer(audio["bytes"], audio.get("format", "webm"), language=st.session_state.interview_language)
                except Exception as exc:  # defensive: don't let a transcription
                    text, err = "", str(exc)  # crash take down the whole interview
            if err:
                st.session_state.transcription_error = err
            else:
                st.session_state.last_audio_id = audio.get("id")
                st.session_state[answer_key] = text
                st.rerun()

        if st.session_state.transcription_error:
            st.error(f"Transcription failed: {st.session_state.transcription_error}")
            if st.button("Retry transcription", key=f"retry_transcription_{idx}"):
                st.session_state.last_audio_id = None
                st.rerun()

        st.text_area(
            "Your answer (type, or edit the transcription)",
            key=answer_key, height=130, max_chars=8000,
            placeholder="Speak using the recorder above, or type your answer here...",
        )

        b1, b2 = st.columns([2, 1])
        with b1:
            submit = st.button("Submit answer", key=f"submit_{idx}")
        with b2:
            skip = st.button("Skip", key=f"skip_{idx}")

        if submit or skip:
            voice_slot.empty()
            answer = "" if skip else st.session_state.get(answer_key, "").strip()
            with st.spinner("Evaluating..."):
                try:
                    ev = evaluate_answer(question, answer, st.session_state.jd_text)
                except Exception as exc:
                    ev = {"error": str(exc), "score": None, "language": "", "strengths": "-",
                          "improvements": f"Evaluation failed: {exc}"}
            if ev.get("error"):
                st.error("Evaluation unavailable. Your answer is preserved; click Submit answer to retry.")
                st.stop()
            st.session_state.iv_answers.append(
                {"question": question, "answer": answer or "(no answer)", "eval": ev}
            )
            if idx + 1 >= total:
                with st.spinner("Compiling your interview report..."):
                    try:
                        st.session_state.iv_report = generate_final_report(
                            st.session_state.iv_answers, res["match_percentage"],
                            st.session_state.jd_text,
                        )
                        st.session_state.report_error = st.session_state.iv_report.get("error")
                    except Exception as exc:
                        st.session_state.report_error = str(exc)
                        st.session_state.iv_report = {
                            "overall_score": round(sum(a["eval"]["score"] for a in st.session_state.iv_answers) / len(st.session_state.iv_answers) * 10), "recommendation": "Maybe",
                            "summary": f"Report generation failed: {exc}",
                            "strengths": [], "improvements": [],
                        }
                st.session_state.iv_done = True
            else:
                st.session_state.iv_index += 1
                st.session_state.last_audio_id = None
                st.session_state.transcription_error = None
            st.rerun()

st.markdown(
    "<p style='text-align:center;color:#55556e;font-size:.8rem;margin-top:2rem'>"
    "Built with Streamlit, Groq, Whisper | Skill Gap Lynx</p>",
    unsafe_allow_html=True,
)
