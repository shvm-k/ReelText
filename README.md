# ReelText

Turn Instagram Reels and uploaded videos into clean text transcripts.
Open-source · privacy-first · no account required · free.

Paste a public Reel URL or drop an MP4/MOV, and ReelText extracts the audio and
transcribes it locally with an open-source speech-to-text model. Nothing is stored —
audio is processed and discarded.

## Stack

- [Streamlit](https://streamlit.io) — UI
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — fetch the video
- **ffmpeg** — extract the audio track
- [moonshine-voice](https://github.com/moonshine-ai/moonshine) — on-device transcription

No paid APIs, no keys, no tracking.

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# ffmpeg must be installed on your system (brew install ffmpeg / apt install ffmpeg)
streamlit run app.py
```

## Deploy

This is a long-running Streamlit server (WebSocket) that needs the `ffmpeg` system
binary, so it runs on Streamlit-style hosts — **not** static/serverless platforms.

**Streamlit Community Cloud (recommended, free):**
1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → pick this repo, branch, and `app.py`.
3. Deploy. `packages.txt` installs ffmpeg and `requirements.txt` installs the Python deps automatically.

**Hugging Face Spaces** also works — create a Space with the *Streamlit* SDK and push these files.

## License

Open source.
