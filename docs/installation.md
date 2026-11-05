# Installation guide

This guide takes you from nothing installed to a working app. You only do it once, and most of the time goes on waiting for downloads.

**Contents**

1. [Check your computer](#1-check-your-computer)
2. [Install FFmpeg](#2-install-ffmpeg)
3. [Download the app](#3-download-the-app)
4. [Create a Python environment](#4-create-a-python-environment)
5. [Optional: enable an NVIDIA GPU](#5-optional-enable-an-nvidia-gpu)
6. [Get access to the speaker model](#6-get-access-to-the-speaker-model)
7. [Start the app](#7-start-the-app)
8. [Using the app again later](#using-the-app-again-later)
9. [Updating and uninstalling](#updating)

## 1. Check your computer

| Requirement | Details |
| --- | --- |
| **Operating system** | Windows, macOS or Linux |
| **Python** | 3.10, 3.11, 3.12 or 3.13. We recommend 3.11. **Python 3.14 doesn't work**, because WhisperX doesn't support it yet. The Conda steps below install the right version for you. |
| **Disk space** | About 3 GB for the Python packages (more with GPU support), plus the models you use (see below) |
| **Memory** | As a rough guide, 8 GB of RAM for the smaller models and 16 GB for the larger ones |
| **GPU** | Optional. Only NVIDIA GPUs are accelerated. |

The models download automatically the first time you use them, and are then stored on your computer. You only download the Whisper model you choose:

| Download | Size | When |
| --- | --- | --- |
| Whisper `tiny` | 78 MB | The first time you choose it |
| Whisper `base` | 148 MB | The first time you choose it |
| Whisper `small` | 486 MB | The first time you choose it |
| Whisper `medium` | 1.5 GB | The first time you choose it |
| Whisper `large-v3` (default) | 3.1 GB | The first time you choose it |
| English alignment model | 378 MB | Your first English recording |
| Other language alignment models | Varies | Your first recording in that language |
| Speaker identification model | About 30 MB | Your first recording |

## 2. Install FFmpeg

FFmpeg lets the app read MP3, M4A, MP4 and most other formats.

**Windows** (in PowerShell):

```powershell
winget install Gyan.FFmpeg
```

**macOS** (with [Homebrew](https://brew.sh/)):

```bash
brew install ffmpeg
```

**Ubuntu or Debian Linux:**

```bash
sudo apt update && sudo apt install ffmpeg
```

Then **open a new terminal window** and check that it worked:

```bash
ffmpeg -version
```

You should see a version number. If you get "command not found" or "not recognized", see [troubleshooting](troubleshooting.md#m4a-mp3-or-video-files-wont-load).

## 3. Download the app

**With Git** (makes updating easier):

```bash
git clone https://github.com/MatthiasRo/my_local_scribe.git
```

```bash
cd my_local_scribe
```

**Without Git:** open the [project page](https://github.com/MatthiasRo/my_local_scribe), click **Code → Download ZIP**, unzip it, and open a terminal inside the unzipped folder.

## 4. Create a Python environment

An environment keeps this app's packages separate from everything else on your computer. Choose one of the two options.

### Option A: Conda (recommended)

If you don't have Conda yet, install [Miniconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). On Windows, run the commands below in **Anaconda Prompt**.

```bash
conda create -n my_local_scribe python=3.11 -y
```

```bash
conda activate my_local_scribe
```

If you want NVIDIA GPU support, do [step 5](#5-optional-enable-an-nvidia-gpu) **now**, before you continue.

```bash
python -m pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```

### Option B: Python's built-in venv

Use this if you already have Python 3.10 to 3.13 installed. Check with `python --version`.

**Windows (PowerShell):**

```powershell
python -m venv .venv
```

```powershell
.venv\Scripts\Activate.ps1
```

**macOS or Linux:**

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

If you want NVIDIA GPU support, do [step 5](#5-optional-enable-an-nvidia-gpu) **now**, before you continue. Then, on any system:

```bash
python -m pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```

## 5. Optional: enable an NVIDIA GPU

Skip this if you don't have an NVIDIA GPU. The app runs without one, just more slowly.

> [!IMPORTANT]
> On Windows, `pip install -r requirements.txt` installs a **CPU-only** version of PyTorch unless you install the GPU version first. If you skip this step, the app works but never uses your GPU.

> [!NOTE]
> These GPU steps haven't been tested on real hardware by the project yet. If you try them, please report how it went.

Make sure your NVIDIA driver is up to date and that this command shows your GPU:

```bash
nvidia-smi
```

Then, with your environment active and **before** installing `requirements.txt`, run:

```bash
pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
```

Now go back and finish step 4. To check that it worked afterwards:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

You want to see a version ending in `+cu128`, followed by `True`.

**Already installed the CPU version?** Replace it with:

```bash
pip install --force-reinstall --no-deps torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
```

## 6. Get access to the speaker model

The speaker identification model is free, but its authors ask you to accept their conditions first. You only do this once.

1. Create or sign in to a [Hugging Face account](https://huggingface.co/join).
2. Open the [Community-1 model page](https://huggingface.co/pyannote/speaker-diarization-community-1).
3. Accept the conditions. The form asks for your company or university and your use case, and access is granted automatically.
4. Open your [token settings](https://huggingface.co/settings/tokens) and create a new token of type **Read**.
5. Copy the token. It starts with `hf_`.

> [!CAUTION]
> Treat your token like a password. Don't share it or put it in a file inside this project.

You have two ways to give the app your token.

**Paste it into the app.** Use the **Hugging Face token** field in the sidebar. You'll need to do this each time you start the app.

**Set it as an environment variable,** so the app finds it by itself. Run the command for your terminal before you start the app:

| Terminal | Command |
| --- | --- |
| PowerShell | `$env:HF_TOKEN="hf_your_token_here"` |
| Anaconda Prompt or Command Prompt | `set HF_TOKEN=hf_your_token_here` |
| macOS or Linux | `export HF_TOKEN="hf_your_token_here"` |

These commands last until you close the terminal.

## 7. Start the app

From inside the project folder, with your environment active:

```bash
python -m streamlit run local_transcriber_app.py
```

Your browser opens at `http://localhost:8501`. If it doesn't, open that address yourself.

Streamlit may ask for your email the first time you run it. You can press Enter to skip this.

**Test your setup** with a short clip before using a long recording:

1. Set **Whisper model** to `tiny`.
2. Paste your token into the sidebar.
3. Upload a clip of a minute or two, and click **Transcribe + diarize**.

If you get a transcript, your installation works. Continue with the [usage guide](usage.md). If not, see [troubleshooting](troubleshooting.md).

To stop the app, press `Ctrl+C` in the terminal.

## Using the app again later

You don't need to reinstall anything. Open a terminal, go to the project folder, and run:

```bash
conda activate my_local_scribe
```

```bash
python -m streamlit run local_transcriber_app.py
```

If you used a venv, activate it as shown in [step 4](#option-b-pythons-built-in-venv) instead.

## Updating

If you installed with Git, run these from the project folder with your environment active:

```bash
git pull
```

```bash
pip install -r requirements.txt
```

If you downloaded a ZIP, download the new version and repeat the `pip install` step. Your models stay in place, so you won't download them again.

## Uninstalling

1. Delete the project folder.
2. Remove the environment if you used Conda:

    ```bash
    conda env remove -n my_local_scribe
    ```

3. To free the space used by models, delete the folders for the models you no longer need:

| Data | Windows | macOS and Linux |
| --- | --- | --- |
| Models | `C:\Users\<you>\.cache\huggingface\hub` | `~/.cache/huggingface/hub` |
| Sentence data | `%APPDATA%\nltk_data` | `~/nltk_data` |

The Hugging Face folder may also contain models used by other programs, so check the folder names before you delete anything. This app's folders start with `models--Systran--faster-whisper`, `models--facebook--wav2vec2` and `models--pyannote`.
