from __future__ import annotations

import csv
import gc
import io
import inspect
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import uuid
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import streamlit as st

from transcript_editor import PLAYER_CONTAINER_KEY, transcript_editor


APP_TITLE = "My Local Scribe"
SUPPORTED_TYPES = ["wav", "mp3", "m4a", "flac", "aac", "ogg", "mp4", "mov", "mkv", "webm"]
MODEL_OPTIONS = ["large-v3", "medium", "small", "base", "tiny"]
WHISPER_MODEL_REPOS = {
    "large-v3": "Systran/faster-whisper-large-v3",
    "medium": "Systran/faster-whisper-medium",
    "small": "Systran/faster-whisper-small",
    "base": "Systran/faster-whisper-base",
    "tiny": "Systran/faster-whisper-tiny",
}
WHISPER_MODEL_PATTERNS = {
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
}

# WhisperX defaults to torchaudio's WAV2VEC2_ASR_BASE_960H for English
# alignment, which downloads from download.pytorch.org on first use.  On
# networks where that host is blocked/unresolvable, use the corresponding
# public Hugging Face Wav2Vec2 CTC checkpoint instead so all model downloads
# go through the same Hugging Face cache/download path.
ENGLISH_ALIGN_MODEL_REPO = "facebook/wav2vec2-base-960h"
ENGLISH_ALIGN_ALLOW_PATTERNS = [
    "config.json",
    "preprocessor_config.json",
    "feature_extractor_config.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "model.safetensors",
]
DIARIZATION_MODEL_REPO = "pyannote/speaker-diarization-community-1"

# pyannote.audio reports usage metrics (audio duration, speaker counts) to
# otel.pyannote.ai unless told otherwise, which does not fit a local-first tool.
# This must run before pyannote is imported. setdefault() keeps it overridable:
# anyone who wants to share these metrics can set the variables themselves.
os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "false")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


st.set_page_config(page_title=APP_TITLE, page_icon="🎙️", layout="wide")


def clear_cuda_cache() -> None:
    """Best-effort GPU cleanup between large models."""
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def resolve_device(choice: str) -> str:
    import torch

    if choice == "CPU":
        return "cpu"
    if choice == "CUDA (NVIDIA GPU)":
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA was selected, but PyTorch cannot see an NVIDIA GPU. "
                "Choose Auto/CPU or fix your CUDA/PyTorch installation."
            )
        return "cuda"
    return "cuda" if torch.cuda.is_available() else "cpu"


def resolve_compute_type(choice: str, device: str) -> str:
    if choice != "Auto":
        return choice
    return "float16" if device == "cuda" else "int8"


def hms(seconds: float | int | None) -> str:
    if seconds is None or (isinstance(seconds, float) and math.isnan(seconds)):
        return "00:00:00.000"
    total_ms = max(0, int(round(float(seconds) * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def srt_time(seconds: float | int | None) -> str:
    return hms(seconds).replace(".", ",")


def safe_stem(filename: str) -> str:
    stem = Path(filename).stem.strip() or "transcript"
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)


def speaker_ids_in_order(segments: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for seg in segments:
        spk = seg.get("speaker")
        if spk and spk not in seen:
            seen.append(spk)
        for word in seg.get("words") or []:
            wspk = word.get("speaker")
            if wspk and wspk not in seen:
                seen.append(wspk)
    if not seen:
        seen.append("UNKNOWN")
    return seen


def make_display_rows(
    segments: list[dict[str, Any]],
    name_map: dict[str, str],
    edits: dict[str, str] | None = None,
    speaker_changes: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Build export rows, keyed by segment index for ``edits`` and ``speaker_changes``.

    ``edits`` holds corrected text, and ``speaker_changes`` holds reassigned speaker IDs.
    """
    edits = edits or {}
    speaker_changes = speaker_changes or {}
    rows: list[dict[str, Any]] = []
    for index, seg in enumerate(segments):
        raw = speaker_changes.get(str(index)) or seg.get("speaker") or "UNKNOWN"
        edited_text = edits.get(str(index))
        rows.append(
            {
                "start": float(seg.get("start", 0.0) or 0.0),
                "end": float(seg.get("end", seg.get("start", 0.0)) or 0.0),
                "speaker_id": raw,
                "speaker": name_map.get(raw, raw),
                "text": str(seg.get("text", "")).strip() if edited_text is None else edited_text.strip(),
                "edited": edited_text is not None,
                "speaker_changed": str(index) in speaker_changes,
            }
        )
    return rows


def merge_turns(rows: list[dict[str, Any]], max_gap: float = 1.25) -> list[dict[str, Any]]:
    """Merge adjacent aligned segments from the same speaker for readable TXT output."""
    merged: list[dict[str, Any]] = []
    for row in rows:
        if not row["text"]:
            continue
        if (
            merged
            and merged[-1]["speaker_id"] == row["speaker_id"]
            and row["start"] - merged[-1]["end"] <= max_gap
        ):
            merged[-1]["end"] = max(merged[-1]["end"], row["end"])
            merged[-1]["text"] = (merged[-1]["text"].rstrip() + " " + row["text"].lstrip()).strip()
        else:
            merged.append(dict(row))
    return merged


def build_txt(turns: list[dict[str, Any]]) -> str:
    blocks = []
    for t in turns:
        blocks.append(
            f"[{hms(t['start'])} - {hms(t['end'])}] {t['speaker']}\n{t['text']}"
        )
    return "\n\n".join(blocks).strip() + "\n"


def build_csv(rows: list[dict[str, Any]]) -> str:
    out = io.StringIO(newline="")
    writer = csv.DictWriter(
        out,
        fieldnames=[
            "start",
            "end",
            "start_time",
            "end_time",
            "speaker_id",
            "speaker",
            "text",
            "edited",
            "speaker_changed",
        ],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(
            {
                "start": f"{r['start']:.3f}",
                "end": f"{r['end']:.3f}",
                "start_time": hms(r["start"]),
                "end_time": hms(r["end"]),
                "speaker_id": r["speaker_id"],
                "speaker": r["speaker"],
                "text": r["text"],
                "edited": "yes" if r["edited"] else "no",
                "speaker_changed": "yes" if r["speaker_changed"] else "no",
            }
        )
    return out.getvalue()


def build_word_csv(
    segments: list[dict[str, Any]],
    name_map: dict[str, str],
    edits: dict[str, str] | None = None,
    speaker_changes: dict[str, str] | None = None,
) -> str:
    """Build the word table.

    Word timings come from the audio, so they always show the original recognized
    words. ``segment_edited`` flags the words whose passage was later corrected.
    A reassigned passage moves all of its words to the new speaker.
    """
    edits = edits or {}
    speaker_changes = speaker_changes or {}
    out = io.StringIO(newline="")
    writer = csv.DictWriter(
        out,
        fieldnames=[
            "start",
            "end",
            "start_time",
            "end_time",
            "speaker_id",
            "speaker",
            "word",
            "score",
            "segment_edited",
            "segment_speaker_changed",
        ],
    )
    writer.writeheader()
    for index, seg in enumerate(segments):
        seg_spk = seg.get("speaker") or "UNKNOWN"
        new_speaker = speaker_changes.get(str(index))
        for w in seg.get("words") or []:
            raw = new_speaker or w.get("speaker") or seg_spk
            start = w.get("start")
            end = w.get("end")
            writer.writerow(
                {
                    "start": "" if start is None else f"{float(start):.3f}",
                    "end": "" if end is None else f"{float(end):.3f}",
                    "start_time": "" if start is None else hms(float(start)),
                    "end_time": "" if end is None else hms(float(end)),
                    "speaker_id": raw,
                    "speaker": name_map.get(raw, raw),
                    "word": str(w.get("word", "")).strip(),
                    "score": "" if w.get("score") is None else w.get("score"),
                    "segment_edited": "yes" if str(index) in edits else "no",
                    "segment_speaker_changed": "yes" if new_speaker else "no",
                }
            )
    return out.getvalue()


def build_srt(rows: list[dict[str, Any]]) -> str:
    blocks = []
    idx = 1
    for r in rows:
        if not r["text"]:
            continue
        blocks.append(
            f"{idx}\n{srt_time(r['start'])} --> {srt_time(r['end'])}\n{r['speaker']}: {r['text']}"
        )
        idx += 1
    return "\n\n".join(blocks).strip() + "\n"


def json_default(obj: Any) -> Any:
    try:
        import numpy as np

        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except Exception:
        pass
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    return str(obj)


def build_json(
    raw_result: dict[str, Any],
    name_map: dict[str, str],
    metadata: dict[str, Any],
    edits: dict[str, str] | None = None,
    speaker_changes: dict[str, str] | None = None,
) -> str:
    edits = edits or {}
    speaker_changes = speaker_changes or {}
    result = deepcopy(raw_result)
    for index, seg in enumerate(result.get("segments", [])):
        raw = seg.get("speaker") or "UNKNOWN"
        new_speaker = speaker_changes.get(str(index))
        seg["speaker_changed"] = new_speaker is not None
        if new_speaker:
            seg["original_speaker_id"] = raw
            raw = new_speaker
        seg["speaker_id"] = raw
        seg["speaker"] = name_map.get(raw, raw)
        seg["edited"] = str(index) in edits
        if seg["edited"]:
            seg["original_text"] = seg.get("text", "")
            seg["text"] = edits[str(index)].strip()
        for w in seg.get("words") or []:
            wraw = new_speaker or w.get("speaker") or raw
            w["speaker_id"] = wraw
            w["speaker"] = name_map.get(wraw, wraw)
    payload = {"metadata": metadata, "result": result}
    return json.dumps(payload, ensure_ascii=False, indent=2, default=json_default)


def build_zip(files: dict[str, bytes]) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, data in files.items():
            zf.writestr(filename, data)
    return bio.getvalue()


def progress_mapper(
    progress_bar,
    status_slot,
    start_pct: int,
    end_pct: int,
    label: str,
) -> Callable[[float], None]:
    def callback(inner_pct: float) -> None:
        inner = min(100.0, max(0.0, float(inner_pct)))
        overall = int(round(start_pct + (end_pct - start_pct) * inner / 100.0))
        progress_bar.progress(overall, text=f"{label}: {inner:.0f}%")
        status_slot.caption(f"{label}: {inner:.0f}%")

    return callback


def configure_huggingface_downloads(disable_xet: bool) -> None:
    """Configure conservative Hugging Face network behavior before importing HF clients."""
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "15")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
    # Whisper repositories are public; do not implicitly attach the pyannote token to them.
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    if disable_xet:
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    else:
        os.environ.pop("HF_HUB_DISABLE_XET", None)

    # Streamlit hot-reload can leave huggingface_hub imported in the same Python process.
    # Mirror the environment choice into the already-imported constants when possible.
    try:
        from huggingface_hub import constants as hf_constants

        hf_constants.HF_HUB_DISABLE_XET = bool(disable_xet)
        hf_constants.HF_HUB_DISABLE_IMPLICIT_TOKEN = True
    except Exception:
        pass


def _human_bytes(value: int | float | None) -> str:
    if not value:
        return "unknown size"
    n = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def ensure_whisper_model_cached(
    model_name: str,
    progress_bar,
    status_slot,
) -> Path:
    """Resolve/download the faster-whisper model explicitly, then return its local snapshot directory.

    This avoids hiding first-run network activity inside whisperx.load_model().
    """
    import huggingface_hub
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    from huggingface_hub.constants import HF_HUB_CACHE
    from tqdm.auto import tqdm

    repo_id = WHISPER_MODEL_REPOS.get(model_name)
    if repo_id is None:
        # Custom/unknown Whisper IDs can still be handled by WhisperX directly, but all UI choices
        # are intentionally mapped above so that downloads are observable.
        raise ValueError(f"No download mapping is configured for Whisper model: {model_name}")

    allow_patterns = [
        "config.json",
        "preprocessor_config.json",
        "model.bin",
        "tokenizer.json",
        "vocabulary.*",
    ]

    # Fast path: if a complete snapshot is already cached, do not touch the network at all.
    try:
        cached_dir = snapshot_download(
            repo_id=repo_id,
            cache_dir=HF_HUB_CACHE,
            allow_patterns=allow_patterns,
            local_files_only=True,
        )
        cached_path = Path(cached_dir)
        required = [cached_path / "config.json", cached_path / "model.bin", cached_path / "tokenizer.json"]
        has_vocab = any(cached_path.glob("vocabulary.*"))
        if all(path.is_file() for path in required) and has_vocab:
            progress_bar.progress(17, text=f"Whisper model already cached ({model_name})")
            status_slot.caption(f"Using cached Whisper model: {cached_dir}")
            return cached_path
    except Exception:
        pass

    progress_bar.progress(5, text=f"Checking Whisper model download ({model_name})")
    status_slot.caption(f"Contacting Hugging Face for {repo_id} …")

    # Public ASR model: intentionally avoid using the user's gated-model token here.
    api = HfApi(token=False)
    info = api.model_info(repo_id, files_metadata=True)
    siblings = list(info.siblings or [])
    wanted = []
    for item in siblings:
        name = item.rfilename
        if name in WHISPER_MODEL_PATTERNS or name.startswith("vocabulary."):
            wanted.append((name, int(item.size or 0)))

    if not wanted:
        raise RuntimeError(f"Could not resolve model files for {repo_id}.")

    total_bytes = sum(size for _, size in wanted) or 1
    finished_bytes = 0
    local_paths: list[Path] = []

    for idx, (filename, file_size) in enumerate(wanted, start=1):
        status_slot.caption(
            f"Whisper download {idx}/{len(wanted)}: {filename} ({_human_bytes(file_size)})"
        )

        done_before = finished_bytes

        class StreamlitDownloadTqdm(tqdm):
            def update(self, n=1):  # type: ignore[override]
                result = super().update(n)
                current = min(float(self.n), float(file_size or self.total or 0))
                overall_fraction = min(1.0, (done_before + current) / total_bytes)
                overall_pct = 5 + int(round(12 * overall_fraction))
                progress_bar.progress(
                    overall_pct,
                    text=f"Downloading Whisper model: {filename}",
                )
                if self.total:
                    status_slot.caption(
                        f"Whisper download {idx}/{len(wanted)}: {filename} · "
                        f"{_human_bytes(self.n)} / {_human_bytes(self.total)}"
                    )
                return result

        # huggingface_hub <=0.36.x does not expose ``tqdm_class`` on
        # hf_hub_download(), while newer releases do. WhisperX 3.8.6 can install
        # either family depending on the environment, so feature-detect instead
        # of assuming a particular Hub version.
        download_kwargs: dict[str, Any] = {
            "repo_id": repo_id,
            "filename": filename,
            "revision": info.sha,
            "cache_dir": HF_HUB_CACHE,
            "token": False,
            "force_download": False,
        }
        supports_custom_tqdm = "tqdm_class" in inspect.signature(hf_hub_download).parameters
        if supports_custom_tqdm:
            download_kwargs["tqdm_class"] = StreamlitDownloadTqdm
        else:
            status_slot.caption(
                f"Whisper download {idx}/{len(wanted)}: {filename} "
                f"({_human_bytes(file_size)}) · downloading with "
                f"huggingface_hub {huggingface_hub.__version__}"
            )

        local_file = hf_hub_download(**download_kwargs)
        local_paths.append(Path(local_file))
        finished_bytes += file_size
        progress_bar.progress(
            5 + int(round(12 * min(1.0, finished_bytes / total_bytes))),
            text=f"Downloaded Whisper model file {idx}/{len(wanted)}",
        )

    # Every downloaded file is in the same resolved snapshot directory.
    model_dir = local_paths[0].parent
    progress_bar.progress(17, text=f"Whisper model download complete ({model_name})")
    status_slot.caption(f"Whisper model cached at: {model_dir}")
    return model_dir


def ensure_hf_snapshot_cached(
    repo_id: str,
    label: str,
    progress_bar,
    status_slot,
    start_pct: int,
    end_pct: int,
    *,
    token: str | bool | None = False,
    allow_patterns: list[str] | None = None,
    required_files: tuple[str, ...] = (),
) -> Path:
    """Resolve/download a Hugging Face repository and return its local snapshot path.

    The function first checks the local cache without touching the network.  If
    files are missing it performs an explicit snapshot download so Streamlit
    shows which model is being retrieved instead of appearing frozen inside a
    downstream library call.
    """
    from huggingface_hub import snapshot_download
    from huggingface_hub.constants import HF_HUB_CACHE
    from tqdm.auto import tqdm

    common_kwargs: dict[str, Any] = {
        "repo_id": repo_id,
        "cache_dir": HF_HUB_CACHE,
        "token": token,
    }
    if allow_patterns is not None:
        common_kwargs["allow_patterns"] = allow_patterns

    # Offline/cache-only fast path.
    try:
        cached_dir = snapshot_download(
            **common_kwargs,
            local_files_only=True,
        )
        cached_path = Path(cached_dir)
        if all((cached_path / rel).is_file() for rel in required_files):
            progress_bar.progress(end_pct, text=f"{label} already cached")
            status_slot.caption(f"Using cached {label}: {cached_dir}")
            return cached_path
    except Exception:
        pass

    progress_bar.progress(start_pct, text=f"Downloading {label}")
    status_slot.caption(f"First-run download from Hugging Face: {repo_id}")

    class StreamlitSnapshotTqdm(tqdm):
        def update(self, n=1):  # type: ignore[override]
            result = super().update(n)
            if self.total:
                fraction = min(1.0, float(self.n) / float(self.total))
                pct = start_pct + int(round((end_pct - start_pct) * fraction))
                progress_bar.progress(pct, text=f"Downloading {label}")
                status_slot.caption(
                    f"Downloading {label}: {self.n:.0f}/{self.total:.0f} files"
                )
            return result

    online_kwargs = dict(common_kwargs)
    online_kwargs["local_files_only"] = False
    if "tqdm_class" in inspect.signature(snapshot_download).parameters:
        online_kwargs["tqdm_class"] = StreamlitSnapshotTqdm

    try:
        downloaded_dir = snapshot_download(**online_kwargs)
    except Exception as exc:
        raise RuntimeError(
            f"Could not download {label} from Hugging Face ({repo_id}). "
            f"Original error: {exc}"
        ) from exc

    downloaded_path = Path(downloaded_dir)
    missing = [rel for rel in required_files if not (downloaded_path / rel).is_file()]
    if missing:
        raise RuntimeError(
            f"{label} download completed but required files are missing: "
            + ", ".join(missing)
        )

    progress_bar.progress(end_pct, text=f"{label} download complete")
    status_slot.caption(f"{label} cached at: {downloaded_dir}")
    return downloaded_path


def ensure_nltk_punkt_tab(progress_bar, status_slot, start_pct: int, end_pct: int) -> None:
    """Make WhisperX sentence-tokenization data explicit instead of downloading silently."""
    import nltk

    try:
        nltk.data.find("tokenizers/punkt_tab")
        progress_bar.progress(end_pct, text="NLTK sentence data already cached")
        return
    except LookupError:
        pass

    progress_bar.progress(start_pct, text="Downloading NLTK sentence data")
    status_slot.caption("First-run download: NLTK punkt_tab sentence tokenizer…")
    try:
        ok = nltk.download("punkt_tab", quiet=True)
    except Exception as exc:
        raise RuntimeError(
            "Could not download NLTK punkt_tab data required by WhisperX alignment. "
            f"Original error: {exc}"
        ) from exc

    if not ok:
        raise RuntimeError(
            "NLTK punkt_tab download failed. Run `python -m nltk.downloader punkt_tab` "
            "once from the app's Python environment, then retry."
        )

    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError as exc:
        raise RuntimeError(
            "NLTK reported a successful punkt_tab download, but the data could not be found."
        ) from exc

    progress_bar.progress(end_pct, text="NLTK sentence data ready")
    status_slot.caption("NLTK punkt_tab is cached locally.")


def create_playback_audio(input_path: Path) -> bytes | None:
    """Make a small MP3 copy of the recording for the player, or None if that fails.

    Browsers can't play every format the app accepts (MKV and MOV, for example), and
    a video file would be needlessly large. Playback is a convenience, so a failure
    here must never cost the user a finished transcript.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    output_path = input_path.with_name("playback.mp3")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-nostdin",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-c:a", "libmp3lame",
        "-b:a", "64k",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return output_path.read_bytes()
    except (OSError, subprocess.CalledProcessError):
        return None


def transcribe_file(
    input_path: Path,
    model_name: str,
    language: str | None,
    num_speakers: int,
    device_choice: str,
    compute_choice: str,
    batch_size: int,
    hf_token: str,
    disable_xet: bool,
    progress_bar,
    status_slot,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run local WhisperX transcription + alignment + pyannote Community-1 diarization."""
    configure_huggingface_downloads(disable_xet=disable_xet)

    # Resolve first-run model downloads explicitly so network stalls are visible rather than
    # appearing as a frozen whisperx.load_model() call.
    model_dir = ensure_whisper_model_cached(model_name, progress_bar, status_slot)

    import torch
    import whisperx
    from whisperx.diarize import DiarizationPipeline

    device = resolve_device(device_choice)
    compute_type = resolve_compute_type(compute_choice, device)

    if device == "cpu" and compute_type == "float16":
        raise RuntimeError("float16 is not supported for this CPU workflow. Choose Auto, int8, or float32.")

    progress_bar.progress(18, text="Loading audio")
    status_slot.caption("Loading audio locally…")
    audio = whisperx.load_audio(str(input_path))

    progress_bar.progress(20, text=f"Loading cached Whisper model ({model_name})")
    status_slot.caption(f"Initializing WhisperX ASR model from local cache: {model_name}")
    model = whisperx.load_model(
        str(model_dir),
        device,
        compute_type=compute_type,
        local_files_only=True,
        language=language.lower().strip() if language else None,
    )

    asr_cb = progress_mapper(progress_bar, status_slot, 22, 54, "Transcription")
    transcribe_kwargs: dict[str, Any] = {
        "batch_size": int(batch_size),
        "progress_callback": asr_cb,
    }
    if language:
        transcribe_kwargs["language"] = language.lower().strip()

    result = model.transcribe(audio, **transcribe_kwargs)
    detected_language = result.get("language") or language or "unknown"

    del model
    clear_cuda_cache()

    # English WhisperX normally uses torchaudio's WAV2VEC2_ASR_BASE_960H,
    # whose first-run download comes from download.pytorch.org.  Route English
    # alignment through Hugging Face instead so it uses the same cache/network
    # path as the Whisper model and can be loaded strictly from disk afterward.
    if str(detected_language).lower() == "en":
        progress_bar.progress(55, text="Preparing English alignment model")
        align_model_dir = ensure_hf_snapshot_cached(
            repo_id=ENGLISH_ALIGN_MODEL_REPO,
            label="English Wav2Vec2 alignment model",
            progress_bar=progress_bar,
            status_slot=status_slot,
            start_pct=55,
            end_pct=59,
            token=False,
            allow_patterns=ENGLISH_ALIGN_ALLOW_PATTERNS,
            required_files=("config.json", "vocab.json", "model.safetensors"),
        )
        progress_bar.progress(60, text="Loading cached English alignment model")
        status_slot.caption("Initializing English forced-alignment model from local cache…")
        align_model, metadata = whisperx.load_align_model(
            language_code="en",
            device=device,
            model_name=str(align_model_dir),
            model_cache_only=True,
        )
        alignment_model_name = ENGLISH_ALIGN_MODEL_REPO
    else:
        # Keep WhisperX's tested language-specific defaults for non-English audio.
        # Some of those models may perform a one-time download on first use.
        progress_bar.progress(55, text=f"Loading alignment model ({detected_language})")
        status_slot.caption(f"Loading forced-alignment model for: {detected_language}")
        align_model, metadata = whisperx.load_align_model(
            language_code=detected_language,
            device=device,
        )
        alignment_model_name = "WhisperX default"

    # WhisperX 3.8.6 uses NLTK punkt_tab for sentence boundaries during alignment.
    ensure_nltk_punkt_tab(progress_bar, status_slot, start_pct=60, end_pct=61)

    align_cb = progress_mapper(progress_bar, status_slot, 62, 74, "Word-level alignment")
    result = whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
        progress_callback=align_cb,
    )

    del align_model
    clear_cuda_cache()

    # Let pyannote/WhisperX resolve Community-1 using its supported loader.
    # Community-1 is a pipeline repository whose config.yaml points to several
    # nested assets (segmentation, embedding, PLDA).  Manually snapshotting and
    # validating the repository can produce false "config.yaml missing" errors
    # with some huggingface_hub/cache combinations on Windows.  The official
    # Pipeline.from_pretrained path handles the repository layout and caches the
    # required assets automatically.
    progress_bar.progress(75, text="Loading pyannote Community-1")
    status_slot.caption(
        "Initializing pyannote Community-1. On the first run, pyannote may download "
        "its diarization assets from Hugging Face; later runs use the local cache."
    )
    try:
        diarize_model = DiarizationPipeline(
            model_name=DIARIZATION_MODEL_REPO,
            token=hf_token,
            device=device,
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not load pyannote Community-1. Make sure you have accepted the "
            "Community-1 access conditions on Hugging Face and that HF_TOKEN is valid. "
            f"Original error: {exc}"
        ) from exc

    progress_bar.progress(80, text="pyannote Community-1 ready")
    diarize_cb = progress_mapper(progress_bar, status_slot, 81, 95, "Speaker diarization")
    diarize_segments = diarize_model(
        audio,
        num_speakers=int(num_speakers),
        progress_callback=diarize_cb,
    )

    progress_bar.progress(96, text="Assigning speakers to words")
    status_slot.caption("Reconciling speaker turns with word timestamps…")
    result = whisperx.assign_word_speakers(diarize_segments, result)

    del diarize_model
    clear_cuda_cache()

    progress_bar.progress(100, text="Complete")
    status_slot.caption("Processing complete.")

    run_metadata = {
        "model": model_name,
        "language": detected_language,
        "requested_speakers": int(num_speakers),
        "device": device,
        "compute_type": compute_type,
        "whisperx_version": getattr(whisperx, "__version__", "unknown"),
        "torch_version": getattr(torch, "__version__", "unknown"),
        "alignment_model": alignment_model_name,
        "diarization_model": DIARIZATION_MODEL_REPO,
    }
    return result, run_metadata


def main() -> None:
    st.title(f"🎙️ {APP_TITLE}")
    st.write(
        "Drag in an audio/video file, transcribe it with WhisperX, align words to timestamps, "
        "and label speakers with pyannote Community-1. Processing runs on the machine hosting this app."
    )

    with st.expander("Privacy and first-run model downloads", expanded=False):
        st.markdown(
            "- If you run this app on **your own computer** (for example at `localhost`), the uploaded audio stays on that computer.\n"
            "- The uploaded file is copied to a temporary folder only while processing and is then deleted.\n"
            "- On the **first run**, Whisper/alignment/pyannote model files and NLTK sentence data may be downloaded. "
            "The audio itself is not sent there by this app.\n"
            "- Usage reporting by pyannote and Streamlit is switched off when you start the app from the project folder.\n"
            "- Do **not** deploy this app to Streamlit Community Cloud or another remote server if you require local-only handling of sensitive audio."
        )

    if shutil.which("ffmpeg") is None:
        st.warning(
            "FFmpeg was not found on PATH. MP3/M4A/MP4 decoding will usually fail until FFmpeg is installed. "
            "WAV may still work in some configurations."
        )

    with st.sidebar:
        st.header("Processing options")
        model_name = st.selectbox(
            "Whisper model",
            MODEL_OPTIONS,
            index=0,
            help="large-v3 is the accuracy-first default. Smaller models use less memory and run faster.",
        )
        language_text = st.text_input(
            "Language code (optional)",
            value="",
            placeholder="Leave blank for auto-detect; e.g. en, es, de",
            help="Leaving this blank lets Whisper detect the language.",
        )
        num_speakers = st.number_input(
            "Exact number of speakers",
            min_value=1,
            max_value=20,
            value=2,
            step=1,
            help="For a typical interviewer + participant recording, use 2.",
        )

        st.divider()
        device_choice = st.selectbox(
            "Device",
            ["Auto", "CUDA (NVIDIA GPU)", "CPU"],
            index=0,
        )
        compute_choice = st.selectbox(
            "Compute type",
            ["Auto", "float16", "int8", "float32"],
            index=0,
            help="Auto uses float16 on CUDA and int8 on CPU.",
        )
        batch_size = st.number_input(
            "ASR batch size",
            min_value=1,
            max_value=64,
            value=8,
            step=1,
            help="Lower this if you run out of GPU memory. 4–8 is a conservative starting point.",
        )

        st.divider()
        env_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or ""
        hf_token_input = st.text_input(
            "Hugging Face token",
            value="",
            type="password",
            placeholder="Uses HF_TOKEN env var if left blank" if env_token else "Required for first pyannote download",
            help=(
                "Needed to download the gated pyannote Community-1 model after you accept its user conditions. "
                "You can instead set HF_TOKEN in your environment."
            ),
        )
        disable_xet = st.checkbox(
            "Hugging Face compatibility download mode",
            value=sys.platform.startswith("win"),
            help=(
                "Disables the newer Xet transfer backend and uses the regular HTTP download path. "
                "Recommended on Windows if model downloads hang. Cached models are unaffected."
            ),
        )

    uploaded = st.file_uploader(
        "Audio or video file",
        type=SUPPORTED_TYPES,
        accept_multiple_files=False,
        help="Common formats such as M4A, MP3, WAV, FLAC, MP4, and MOV are supported through FFmpeg.",
    )

    if uploaded is not None:
        try:
            st.audio(uploaded)
        except Exception:
            pass
        size_mb = uploaded.size / (1024 * 1024)
        st.caption(f"Selected: **{uploaded.name}** · {size_mb:.1f} MB")

    # Shown whenever results exist, not only once edits exist: an element appearing
    # above the editor mid-session could interrupt typing or playback.
    if "transcription_result" in st.session_state:
        st.warning(
            "Transcribing again **overwrites the current transcript and all your edits**. "
            "Download your files first."
        )

    run = st.button("Transcribe + diarize", type="primary", disabled=uploaded is None)

    if run and uploaded is not None:
        hf_token = hf_token_input.strip() or env_token
        if not hf_token:
            st.error(
                "A Hugging Face token is required to load pyannote Community-1 the first time. "
                "Enter it in the sidebar or set the HF_TOKEN environment variable."
            )
            st.stop()

        progress_bar = st.progress(0, text="Starting")
        status_slot = st.empty()

        try:
            suffix = Path(uploaded.name).suffix or ".audio"
            with tempfile.TemporaryDirectory(prefix="local_transcriber_") as tmpdir:
                input_path = Path(tmpdir) / f"input{suffix}"
                input_path.write_bytes(uploaded.getvalue())

                result, metadata = transcribe_file(
                    input_path=input_path,
                    model_name=model_name,
                    language=language_text.strip() or None,
                    num_speakers=int(num_speakers),
                    device_choice=device_choice,
                    compute_choice=compute_choice,
                    batch_size=int(batch_size),
                    hf_token=hf_token,
                    disable_xet=disable_xet,
                    progress_bar=progress_bar,
                    status_slot=status_slot,
                )

                progress_bar.progress(100, text="Preparing audio for playback")
                status_slot.caption("Creating a small audio copy for the transcript player…")
                playback_audio = create_playback_audio(input_path)

            st.session_state["transcription_result"] = result
            st.session_state["transcription_metadata"] = metadata
            st.session_state["transcription_source"] = uploaded.name
            st.session_state["transcription_run_id"] = uuid.uuid4().hex[:8]
            st.session_state["transcription_audio"] = playback_audio
            st.session_state["transcription_just_finished"] = True
            # Rerun so the progress bar is gone before the editor appears. Elements
            # disappearing above the editor later could interrupt playback or typing.
            st.rerun()

        except Exception as exc:
            progress_bar.empty()
            status_slot.empty()
            st.error(f"Processing failed: {exc}")
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
            st.info(
                "Common causes: FFmpeg is missing; Hugging Face or NLTK is unreachable; the pyannote model conditions were not accepted; "
                "the token lacks access; CUDA/PyTorch is misconfigured; or the selected model/batch size exceeds available VRAM. "
                "For English, this version intentionally downloads the alignment model from Hugging Face rather than download.pytorch.org. "
                "If a first-run Hugging Face download hangs on Windows, leave compatibility download mode enabled and fully restart Streamlit."
            )

    if "transcription_result" not in st.session_state:
        return

    if st.session_state.pop("transcription_just_finished", False):
        st.toast("Transcription and diarization complete.", icon="✅")

    result = st.session_state["transcription_result"]
    metadata = dict(st.session_state.get("transcription_metadata", {}))
    source_name = st.session_state.get("transcription_source", "audio")
    run_id = st.session_state.get("transcription_run_id", "run")
    segments = result.get("segments", [])

    st.divider()
    st.header("Transcript")
    st.caption(
        f"Source: **{source_name}** · detected language: **{metadata.get('language', 'unknown')}** · "
        f"model: **{metadata.get('model', 'unknown')}**"
    )

    speaker_ids = speaker_ids_in_order(segments)
    st.subheader("Speaker names")
    st.write(
        "Diarization produces anonymous speaker IDs. Rename them here before downloading. "
        "The defaults are numbered in order of first appearance."
    )

    name_map: dict[str, str] = {}
    cols = st.columns(min(3, max(1, len(speaker_ids))))
    for i, raw_id in enumerate(speaker_ids):
        with cols[i % len(cols)]:
            default_name = f"Speaker {i + 1}" if raw_id != "UNKNOWN" else "Unknown speaker"
            display_name = st.text_input(
                raw_id,
                value=default_name,
                key=f"speaker_name_{run_id}_{raw_id}",
            ).strip()
            name_map[raw_id] = display_name or default_name

    st.subheader("Review and edit")
    playback_audio = st.session_state.get("transcription_audio")
    st.warning(
        "**Edits can't be saved or reopened yet, so you can only edit a transcript here once.** "
        "Closing or refreshing this page loses your edits, and transcribing again overwrites them. "
        "Finish your review in one sitting and download your files before you leave. "
        "The app can't load them back in for further editing."
    )
    if playback_audio:
        st.write(
            "Press play to follow along, or click any word to hear it. Click into the text to "
            "correct it, and hover over a passage to change its speaker. "
            "Your changes are included in every download below."
        )
    else:
        st.warning(
            "Audio playback isn't available for this recording, but you can still edit the "
            "transcript. FFmpeg couldn't create the playback copy."
        )
    with st.container(key=PLAYER_CONTAINER_KEY):
        if playback_audio:
            st.audio(playback_audio, format="audio/mpeg")
    edits, speaker_changes = transcript_editor(
        segments, name_map, run_id, has_audio=bool(playback_audio)
    )

    rows = make_display_rows(segments, name_map, edits, speaker_changes)
    turns = merge_turns(rows)
    txt = build_txt(turns)
    csv_text = build_csv(rows)
    word_csv = build_word_csv(segments, name_map, edits, speaker_changes)
    srt = build_srt(rows)
    metadata["source_file"] = source_name
    metadata["speaker_names"] = name_map
    metadata["edited_segments"] = len(edits)
    metadata["reassigned_segments"] = len(speaker_changes)
    json_text = build_json(result, name_map, metadata, edits, speaker_changes)

    with st.expander("Segment table"):
        st.dataframe(rows, width="stretch", hide_index=True)

    stem = safe_stem(source_name)
    files = {
        f"{stem}_transcript.txt": txt.encode("utf-8"),
        f"{stem}_segments.csv": csv_text.encode("utf-8-sig"),
        f"{stem}_words.csv": word_csv.encode("utf-8-sig"),
        f"{stem}_transcript.srt": srt.encode("utf-8"),
        f"{stem}_transcript.json": json_text.encode("utf-8"),
    }
    zip_bytes = build_zip(files)

    st.subheader("Downloads")
    dcols = st.columns(5)
    dcols[0].download_button(
        "TXT",
        data=files[f"{stem}_transcript.txt"],
        file_name=f"{stem}_transcript.txt",
        mime="text/plain",
    )
    dcols[1].download_button(
        "Segments CSV",
        data=files[f"{stem}_segments.csv"],
        file_name=f"{stem}_segments.csv",
        mime="text/csv",
    )
    dcols[2].download_button(
        "Words CSV",
        data=files[f"{stem}_words.csv"],
        file_name=f"{stem}_words.csv",
        mime="text/csv",
    )
    dcols[3].download_button(
        "SRT",
        data=files[f"{stem}_transcript.srt"],
        file_name=f"{stem}_transcript.srt",
        mime="application/x-subrip",
    )
    dcols[4].download_button(
        "JSON",
        data=files[f"{stem}_transcript.json"],
        file_name=f"{stem}_transcript.json",
        mime="application/json",
    )
    st.download_button(
        "Download all outputs (.zip)",
        data=zip_bytes,
        file_name=f"{stem}_transcription_bundle.zip",
        mime="application/zip",
        type="primary",
    )


if __name__ == "__main__":
    main()
