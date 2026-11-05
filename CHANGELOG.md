# Changelog

Notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added

- Initial public repository: the Streamlit app, the `split_audio.py` helper, and user and developer documentation.
- Transcript editor with synced audio: passages and words are highlighted during playback, clicking a word or timestamp moves the audio, and corrections are included in the exports.
- Per-passage speaker reassignment in the transcript editor.
- In-app warnings that edits can't be saved or reopened, and that transcribing again overwrites them.
- `edited` and `speaker_changed` columns in the segments CSV, `segment_edited` and `segment_speaker_changed` columns in the words CSV, and matching values in the JSON export, including `original_text` and `original_speaker_id`.
- `.streamlit/config.toml`, which limits the app to your own computer and turns off Streamlit usage statistics.
- `.gitignore` rules that keep tokens, recordings and transcripts out of Git.

### Changed

- Renamed the app from "Local Interview Transcriber" to "My Local Scribe".
- Replaced the read-only "Readable transcript" box with the transcript editor.
- Replaced Streamlit's deprecated `use_container_width` argument, and raised the minimum Streamlit version to 1.64.

### Privacy

- Turned off pyannote's usage metrics by default. These previously reported audio duration and speaker counts to `otel.pyannote.ai`.
- Turned off Hugging Face Hub telemetry by default.
