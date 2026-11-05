# 🎙️ My Local Scribe

**Turn interview recordings into speaker-labelled transcripts, entirely on your own computer.**

My Local Scribe is a small browser-based app for researchers, journalists and anyone else who works with recordings that shouldn't be uploaded to a cloud transcription service. Drop in an audio or video file, and it gives you a timestamped transcript showing who said what.

> [!WARNING]
> **Pre-release software.** This project is under active development. Features, settings and output formats may change before the first release. Please check important transcripts against the original recording.

## What it does

- **Transcribes speech** with [WhisperX](https://github.com/m-bain/whisperX), in many languages, with automatic language detection.
- **Times every word** using forced alignment.
- **Identifies speakers** with [pyannote Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1), then lets you rename them ("Interviewer", "Participant") without processing the file again.
- **Lets you check and correct the transcript in the app.** Each word lights up as the recording plays, and clicking a word jumps to that moment in the audio. You can fix the text, and change who said a passage, and your corrections go into every export.
- **Exports** TXT, CSV, SRT subtitles and JSON, individually or as one ZIP.
- **Keeps your recordings local.** Audio is processed on your computer and is never uploaded. [Read exactly what does and doesn't leave your machine.](docs/privacy.md)

**Accepted files:** WAV, MP3, M4A, FLAC, AAC, OGG, MP4, MOV, MKV, WEBM (up to 200 MB by default, [and you can raise this](docs/usage.md#large-files)).

## What you'll need

| | |
| --- | --- |
| **Python** | 3.10 to 3.13 (3.11 recommended). Python 3.14 doesn't work yet. |
| **FFmpeg** | Reads compressed audio and video formats. |
| **Hugging Face account** | Free. Needed once, to download the speaker identification model. |
| **Disk space** | About 6 GB for the Python packages and the most accurate model, and more with GPU support. |
| **NVIDIA GPU** | Optional, but long recordings are much faster with one. |

## Quick start

These steps assume you have [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) and [Git](https://git-scm.com/downloads). If you're new to any of this, the [installation guide](docs/installation.md) explains each step, including how to install FFmpeg and how to enable an NVIDIA GPU.

**1. Download the app and install its dependencies**

```bash
git clone https://github.com/MatthiasRo/my_local_scribe.git
```

```bash
cd my_local_scribe
```

```bash
conda create -n my_local_scribe python=3.11 -y
```

```bash
conda activate my_local_scribe
```

```bash
pip install -r requirements.txt
```

**2. Get access to the speaker identification model**

1. Create a free [Hugging Face](https://huggingface.co/join) account.
2. Open the [Community-1 model page](https://huggingface.co/pyannote/speaker-diarization-community-1) and accept its conditions.
3. Create a [**Read** access token](https://huggingface.co/settings/tokens) and copy it. You'll paste it into the app.

**3. Start the app**

```bash
python -m streamlit run local_transcriber_app.py
```

Your browser opens at `http://localhost:8501`. Always start the app from inside the `my_local_scribe` folder, because that's what applies its [privacy settings](docs/privacy.md#start-the-app-from-the-project-folder).

**4. Transcribe a recording**

1. Paste your token into the sidebar.
2. Set the **exact number of speakers**.
3. Upload your file and click **Transcribe + diarize**.
4. Rename the speakers, and listen through to check and correct the transcript.
5. Download your files.

The first run takes longer because the models are downloaded. For a quick first test, choose the `tiny` model and a short clip.

Your results and corrections exist only in the open browser tab, so **download them before you close or refresh it**. See the [usage guide](docs/usage.md) for what each setting does.

## Example output

```text
[00:00:00.131 - 00:00:05.795] Interviewer
Thank you for joining me today. Could you tell me a little about how you started working in this field?

[00:00:06.776 - 00:00:14.382] Participant
Of course. I began about 10 years ago as a research assistant at a small university in the north of the country.
```

## Documentation

| Guide | Read it to find out |
| --- | --- |
| [Installation](docs/installation.md) | How to set up on Windows, macOS or Linux, including GPU support |
| [Usage](docs/usage.md) | What each setting does, which model to pick, and what the export files contain |
| [Privacy](docs/privacy.md) | What stays on your computer, what connects to the internet, and how to run fully offline |
| [Troubleshooting](docs/troubleshooting.md) | How to fix common errors, and which warnings are safe to ignore |
| [How it works](docs/how-it-works.md) | How the processing pipeline and the code are organized |

## Known limitations

- **Transcripts are drafts.** Speech recognition and speaker identification both make mistakes, especially with overlapping speech, so review anything important.
- **You must give the exact speaker count.** There's no automatic speaker count yet.
- **The app asks for a token on every run,** even though a valid one is only needed for the first download. See [Running without a valid token](docs/privacy.md#the-hugging-face-token).
- **You can only edit a transcript in the app once.** Results and corrections can't be saved or reopened yet. They're lost if you close or refresh the tab, and transcribing again overwrites them. The browser warns you before you leave a page with corrections on it.
- **A passage has one speaker.** You can move a passage to a different speaker, but you can't yet split a passage where the speaker changes partway through, or add a speaker the app didn't detect.
- **A failed run starts over.** If a late stage fails, the finished transcription is lost too.
- **Word alignment covers about 40 languages.** Recordings in other languages currently fail at that stage. See [Languages](docs/usage.md#languages).
- **Only NVIDIA GPUs are accelerated.** Other computers, including Apple Silicon Macs, run on the CPU.

## Contributing

Bug reports and ideas are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) first, and **never attach real recordings, transcripts or tokens to an issue**. Changes are tracked in the [changelog](CHANGELOG.md).

## License and acknowledgements

My Local Scribe is released under the [Apache License 2.0](LICENSE.md).

It builds on the work of others, and the models it downloads have their own licenses:

| Component | Used for | License |
| --- | --- | --- |
| [WhisperX](https://github.com/m-bain/whisperX) | Transcription and alignment pipeline | BSD-2-Clause |
| [Whisper models](https://huggingface.co/Systran) (Systran conversions) | Speech recognition | MIT |
| [wav2vec2-base-960h](https://huggingface.co/facebook/wav2vec2-base-960h) | English word alignment | Apache-2.0 |
| [pyannote Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) | Speaker identification | CC-BY-4.0 |
| [Streamlit](https://streamlit.io/) | User interface | Apache-2.0 |
