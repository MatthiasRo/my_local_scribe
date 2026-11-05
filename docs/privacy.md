# Privacy

My Local Scribe is built for recordings you can't send to a cloud service. This page explains exactly what stays on your computer and what connects to the internet, so you can decide whether it's right for your data.

## The short version

- **Your audio and transcripts are never uploaded** by this app.
- **The internet is needed to download models.** The first run contacts Hugging Face and a few other sites to download them.
- **Once models are downloaded, you can [run fully offline](#run-fully-offline).**
- **Usage reporting is switched off** for Streamlit and pyannote.

> [!IMPORTANT]
> These protections only apply when you run the app on your own computer. **Don't deploy it to Streamlit Community Cloud or any other remote server** if your recordings are confidential. Recordings would then be processed on that server.

## What happens to your recording

| Stage | Where your data is |
| --- | --- |
| **Upload** | The file travels from your browser to the app on your own computer, and doesn't leave it. Streamlit keeps it in memory. |
| **Processing** | A copy is written to a temporary folder on your computer. |
| **After processing** | The temporary folder is deleted, even if processing fails. |
| **Playback** | A compressed MP3 copy of the audio is made in that temporary folder, and then kept in memory so the player can use it. Your browser fetches it from the app on your computer. |
| **Results and corrections** | Held in memory for your browser session, and lost when you close the tab or stop the app. The app doesn't write your corrections to disk. |
| **Downloads** | Saved wherever your browser saves files. Protecting these is up to you. |

The app has no database and doesn't save a history of your recordings or transcripts.

If the app is force-closed or your computer shuts down during processing, the temporary copy may be left behind. It's in your system's temporary folder, in a folder whose name starts with `local_transcriber_`, and you can safely delete it.

## What connects to the internet

| Service | When | What's sent | Your audio? |
| --- | --- | --- | --- |
| `huggingface.co` | First use of a model | Download requests. Your token is sent only for the speaker model. | No |
| `huggingface.co` | Normal runs, once models are downloaded | A check for model updates. Your token is included for the speaker model. | No |
| NLTK data on GitHub | First run | A download request for sentence data | No |
| `download.pytorch.org` | First French, German, Spanish or Italian recording | A download request for the alignment model | No |
| `otel.pyannote.ai` | **Never, by default** | Switched off, see below | No |
| Streamlit usage statistics | **Never, by default** | Switched off, see below | No |

### Usage reporting

Two components report usage statistics unless they're told not to. Neither reports audio or text, but this project switches both off anyway.

**pyannote** normally reports metrics to `otel.pyannote.ai`, including how long your recordings are and how many speakers they have. The app turns this off when it starts. If you'd like to support the pyannote project by sharing these metrics, set the environment variable `PYANNOTE_METRICS_ENABLED=true` before you start the app.

**Streamlit** normally collects usage statistics from your browser. The setting `gatherUsageStats = false` in `.streamlit/config.toml` turns this off.

### Start the app from the project folder

Streamlit only reads `.streamlit/config.toml` when you start it from the project folder. That file does two things for your privacy:

- It switches off Streamlit's usage statistics.
- It makes the app reachable only from your own computer. Without it, other devices on your network could open the app.

Always `cd` into the project folder before starting the app.

## Run fully offline

Once you've used your chosen model and language at least once, you can stop the app from contacting anything at all. Set this variable before you start the app:

| Terminal | Command |
| --- | --- |
| PowerShell | `$env:HF_HUB_OFFLINE="1"` |
| Anaconda Prompt or Command Prompt | `set HF_HUB_OFFLINE=1` |
| macOS or Linux | `export HF_HUB_OFFLINE=1` |

We tested this by logging every outbound connection from the app's Python process during a full run on a short English recording with the `tiny` model on Windows: there were none. For extra assurance, you can also disconnect from the internet. In this mode, the app can't download anything new, so a model or language you haven't used before fails with an error.

## The Hugging Face token

- A valid token is needed to **download** the speaker model for the first time, because the model's authors require you to accept their conditions.
- Once the model is downloaded, **a valid token is no longer needed**. The app still won't start processing with an empty token field, though. This is a [known limitation](../README.md#known-limitations). Until it's fixed, you can type any placeholder text into the field after your first run.
- The token is passed only to the speaker model. The app deliberately doesn't send it with the public Whisper and alignment downloads.
- The app doesn't save tokens to disk.

Keep your token out of this project folder. If you ever share or publish it by accident, delete it in your [Hugging Face settings](https://huggingface.co/settings/tokens) and create a new one.

## Your responsibilities

Running locally reduces risk, but it doesn't remove your other obligations. The app doesn't encrypt your files or control who can use your computer. Depending on your work, you may need the consent of the people you record, and you may have to follow your organization's rules or the law on data protection, such as an ethics board's conditions or the GDPR. In particular, check where your downloads are saved, because a folder that syncs to a cloud service will upload your transcripts.

If you find a privacy or security problem in the app, please see [Reporting problems](../CONTRIBUTING.md#reporting-problems).
