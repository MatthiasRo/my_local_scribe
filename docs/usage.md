# Usage guide

This guide assumes the app is [installed](installation.md) and running at `http://localhost:8501`.

**Contents**

- [Transcribing a recording](#transcribing-a-recording)
- [Reviewing and editing the transcript](#reviewing-and-editing-the-transcript)
- [Settings](#settings)
- [Choosing a model](#choosing-a-model)
- [Languages](#languages)
- [Naming speakers](#naming-speakers)
- [Export files](#export-files)
- [Large files](#large-files)
- [Splitting a recording](#splitting-a-recording)
- [Getting better results](#getting-better-results)

## Transcribing a recording

1. **Check the settings** in the sidebar. For a two-person interview, you normally only need to confirm the **exact number of speakers** and paste your **Hugging Face token**.
2. **Upload your file.** Drag it onto the upload box, or click **Upload**. You can process one file at a time.
3. **Click Transcribe + diarize.** A progress bar shows the current stage. Keep the tab open until it finishes.
4. **Rename the speakers** when the transcript appears.
5. **[Check and correct the transcript](#reviewing-and-editing-the-transcript)** while listening to the recording.
6. **Download your files.** Use **Download all outputs (.zip)** to get everything at once.

> [!IMPORTANT]
> Your results and corrections exist only in the open browser tab. If you close or refresh it, or stop the app, they're gone and you'll need to process the recording again. Download what you need first.

## Reviewing and editing the transcript

When processing finishes, the **Review and edit** section shows a player above the transcript. The two are linked, so you can move between the text and the recording in either direction.

### From the audio to the text

Press **Play**. The current passage is shaded and the current word is highlighted, and the transcript scrolls along with the recording. Untick **Follow audio** to stop the scrolling. It also pauses by itself while you're typing, so the text doesn't move away from you.

### From the text to the audio

- **Click a word** to move the audio to that word. If the audio is paused, it stays paused, so press **Play** or `Esc` to hear it.
- **Click a timestamp** to start playing from that passage.

### Correcting the text

1. Click into a passage and type. It works like any text field, including undo with `Ctrl+Z`, and your browser's spell check.
2. Press `Enter`, or click somewhere else, when you're done.

Corrections are saved as you type, and they're included in all your downloads. Edited passages have a dotted underline, and the toolbar shows how many you've changed.

- **To undo a correction,** click **↺** next to the passage. This brings back the original text and its word timing.
- **To remove a passage,** such as a false start, delete all of its text. It's left out of the TXT and SRT exports. Click **↺** to bring it back.

> [!NOTE]
> An edited passage is highlighted as a whole during playback, not word by word, because the original word timings no longer match the text.

### Changing who said a passage

If a passage is assigned to the wrong person:

1. Hover over the passage. A speaker menu appears on the right. On a touch screen, it's always shown.
2. Choose the correct speaker.

The speaker headings regroup straight away, and the change is included in all your downloads. Reassigned passages keep the menu visible, with a colored border. To undo the change, choose the original speaker again, or click **↺**, which restores both the passage's text and its speaker.

The menu lists the speakers the app detected, using the names you've given them. A passage can only have one speaker, so if the speaker changes partway through a passage, assign it to whoever says most of it and note the rest in your own copy.

### You can only edit a transcript once

> [!WARNING]
> **The app can't save your work or reopen it yet, so treat each review as a single sitting.**
>
> - Closing or refreshing the page loses your corrections. The browser warns you before you leave.
> - Clicking **Transcribe + diarize** again overwrites the transcript and all your corrections, with no further warning.
> - Downloaded files can't be loaded back into the app. If you need to make more changes later, edit the downloaded files in your usual editor.
>
> So finish your review, then download your files before you leave the page.

### Keyboard shortcuts

These work anywhere in the transcript, including while you're typing:

| Shortcut | Action |
| --- | --- |
| `Esc` | Play or pause |
| `Alt` + `←` | Back 5 seconds |
| `Alt` + `→` | Forward 5 seconds |
| `Enter` | Finish editing a passage |

On a Mac, use `Option` instead of `Alt`.

For difficult passages, try a slower setting in the toolbar's speed menu.

### If there's no audio player

The app creates a small MP3 copy of your recording for the player. If that fails, you'll see a warning. You can still edit the transcript and download your files, but without playback. See [troubleshooting](troubleshooting.md#audio-playback-isnt-available).

## Settings

| Setting | Default | What it does |
| --- | --- | --- |
| **Whisper model** | `large-v3` | The speech recognition model. Larger is more accurate but slower. See [Choosing a model](#choosing-a-model). |
| **Language code** | Blank | Leave blank to detect the language automatically, or enter a code such as `en`, `de` or `es`. Whisper detects the language from the start of the recording, so enter a code if the recording opens in another language or with silence. |
| **Exact number of speakers** | `2` | How many different people speak in the recording, from 1 to 20. The app assigns speech to exactly this many speakers, so a wrong number gives wrong labels. |
| **Device** | `Auto` | `Auto` uses an NVIDIA GPU if one is available, and otherwise the CPU. |
| **Compute type** | `Auto` | Number precision. `Auto` uses `float16` on a GPU and `int8` on a CPU. `float16` doesn't work on a CPU. |
| **ASR batch size** | `8` | How much audio is processed at once. Lower it if you run out of memory. |
| **Hugging Face token** | Blank | Your access token. Leave blank if you've set the `HF_TOKEN` environment variable. |
| **Hugging Face compatibility download mode** | On for Windows | Uses a slower but more reliable download method. Keep it on if downloads hang. It has no effect once models are downloaded. |

## Choosing a model

| Model | Download | Best for |
| --- | --- | --- |
| `large-v3` | 3.1 GB | The best accuracy. Best with a GPU. |
| `medium` | 1.5 GB | A good balance, and a practical choice without a GPU |
| `small` | 486 MB | Faster runs on a CPU, with clear audio |
| `base` | 148 MB | Quick drafts |
| `tiny` | 78 MB | Testing your setup |

**How long will it take?** That depends on your computer, the model and the length of the recording. Without a GPU, a long recording on `large-v3` can take several times its own length. Try a few minutes of audio first to get a feel for your computer's speed. As a reference point, a 45-second clip on `tiny` took about a minute on a CPU-only computer, most of which went on loading the models.

## Languages

Transcription works in the many languages Whisper supports. The word alignment stage is narrower, because it needs a separate model for each language.

These language codes have an alignment model:

`ar` `ca` `cs` `da` `de` `el` `en` `es` `eu` `fa` `fi` `fr` `gl` `he` `hi` `hr` `hu` `id` `it` `ja` `ka` `ko` `lv` `ml` `nl` `nn` `no` `pl` `pt` `ro` `ru` `sk` `sl` `sv` `te` `tl` `tr` `uk` `ur` `vi` `zh`

> [!WARNING]
> A recording in any other language currently fails with a "No default align-model" error after transcription finishes, and that transcription is lost.

The alignment model for each language downloads the first time you use it, so you need an internet connection for your first recording in a new language. French, German, Spanish and Italian models come from `download.pytorch.org`, which some networks block. See [troubleshooting](troubleshooting.md#a-language-model-wont-download) if this affects you.

## Naming speakers

Speaker identification doesn't know who anyone is. It only groups together speech that sounds like the same voice, and the app numbers those groups in the order they first speak.

Enter names such as `Interviewer` and `Participant` in the **Speaker names** fields. The transcript and all your downloads update immediately, without processing the recording again.

If the app can't assign part of the speech to anyone, it's labelled **Unknown speaker**, and you can rename that too.

## Export files

Each file name starts with the name of your recording. Characters other than letters, numbers, hyphens and underscores are replaced with `_`.

| File | Contains | Good for |
| --- | --- | --- |
| `*_transcript.txt` | The transcript, with consecutive speech by the same person merged into turns | Reading, coding and sharing |
| `*_segments.csv` | One row per segment, with timestamps and speakers | Spreadsheets and analysis |
| `*_words.csv` | One row per word, with timestamps and a confidence score | Detailed analysis |
| `*_transcript.srt` | Subtitles, with the speaker's name in each line | Video players and subtitle editors |
| `*_transcript.json` | Everything above, plus the settings used for the run | Software and record-keeping |
| `*_transcription_bundle.zip` | All five files | Saving everything at once |

### TXT

Speech by the same person is merged into one turn when the pause between segments is 1.25 seconds or less. This uses your corrected speakers, so reassigning a passage can join or split turns.

```text
[00:00:00.131 - 00:00:05.795] Interviewer
Thank you for joining me today. Could you tell me a little about how you started working in this field?

[00:00:06.776 - 00:00:14.382] Participant
Of course. I began about 10 years ago as a research assistant at a small university in the north of the country.
```

### Segments CSV

Columns: `start`, `end`, `start_time`, `end_time`, `speaker_id`, `speaker`, `text`, `edited`, `speaker_changed`.

- `start` and `end` are in seconds, and `start_time` and `end_time` are the same values as `HH:MM:SS.mmm`.
- `speaker_id` is the app's internal label, such as `SPEAKER_00`. `speaker` is the name you chose.
- `edited` is `yes` if you corrected that passage. Passages you removed stay in this file with empty text.
- `speaker_changed` is `yes` if you moved that passage to a different speaker. `speaker_id` and `speaker` show the new speaker.

### Words CSV

Columns: `start`, `end`, `start_time`, `end_time`, `speaker_id`, `speaker`, `word`, `score`, `segment_edited`, `segment_speaker_changed`.

`score` is the alignment model's confidence from 0 to 1. Timing columns can be empty for words the aligner couldn't place, which is common for numbers and symbols.

This file always shows the words as they were originally recognized, because its timings come from the audio. Your text corrections don't appear here. `segment_edited` is `yes` for words in a passage you corrected, so you can filter them out.

Speaker changes do appear here: every word in a reassigned passage moves to the new speaker, and `segment_speaker_changed` is `yes`.

Both CSV files are saved in a UTF-8 format that Excel opens correctly, so accented characters display properly.

### SRT

```text
1
00:00:00,131 --> 00:00:01,592
Interviewer: Thank you for joining me today.
```

### JSON

The file has two parts:

- `metadata` records the source file name, model, language, speaker count, device, compute type, library versions, your speaker names, and the number of edited and reassigned passages. This helps you document how a transcript was produced. `whisperx_version` currently always shows `unknown`.
- `result` holds the full segments and words. Each segment has `edited` and `speaker_changed` values. Corrected segments also keep the machine's version in `original_text`, and reassigned segments keep theirs in `original_speaker_id`.

## Large files

The upload limit is **200 MB** by default. Audio interviews usually fit, but video files often don't. To raise the limit:

1. Open `.streamlit/config.toml` in the project folder.
2. Find the line `# maxUploadSize = 2048`, and remove the `# ` at the start. The number is in megabytes.
3. Restart the app.

The app holds the whole file in memory while it runs, so keep the limit well below your computer's RAM.

If a video is too big, you can also extract just the audio, which is much smaller and is all the app needs:

```bash
ffmpeg -i interview.mp4 -vn -c:a aac -b:a 128k interview.m4a
```

## Splitting a recording

`split_audio.py` is a separate helper that cuts a recording into **2-minute parts**. It's useful for creating short test clips.

```bash
python split_audio.py "path/to/interview.m4a"
```

The parts are saved next to the original as `interview_part_001.m4a`, `interview_part_002.m4a` and so on. Your original isn't changed. The script keeps only the first audio track and copies it without re-encoding, so it's fast and doesn't reduce quality.

To change the length, edit `SEGMENT_LENGTH_SECONDS` at the top of the script.

> [!NOTE]
> Avoid splitting as a way to handle long interviews. Each part is processed separately, so timestamps restart from zero and `Speaker 1` in one part may be `Speaker 2` in the next. Raising the [upload limit](#large-files) gives better results.

## Getting better results

- **Enter the correct number of speakers.** This helps speaker identification more than any other setting.
- **Enter the language code** if you know it, especially if the recording doesn't start with clear speech.
- **Use the best recording you have.** Background noise, distant microphones and people talking over each other all reduce accuracy.
- **Use a larger model** when accuracy matters and you have time to wait.
- **[Check the transcript against the audio.](#reviewing-and-editing-the-transcript)** Names, technical terms and speaker changes are the most likely places to find mistakes.
