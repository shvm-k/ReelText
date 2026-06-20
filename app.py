"""ReelText — turn Instagram Reels and videos into clean text transcripts.

Open-source · privacy-first · no account required.
"""

import os
import shutil
import subprocess
import tempfile

import streamlit as st
import yt_dlp

# ── Config ────────────────────────────────────────────────────────────────────
SITE_URL = "https://shvm-k.github.io"
MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_DURATION_SECONDS = 90
SPEED_TO_ARCH = {"⚡ Fast": "tiny", "🎯 Accurate": "base"}

st.set_page_config(page_title="ReelText — Reels into clean text", page_icon="📝", layout="centered")

# ── Design system ───────────────────────────────────────────────────────────--
CSS = """
<style>
/* Inter + Geist are loaded via [[theme.fontFaces]] in .streamlit/config.toml —
   Streamlit's markdown sanitizer strips @import, so fonts must be registered there. */
:root{
  /* Spacing scale — every margin/padding belongs to this set */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px; --s8:64px; --s9:96px;
  /* Color */
  --bg:#FAFAF8; --bg-sunken:#F5F4F0; --surface:#FFFFFF;
  --text:#111111; --text-2:#666666; --text-3:#9C9A91;
  --border:#EAE8E0; --border-2:#DEDBD0;
  --accent:#D4B200; --accent-soft:rgba(212,178,0,.13);   /* functional gold — used sparingly */
  --marker:#FFE24D; --marker-soft:rgba(255,226,77,.20);  /* bright highlighter — the one signature moment */
  /* Radii */
  --r-lg:24px; --r-md:12px; --r-sm:10px;
  /* Elevation — near-invisible; depth comes from contrast + spacing, not shadows */
  --shadow:0 1px 2px rgba(17,17,17,.04);
  --shadow-press:0 6px 18px -10px rgba(17,17,17,.30);
  /* Motion — never bouncy */
  --ease:cubic-bezier(.4,0,.2,1);
  --ease-out:cubic-bezier(.16,.84,.3,1);
  --fast:.16s; --base:.22s;
  /* Type */
  --font-display:'Geist','Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --font-body:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
}

/* Hide Streamlit chrome (incl. the auto heading-anchor link icon) */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stHeaderActionElements"], #MainMenu, footer{display:none !important;}

html, body, .stApp{background:var(--bg) !important; color:var(--text); font-family:var(--font-body) !important;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
  font-feature-settings:'cv05' 1,'ss01' 1;}
/* Force our type system over Streamlit's theme font (never touch icon fonts) */
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li, [data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p, button[data-baseweb="tab"] p,
[data-testid="stTextInput"] input, [data-testid="stToggle"] label,
.stButton button, .stButton button p, .stDownloadButton button, .stDownloadButton button p,
[data-testid="stBaseButton-segmented_control"], [data-testid="stBaseButton-segmented_control"] p,
[data-testid="stBaseButton-segmented_controlActive"], [data-testid="stBaseButton-segmented_controlActive"] p,
[data-testid="stCode"], [data-testid="stCode"] code, [data-testid="stCode"] pre{
  font-family:var(--font-body) !important;}
[data-testid="stMarkdownContainer"] .rt-headline,
[data-testid="stMarkdownContainer"] .rt-wordmark,
[data-testid="stMarkdownContainer"] .rt-ready{font-family:var(--font-display) !important;}
*{box-shadow:none;}
.block-container{max-width:800px; padding-top:var(--s6) !important; padding-bottom:var(--s8) !important;
  margin-inline:auto !important;}

/* ── Header — logo anchored left for deliberate asymmetry ─────────────────── */
.rt-header{display:flex; align-items:center; justify-content:flex-start; margin:0 0 var(--s7);}
.rt-wordmark{font-family:var(--font-display); font-weight:700; font-size:1.35rem; letter-spacing:-.05em;
  color:var(--text); line-height:1;}
.rt-wordmark .dot{color:var(--accent);}

/* ── Hero — left-aligned, editorial tension ───────────────────────────────--- */
.rt-hero{display:flex; flex-direction:column; align-items:flex-start; text-align:left; margin-bottom:var(--s7);}
.rt-eyebrow{font-size:.75rem; font-weight:600; letter-spacing:.2em; text-transform:uppercase;
  color:var(--text-3); margin:0 0 var(--s4);}
.rt-headline{font-family:var(--font-display); font-weight:700; font-size:clamp(2.75rem,8vw,5.25rem);
  line-height:1.02; letter-spacing:-.045em; color:var(--text); margin:0 0 var(--s4); max-width:16ch;}
.rt-sub{font-size:1.125rem; line-height:1.55; letter-spacing:-.011em; color:var(--text-2);
  max-width:46ch; margin:0;}

/* Signature marker — imperfect, hand-highlighted, revealed once on load */
.rt-mark{position:relative; display:inline-block;}
.rt-mark > span{position:relative; z-index:1;}
.rt-mark::before{content:""; position:absolute; z-index:0; background:var(--marker);
  mix-blend-mode:multiply; border-radius:9px 12px 8px 13px / 13px 9px 14px 8px;
  background-image:
    linear-gradient(180deg, rgba(255,255,255,.18), rgba(255,255,255,0) 32%),
    linear-gradient(0deg, rgba(0,0,0,.045), rgba(0,0,0,0) 36%);
  left:-.12em; right:-.12em; top:.10em; bottom:.05em; transform:rotate(-1.1deg);}
.rt-mark.anim::before{clip-path:inset(0 100% 0 0); animation:rt-reveal .8s var(--ease-out) .3s forwards;}
@keyframes rt-reveal{to{clip-path:inset(0 -.02em 0 0);}}

/* Trust indicators */
.rt-trust{display:flex; flex-wrap:wrap; justify-content:flex-start; gap:var(--s2) var(--s5);
  margin:var(--s5) 0 0; padding:0;}
.rt-trust-item{display:inline-flex; align-items:center; gap:var(--s2); color:var(--text-2);
  font-size:.9rem; cursor:default; transition:color var(--fast) var(--ease);}
.rt-trust-item::before{content:"✓"; color:var(--accent); font-weight:700; font-size:.82em;
  transition:transform var(--fast) var(--ease-out);}
.rt-trust-item:hover{color:var(--text);}
.rt-trust-item:hover::before{transform:scale(1.18);}

/* ── Tool card — belongs to the page; depth via border + surface, not shadow ── */
[data-testid="stVerticalBlockBorderWrapper"]:has(.rt-card-anchor){
  background:var(--surface) !important; border:1px solid rgba(17,17,17,.08) !important;
  border-radius:var(--r-lg) !important; box-shadow:0 1px 2px rgba(0,0,0,.03) !important;
  padding:var(--s6) !important;}
.rt-card-anchor{display:none;}

/* Segmented control (speed) — left-anchored to match the editorial axis */
[data-testid="stButtonGroup"]{background:var(--bg-sunken); padding:var(--s1); border-radius:var(--r-md);
  width:fit-content; margin:0 0 var(--s4); gap:var(--s1) !important;}
[data-testid="stBaseButton-segmented_control"],
[data-testid="stBaseButton-segmented_controlActive"]{border:none !important; border-radius:8px !important;
  font-weight:600 !important; padding:6px 16px !important; transition:background var(--base) var(--ease),
  color var(--base) var(--ease), box-shadow var(--base) var(--ease);}
[data-testid="stBaseButton-segmented_control"]{background:transparent !important; color:var(--text-2) !important;}
[data-testid="stBaseButton-segmented_control"] *{color:var(--text-2) !important;}
[data-testid="stBaseButton-segmented_control"]:hover{background:var(--accent-soft) !important; color:var(--text) !important;}
[data-testid="stBaseButton-segmented_control"]:hover *{color:var(--text) !important;}
[data-testid="stBaseButton-segmented_controlActive"]{background:var(--surface) !important;
  color:var(--text) !important; box-shadow:inset 0 -2px 0 var(--accent), 0 1px 2px rgba(17,17,17,.08) !important;}
[data-testid="stBaseButton-segmented_controlActive"] *{color:var(--text) !important;}

/* Tabs — sliding gold highlight */
[data-baseweb="tab-list"]{gap:var(--s1) !important; border-bottom:1px solid var(--border) !important;
  background:transparent !important;}
button[data-baseweb="tab"]{background:transparent !important; color:var(--text-2) !important;
  font-weight:600 !important; border-radius:9px 9px 0 0 !important; padding:8px 14px !important;
  transition:background var(--base) var(--ease), color var(--base) var(--ease);}
button[data-baseweb="tab"] p{color:inherit !important; font-weight:600 !important; font-size:.95rem !important;}
button[data-baseweb="tab"]:hover{background:var(--marker-soft) !important; color:var(--text) !important;}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--text) !important;}
[data-baseweb="tab-highlight"]{background:var(--accent) !important; height:2px !important; border-radius:2px;
  transition:all .3s var(--ease) !important;}
[data-baseweb="tab-border"]{display:none !important;}

/* Caption / helper text */
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p{color:var(--text-3) !important;
  font-size:.875rem !important; line-height:1.5 !important;}

/* Text input (URL) */
[data-testid="stTextInput"] input{background:var(--surface) !important; height:48px;
  border:1px solid var(--border-2) !important; border-radius:var(--r-sm) !important;
  padding:0 var(--s4) !important; font-size:1rem !important; color:var(--text) !important;
  transition:border-color var(--base) var(--ease), box-shadow var(--base) var(--ease);}
[data-testid="stTextInput"] input::placeholder{color:var(--text-3) !important;}
[data-testid="stTextInput"] input:focus{border-color:var(--accent) !important;
  box-shadow:0 0 0 3px var(--accent-soft) !important; outline:none !important;}

/* Upload dropzone — the dominant surface, with custom idle copy */
[data-testid="stFileUploaderDropzone"]{background:var(--bg-sunken) !important;
  border:1.5px dashed var(--border-2) !important; border-radius:var(--r-md) !important;
  padding:var(--s6) var(--s5) !important; min-height:148px; cursor:pointer;
  display:flex !important; flex-direction:column !important; align-items:center !important;
  justify-content:center !important; gap:var(--s3) !important; text-align:center;
  transition:border-color var(--base) var(--ease), background var(--base) var(--ease),
  box-shadow var(--base) var(--ease);}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--accent) !important;
  background:#FBF7E6 !important;}
[data-testid="stFileUploaderDropzone"]:focus-within{border-color:var(--accent) !important;
  background:#FBF7E6 !important; box-shadow:0 0 0 4px var(--accent-soft) !important;}
/* custom idle copy (replaces the default size line) */
[data-testid="stFileUploaderDropzoneInstructions"]{order:0; display:flex; flex-direction:column;
  align-items:center; gap:var(--s1);}
[data-testid="stFileUploaderDropzoneInstructions"] *{font-size:0 !important; line-height:0 !important;
  color:transparent !important;}
[data-testid="stFileUploaderDropzoneInstructions"]::before{content:"Drop a Reel here"; display:block;
  font-size:1.0625rem; font-weight:600; color:var(--text); letter-spacing:-.012em;}
[data-testid="stFileUploaderDropzoneInstructions"]::after{content:"MP4 · MOV · up to 25 MB"; display:block;
  font-size:.82rem; font-weight:500; color:var(--text-3); margin-top:var(--s1);}
/* browse button → quiet ghost, relabelled */
[data-testid="stFileUploaderDropzone"] > span{order:1;}
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"]{
  background:var(--surface) !important; color:var(--text) !important;
  border:1px solid var(--border-2) !important; border-radius:var(--r-sm) !important;
  font-weight:600 !important; padding:8px 16px !important;
  transition:background var(--fast) var(--ease), border-color var(--fast) var(--ease), transform var(--fast) var(--ease);}
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"] *{color:var(--text) !important;}
[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"]:hover{
  background:var(--accent-soft) !important; border-color:var(--accent) !important; transform:translateY(-1px);}
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p{font-size:0 !important;}
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p::after{
  content:"Browse your device"; font-size:.9rem; font-weight:600; color:var(--text);}
[data-testid="stFileUploaderDropzone"] [data-testid="stIconMaterial"]{color:var(--text-2) !important;
  font-size:18px !important;}

/* Uploaded-file chip — quiet success */
[data-testid="stFileUploaderFile"]{background:var(--surface) !important; border:1px solid var(--border) !important;
  border-radius:var(--r-sm) !important; padding:var(--s3) var(--s4) !important; margin-top:var(--s3) !important;}
[data-testid="stFileUploaderFileName"]{color:var(--text) !important; font-weight:500 !important;}
[data-testid="stFileUploaderFile"] [data-testid="stIconMaterial"]{color:var(--accent) !important;}

/* Primary CTA */
.stButton > button{background:var(--text) !important; color:#fff !important; height:48px;
  border:none !important; border-radius:var(--r-sm) !important; font-weight:600 !important;
  font-size:1rem !important; letter-spacing:-.005em;
  transition:transform var(--fast) var(--ease), box-shadow var(--base) var(--ease), background var(--base) var(--ease);}
.stButton > button *{color:#fff !important;}
.stButton > button:hover{transform:translateY(-1px); box-shadow:var(--shadow-press) !important; background:#000 !important;}
.stButton > button:active{transform:translateY(0); box-shadow:none !important;}

/* Download buttons — quiet secondary */
.stDownloadButton > button{background:var(--surface) !important; color:var(--text) !important; height:44px;
  border:1px solid var(--border-2) !important; border-radius:var(--r-sm) !important; font-weight:600 !important;
  transition:border-color var(--fast) var(--ease), background var(--fast) var(--ease), transform var(--fast) var(--ease);}
.stDownloadButton > button *{color:var(--text) !important;}
.stDownloadButton > button:hover{border-color:var(--text) !important; background:var(--bg-sunken) !important;
  transform:translateY(-1px);}

/* Body copy black; never override dark buttons / muted utility classes */
div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li,
label, h1, h2, h3, h4{color:var(--text);}

/* ── Transcript panel ──────────────────────────────────────────────────--- */
.rt-ready-wrap{display:flex; align-items:center; gap:var(--s3); margin:var(--s7) 0 0;}
.rt-check{width:24px; height:24px; border-radius:7px; background:var(--accent-soft); position:relative; flex:0 0 auto;}
.rt-check::after{content:""; position:absolute; left:9px; top:5px; width:5px; height:10px;
  border:solid var(--accent); border-width:0 2.5px 2.5px 0; transform:rotate(45deg);}
.rt-check.draw{animation:rt-pop .36s var(--ease-out) both;}
@keyframes rt-pop{from{transform:scale(.4); opacity:0;} to{transform:scale(1); opacity:1;}}
.rt-ready{font-family:var(--font-display); font-weight:700; font-size:1.5rem; letter-spacing:-.03em; color:var(--text);}

/* ── Transcript preview (below the fold; illustrative only) ───────────────--- */
.rt-preview{margin-top:var(--s7); border:1px dashed var(--border-2); border-radius:var(--r-md);
  background:var(--bg-sunken); padding:var(--s5);}
.rt-preview-label{font-size:.72rem; font-weight:600; letter-spacing:.16em; text-transform:uppercase;
  color:var(--text-3); margin-bottom:var(--s4);}
.rt-preview-row{display:flex; gap:var(--s3); margin-bottom:var(--s3);}
.rt-preview-row:last-child{margin-bottom:0;}
.rt-preview-ts{flex:0 0 auto; font-size:.8rem; color:var(--accent); opacity:.75;
  font-variant-numeric:tabular-nums; padding-top:4px;}
.rt-preview-text{font-size:1.0625rem; line-height:1.7; color:var(--text-3);}
.rt-meta{font-size:.875rem; color:var(--text-3); padding-top:10px;}
[data-testid="stToggle"]{display:flex; justify-content:flex-end;}
[data-testid="stToggle"] label{color:var(--text-2) !important; font-size:.875rem !important;}
[data-testid="stCode"]{background:var(--surface) !important; border:1px solid var(--border) !important;
  border-radius:var(--r-md) !important; box-shadow:none !important; margin-top:var(--s4) !important;}
[data-testid="stCode"] pre, [data-testid="stCode"] code{font-family:var(--font-body) !important;
  font-size:1.0625rem !important; line-height:1.78 !important; color:var(--text) !important;
  background:transparent !important; white-space:pre-wrap !important; word-break:break-word;
  padding:var(--s5) !important;}
[data-testid="stCode"] pre{padding:0 !important;}
[data-testid="stCode"] [data-testid="stCodeCopyButton"], [data-testid="stCode"] button{
  color:var(--text-3) !important;}

/* Alerts → quiet, left-marker */
[data-testid="stAlertContainer"]{border:none !important; border-left:3px solid var(--text) !important;
  border-radius:8px !important; background:var(--bg-sunken) !important;}
[data-testid="stAlertContainer"] p{color:var(--text) !important;}

/* Spinner → gold */
.stSpinner > div{border-top-color:var(--accent) !important; border-right-color:var(--accent) !important;}

/* ── Footer — asymmetric: name left, values right ─────────────────────────--- */
.rt-footer{margin-top:var(--s7); padding-top:var(--s5); border-top:1px solid var(--border);
  display:flex; align-items:center; justify-content:space-between; gap:var(--s4); flex-wrap:wrap;}
.rt-footer-left{font-size:.9rem; color:var(--text-2);}
.rt-footer-right{font-size:.85rem; color:var(--text-3);}
.rt-ulink{color:var(--text); text-decoration:none; font-weight:600; position:relative;}
.rt-ulink::after{content:""; position:absolute; left:0; bottom:-2px; height:2px; width:100%;
  background:var(--accent); transform:scaleX(0); transform-origin:left;
  transition:transform var(--base) var(--ease);}
.rt-ulink:hover::after{transform:scaleX(1);}

/* Accessibility — visible focus, reduced motion */
a:focus-visible, button:focus-visible{outline:2.5px solid var(--accent); outline-offset:2px; border-radius:5px;}
@media (prefers-reduced-motion: reduce){
  *{animation:none !important; transition:none !important;}
  .rt-mark::before{clip-path:none !important;}
}

/* ── Handcrafted mobile ───────────────────────────────────────────────--- */
@media (max-width:560px){
  .block-container{padding-left:var(--s4) !important; padding-right:var(--s4) !important;
    padding-top:var(--s5) !important;}
  .rt-header{margin-bottom:var(--s6);}
  .rt-hero{margin-bottom:var(--s6);}
  .rt-headline{letter-spacing:-.036em;}
  .rt-sub{font-size:1.0625rem;}
  .rt-trust{display:grid; grid-template-columns:1fr 1fr; gap:var(--s3) var(--s4);
    width:100%; max-width:320px; margin:var(--s5) 0 0;}
  .rt-trust-item{justify-content:flex-start;}
  [data-testid="stVerticalBlockBorderWrapper"]:has(.rt-card-anchor){padding:var(--s5) !important;}
  .rt-footer{flex-direction:column; align-items:flex-start; gap:var(--s2);}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ── Backend ────────────────────────────────────────────────────────────────--
def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def fetch_video_metadata(url: str) -> dict:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def download_video(url: str, dest_template: str) -> None:
    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "outtmpl": dest_template, "format": "mp4/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


def extract_audio(video_path: str, audio_path: str) -> None:
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", audio_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 or not os.path.exists(audio_path):
        raise RuntimeError("Couldn't extract audio from this video — the file may be corrupted or unsupported.")


@st.cache_resource(show_spinner=False)
def get_transcriber(model_arch_name: str):
    from moonshine_voice import Transcriber, get_model_for_language, string_to_model_arch
    model_path, model_arch = get_model_for_language("en", string_to_model_arch(model_arch_name))
    return Transcriber(model_path=model_path, model_arch=model_arch)


def transcribe_audio(audio_path: str, model_arch_name: str) -> list[dict]:
    from moonshine_voice import load_wav_file
    transcriber = get_transcriber(model_arch_name)
    audio_data, sample_rate = load_wav_file(audio_path)
    transcript = transcriber.transcribe_without_streaming(audio_data, sample_rate=sample_rate, flags=0)
    lines = []
    for ln in transcript.lines:
        text = (ln.text or "").strip()
        if not text:
            continue
        start = float(getattr(ln, "start_time", 0.0) or 0.0)
        dur = float(getattr(ln, "duration", 0.0) or 0.0)
        lines.append({"start": start, "end": start + dur, "text": text})
    return lines


# ── Transcript formatting ──────────────────────────────────────────────────--
def _clock(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"


def _srt_clock(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_plain(lines: list[dict]) -> str:
    return " ".join(l["text"] for l in lines).strip()


def to_timestamped(lines: list[dict]) -> str:
    return "\n".join(f"[{_clock(l['start'])}]  {l['text']}" for l in lines)


def to_srt(lines: list[dict]) -> str:
    blocks = [
        f"{i}\n{_srt_clock(l['start'])} --> {_srt_clock(l['end'])}\n{l['text']}\n"
        for i, l in enumerate(lines, 1)
    ]
    return ("\n".join(blocks).strip() + "\n") if blocks else ""


def word_count(lines: list[dict]) -> int:
    return len(to_plain(lines).split())


def process(speed_label: str, *, url: str = None, uploaded_file=None):
    """Run the full pipeline. Returns a list of line dicts ([] if no speech), or None on error."""
    if not ffmpeg_available():
        st.error("FFmpeg isn't installed on this server, so audio can't be extracted.")
        return None

    arch = SPEED_TO_ARCH[speed_label]
    tmp_dir = tempfile.mkdtemp(prefix="reeltext_")
    audio_path = os.path.join(tmp_dir, "audio.wav")
    try:
        with st.spinner("Fetching video…"):
            if url:
                info = fetch_video_metadata(url)
                duration = info.get("duration")
                if duration is None:
                    raise ValueError("Couldn't read this video's length — it may be a livestream or unsupported link.")
                if duration > MAX_DURATION_SECONDS:
                    raise ValueError(
                        f"This video is {int(duration)}s long. ReelText currently handles clips up to "
                        f"{MAX_DURATION_SECONDS}s."
                    )
                download_video(url, os.path.join(tmp_dir, "source.%(ext)s"))
                matches = [f for f in os.listdir(tmp_dir) if f.startswith("source.")]
                if not matches:
                    raise RuntimeError("The video downloaded but couldn't be located afterwards.")
                video_path = os.path.join(tmp_dir, matches[0])
            else:
                video_path = os.path.join(tmp_dir, "upload_" + uploaded_file.name)
                with open(video_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

        with st.spinner("Extracting audio…"):
            extract_audio(video_path, audio_path)

        with st.spinner(f"Transcribing — {speed_label}…"):
            return transcribe_audio(audio_path, arch)

    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()
        if any(k in msg for k in ("private", "login", "rate-limit")):
            st.error("This looks like a private or restricted account — ReelText can only read public videos.")
        else:
            st.error("Couldn't fetch this video. The link may be invalid, deleted, or temporarily unreachable.")
    except ValueError as e:
        st.error(str(e))
    except ImportError:
        st.error("A required dependency is missing on the server.")
    except RuntimeError as e:
        st.error(str(e))
    except Exception:
        st.error("Something went wrong while processing this video. Try a different file or link.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return None


# ── Header ─────────────────────────────────────────────────────────────────--
st.markdown(
    """
    <div class="rt-header">
      <div class="rt-wordmark">REELTEXT<span class="dot">.</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Hero (marker reveal plays once per session) ────────────────────────────--
first_load = "rt_seen" not in st.session_state
if first_load:
    st.session_state.rt_seen = True
mark_cls = "rt-mark anim" if first_load else "rt-mark"

st.markdown(
    f"""
    <div class="rt-hero">
      <p class="rt-eyebrow">Open-source transcription</p>
      <h1 class="rt-headline">Turn Reels Into<br><span class="{mark_cls}"><span>Clean Text</span></span></h1>
      <p class="rt-sub">Paste an Instagram Reel or upload a video. Get a clean transcript in
      seconds — no account required.</p>
      <div class="rt-trust">
        <span class="rt-trust-item">No account</span>
        <span class="rt-trust-item">Private by default</span>
        <span class="rt-trust-item">Open source</span>
        <span class="rt-trust-item">Free forever</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Tool card ─────────────────────────────────────────────────────────────--
up_go = url_go = False
uploaded_file = None
url_value = ""

with st.container(border=True):
    st.markdown('<span class="rt-card-anchor"></span>', unsafe_allow_html=True)

    speed = st.segmented_control(
        "Transcription speed",
        options=list(SPEED_TO_ARCH.keys()),
        default="⚡ Fast",
        label_visibility="collapsed",
        help="Fast is quicker with lighter accuracy. Accurate is slower but handles accents and noise better.",
    ) or "⚡ Fast"

    tab_upload, tab_url = st.tabs(["Upload Video", "Paste Reel URL"])

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Upload a video", type=["mp4", "mov"], label_visibility="collapsed"
        )
        if uploaded_file is not None and uploaded_file.size > MAX_UPLOAD_BYTES:
            st.error(
                f"This file is {uploaded_file.size / (1024 * 1024):.1f}MB — the limit is {MAX_UPLOAD_MB}MB."
            )
            uploaded_file = None
        up_go = st.button("Get Transcript →", key="go_upload", use_container_width=True)

    with tab_url:
        st.caption("Paste a public Instagram Reel link. Nothing is stored — audio is processed and discarded.")
        url_value = st.text_input(
            "Reel URL", placeholder="https://www.instagram.com/reel/…", label_visibility="collapsed"
        )
        url_go = st.button("Get Transcript →", key="go_url", use_container_width=True)

# ── Run pipeline ───────────────────────────────────────────────────────────--
if up_go or url_go:
    st.session_state.pop("tx", None)
    st.session_state.pop("tx_fresh", None)
    if up_go and uploaded_file is None:
        st.error("Add a video file first (MP4 or MOV, up to 25MB).")
    elif url_go and not url_value.strip():
        st.error("Paste a Reel URL first.")
    else:
        result = process(speed, url=url_value.strip() if url_go else None,
                         uploaded_file=uploaded_file if up_go else None)
        if result is not None and len(result) == 0:
            st.warning("Transcription finished, but no speech was detected in this video.")
        elif result:
            st.session_state.tx = result
            st.session_state.tx_fresh = True

# ── Transcript panel ───────────────────────────────────────────────────────--
if "tx" in st.session_state:
    lines = st.session_state.tx
    fresh = st.session_state.pop("tx_fresh", False)
    check_cls = "rt-check draw" if fresh else "rt-check"

    st.markdown(
        f'<div class="rt-ready-wrap"><span class="{check_cls}"></span>'
        f'<span class="rt-ready">Transcript ready</span></div>',
        unsafe_allow_html=True,
    )

    meta_col, toggle_col = st.columns([1, 1])
    with meta_col:
        st.markdown(
            f'<div class="rt-meta">{word_count(lines)} words · {len(lines)} segments</div>',
            unsafe_allow_html=True,
        )
    with toggle_col:
        show_ts = st.toggle("Show timestamps", value=False)

    body = to_timestamped(lines) if show_ts else to_plain(lines)
    st.code(body, language=None, wrap_lines=True)

    dl_txt, dl_srt = st.columns(2)
    dl_txt.download_button(
        "Download .txt", data=to_plain(lines), file_name="transcript.txt",
        mime="text/plain", use_container_width=True,
    )
    dl_srt.download_button(
        "Download .srt", data=to_srt(lines), file_name="transcript.srt",
        mime="application/x-subrip", use_container_width=True,
    )
else:
    # Below-the-fold: a static preview answering "what do I actually get?"
    st.markdown(
        """
        <div class="rt-preview">
          <div class="rt-preview-label">Transcript preview</div>
          <div class="rt-preview-row"><span class="rt-preview-ts">00:00</span>
            <span class="rt-preview-text">"Today I'm going to show you three small settings that
            instantly make your footage look more cinematic…"</span></div>
          <div class="rt-preview-row"><span class="rt-preview-ts">00:07</span>
            <span class="rt-preview-text">"First, drop your shutter speed to double your frame rate —
            that's the motion-blur trick the pros use."</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Footer ─────────────────────────────────────────────────────────────────--
st.markdown(
    f"""
    <div class="rt-footer">
      <div class="rt-footer-left">Built by
        <a class="rt-ulink" href="{SITE_URL}" target="_blank" rel="noopener">SHVM</a></div>
      <div class="rt-footer-right">Open Source · Privacy-first</div>
    </div>
    """,
    unsafe_allow_html=True,
)
