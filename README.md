# Skill Gap Lynx

AI-powered CV analysis and mock interviews with learning roadmaps, YouTube resources, and English/Urdu voice support.

[Live app](https://skill-gap-lynx.streamlit.app/) · [Repository](https://github.com/marmahmus/skill-gap-lynx)

## Features

- Upload a text-based PDF or Word `.docx` resume (up to 10MB).
- Compare your CV with a job description and view matching/missing skills.
- Get a learning roadmap and tutorials for missing skills.
- Get practice videos for existing skills when all assessed requirements match.
- Practice four personalized interview questions in English or Urdu.
- Answer by typing or microphone, edit the transcription, and receive scores and feedback.
- Retry failed transcription, evaluation, audio generation, and report feedback.

## Project structure

```text
app.py                      Streamlit interface and session flow
requirements.txt            Python dependencies
.env.example                API key template, without real secrets
.gitignore                  Excludes secrets, caches, logs, and local environment
.streamlit/config.toml      Theme and upload settings
modules/
  config.py                 Configuration and secret loading
  groq_client.py            Groq chat and speech transcription requests
  groq_analyzer.py          CV/JD comparison and skill scoring
  interview.py              Questions, evaluations, and reports
  pdf_resume.py             PDF text extraction
  resume_reader.py          PDF/Word file routing and Word extraction
  validation.py             AI response validation helpers
  voice_player.py           Custom question audio player
  youtube.py                Learning/practice video lookup
  __init__.py               Python package marker
tests/                      Automated reliability and interview flow checks
README.md                   Setup and project guide
```

## Local setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with your own API keys:

```env
GROQ_API_KEY=your_groq_key_here
YOUTUBE_API_KEY=your_youtube_key_here
```

Groq is required for AI analysis/interviews. YouTube is optional for learning videos. Enable YouTube Data API v3 in the Google Cloud project used for its key.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Streamlit hosting

Connect `marmahmus/skill-gap-lynx`, branch `main`, entry file `app.py`. Set `GROQ_API_KEY` and `YOUTUBE_API_KEY` in Streamlit Secrets. Never commit `.env` or real API keys. Changes pushed to the connected branch can update the hosted app.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Scoring and limitations

Match score is the percentage of distinct assessed requirements supported by the CV; requirements have equal weight. AI classifications may vary between analyses. Interview score is the average of successfully evaluated answers converted to 100. Failed evaluations preserve answers for retry. Mock-interview recommendations use thresholds of 85, 70, and 50 and are practice feedback.

PDFs must contain selectable text and have 1–100 pages; convert scans to searchable text first. Unlock encrypted files before uploading. Save older Word `.doc` files as `.docx`. Select the interview language before starting. Browser microphone permission is needed for recording; typing remains available. If autoplay is blocked, use the player's play button.

Results are stored temporarily in the current session; there is no permanent results database. External API availability and quotas affect AI and video features. CV text, job descriptions, and answers are sent to Groq for the requested processing; question text is sent to the text-to-speech service.

Local `.venv`, `.env`, `.git`, cache folders, and logs are not app source uploads. `.venv` is useful for local execution; `.git` preserves repository history. Keep them locally as needed.

## Developer

Muhammad Shamikh — [GitHub](https://github.com/shamikh003)
