# Troubleshooting

Find your symptom below. When processing fails, the app shows the error along with a **Technical details** section, which is the most useful thing to include in a [bug report](../CONTRIBUTING.md#reporting-problems).

**Contents**

- [Installation problems](#installation-problems)
- [Access and token errors](#access-and-token-errors)
- [Downloads hang or fail](#downloads-hang-or-fail)
- [Files won't upload or load](#files-wont-upload-or-load)
- [Memory and GPU problems](#memory-and-gpu-problems)
- [Problems with playback and editing](#problems-with-playback-and-editing)
- [Problems with the results](#problems-with-the-results)
- [Warnings you can ignore](#warnings-you-can-ignore)

## Installation problems

### `pip install` can't find a version of WhisperX

Your Python version is probably too new or too old. WhisperX needs Python 3.10 to 3.13. Check your version:

```bash
python --version
```

If it's outside that range, create a Conda environment as described in the [installation guide](installation.md#option-a-conda-recommended).

### `conda` isn't recognized

Conda either isn't installed or isn't available in this terminal. On Windows, open **Anaconda Prompt** from the Start menu instead of PowerShell.

### `streamlit` isn't recognized, or the app can't find a package

Your environment probably isn't active. Run `conda activate my_local_scribe`, and start the app with the `python -m` form, which always uses the active environment:

```bash
python -m streamlit run local_transcriber_app.py
```

### The port is already in use

Another copy of the app is probably running. Close it with `Ctrl+C` in its terminal, or choose another port:

```bash
python -m streamlit run local_transcriber_app.py --server.port 8502
```

## Access and token errors

### "A Hugging Face token is required"

Paste your token into the sidebar, or [set `HF_TOKEN`](installation.md#6-get-access-to-the-speaker-model). The app asks for this on every run. If you set the variable in a different terminal window, it won't apply here.

### "Could not load pyannote Community-1", or a 401, 403 or gated repository error

Check each of these:

1. You accepted the conditions on the [Community-1 model page](https://huggingface.co/pyannote/speaker-diarization-community-1), signed in with the same account that created the token.
2. Your token is valid and has **Read** access.
3. You copied the whole token, with no spaces around it.

## Downloads hang or fail

### The app seems stuck on a download

The largest model is 3.1 GB, so a first run can take a while on a slow connection. If the progress doesn't change for a long time:

1. Stop the app completely with `Ctrl+C` in the terminal.
2. Start it again.
3. Tick **Hugging Face compatibility download mode** in the sidebar.
4. Run the file again. Finished downloads aren't repeated.

### Test the download outside the app

This downloads the small `tiny` model directly, so you can tell whether the problem is your network or the app. You should see download progress in the terminal, and once it succeeds, the app reuses that model.

**PowerShell:**

```powershell
$env:HF_HUB_DISABLE_XET="1"
```

```powershell
python -c "from huggingface_hub import snapshot_download; print(snapshot_download('Systran/faster-whisper-tiny', allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*']))"
```

**Anaconda Prompt or Command Prompt:**

```cmd
set HF_HUB_DISABLE_XET=1
```

```cmd
python -c "from huggingface_hub import snapshot_download; print(snapshot_download('Systran/faster-whisper-tiny', allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*']))"
```

### A language model won't download

Alignment models for French, German, Spanish and Italian download from `download.pytorch.org`. Other languages download from Hugging Face. A company or university network may block these sites, so try another network for that first download. Once it's downloaded, you won't need the connection again.

English isn't affected, because the app downloads its alignment model from Hugging Face.

### "NLTK punkt_tab download failed"

Run this once, with your environment active, and then try again:

```bash
python -m nltk.downloader punkt_tab
```

## Files won't upload or load

### M4A, MP3 or video files won't load

The app needs FFmpeg, and it shows a warning at the top of the page if it can't find it. Check this in the same terminal you use to start the app:

```bash
ffmpeg -version
```

If that fails, [install FFmpeg](installation.md#2-install-ffmpeg). If you've just installed it, close the terminal, open a new one and start the app again.

### The file is too large to upload

See [Large files](usage.md#large-files) for how to raise the limit or extract the audio from a video.

### Processing fails on a file you know is valid

Check that the file plays in a media player, and that it contains an audio track. You can also try converting it to WAV:

```bash
ffmpeg -i input_file.m4a -ar 16000 -ac 1 output_file.wav
```

## Memory and GPU problems

### Out of memory

Try these in order, and run the file again after each one:

1. Lower **ASR batch size**: `8`, then `4`, `2`, `1`.
2. Switch from `large-v3` to `medium`.
3. Set **Compute type** to `int8`.
4. Set **Device** to `CPU`.

### "CUDA was selected, but PyTorch cannot see an NVIDIA GPU"

Or: the app always uses the CPU even though you have an NVIDIA GPU.

The most likely cause is that the CPU-only version of PyTorch is installed. Check with:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

If the version ends in `+cpu`, or you see `False`, follow the [GPU steps](installation.md#5-optional-enable-an-nvidia-gpu). Until that's fixed, set **Device** to `Auto` or `CPU`.

### "float16 is not supported for this CPU workflow"

Set **Compute type** to `Auto`, `int8` or `float32`.

### Processing is very slow

This is normal for a CPU, especially with `large-v3`. Try `medium` or `small`, or use a computer with an NVIDIA GPU. See [Choosing a model](usage.md#choosing-a-model).

## Problems with playback and editing

### Audio playback isn't available

The app couldn't create its playback copy of the recording. Check that FFmpeg works, and that your version can create MP3 files:

```bash
ffmpeg -hide_banner -encoders
```

Look for `libmp3lame` in the list. If it's missing, install a full FFmpeg build as described in the [installation guide](installation.md#2-install-ffmpeg), and process the recording again. You can still edit the transcript and download your files in the meantime.

### Clicking a word does nothing

Words in an edited passage can't be clicked individually, because their timings no longer match the text. Click the passage's timestamp, or click **↺** to restore the original.

### The highlight is slightly ahead of or behind the speech

Word timings are estimates, and they're less exact in noisy audio and fast or overlapping speech. Passages with numbers or symbols can have words that aren't highlighted at all, because the aligner couldn't place them.

### I can't see the speaker menu

The menu appears when you hover over a passage or click into it. It's hidden if the app only found one speaker, because there's nobody to reassign the passage to. If a speaker is missing because the speaker count was too low, set the right number and transcribe again.

### The page warns me about leaving

You have corrections that would be lost, because they exist only in the open tab. Stay on the page and download your files first.

## Problems with the results

### My transcript disappeared

Results and corrections exist only in the open browser tab, and they're lost if you refresh it, close it, stop the app or transcribe again. They [can't be recovered or reopened](usage.md#you-can-only-edit-a-transcript-once), so download your files as soon as you've finished.

### My correction isn't in the downloaded file

Corrections take a moment to save. If you click a download button straight after typing, wait a second and click it again. The words CSV is the exception, because it [always shows the original words](usage.md#words-csv).

### "No default align-model for language"

The recording's language doesn't have an alignment model. See [Languages](usage.md#languages). If the language was detected wrongly, enter the correct code in **Language code**.

### The wrong language was detected

Enter the correct code in **Language code**. Detection uses the start of the recording, so silence, music or a short greeting in another language can mislead it.

### Speakers are mixed up

Speaker identification is an estimate, and it's least reliable with overlapping speech, very short turns and similar voices. Check that you've entered the right number of speakers, and [reassign any wrong passages](usage.md#changing-who-said-a-passage). For research where accuracy matters, review the speaker changes against the recording.

### Some words have no timestamps

This is normal. The aligner can't always place numbers, symbols and unclear speech, so those cells stay empty in the words CSV.

## Warnings you can ignore

The terminal can show alarming messages even when everything is working. The following appeared during successful test runs:

| Message | Why it's harmless |
| --- | --- |
| `torchcodec is not installed correctly so built-in audio decoding will fail` | The app loads audio with FFmpeg itself, so it doesn't need this component. |
| `Some weights of Wav2Vec2ForCTC were not initialized...` and `You should probably TRAIN this model` | That part of the model isn't used for alignment. |
| `Lightning automatically upgraded your loaded checkpoint` | A one-off format conversion in memory. |
| `std(): degrees of freedom is <= 0` | An internal calculation in the speaker model, triggered by very short sounds. |
