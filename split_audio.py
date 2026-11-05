from pathlib import Path
import subprocess
import sys
import shutil


SEGMENT_LENGTH_SECONDS = 120


def split_audio(input_file):
    input_path = Path(input_file).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    if not input_path.is_file():
        raise ValueError(f"Not a file: {input_path}")

    # Make sure FFmpeg is available
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "FFmpeg was not found. Make sure FFmpeg is installed "
            "and available on your PATH."
        )

    output_dir = input_path.parent
    stem = input_path.stem
    extension = input_path.suffix

    # Example:
    # interview.m4a
    # -> interview_part_001.m4a
    # -> interview_part_002.m4a
    # etc.
    output_pattern = output_dir / f"{stem}_part_%03d{extension}"

    command = [
        ffmpeg,
        "-hide_banner",
        "-i", str(input_path),

        # Select the first audio stream only
        "-map", "0:a:0",

        # Do not re-encode the audio
        "-c", "copy",

        # Split into segments
        "-f", "segment",
        "-segment_time", str(SEGMENT_LENGTH_SECONDS),
        "-reset_timestamps", "1",

        # Start numbering at 1
        "-segment_start_number", "1",

        str(output_pattern)
    ]

    print(f"Input: {input_path}")
    print(f"Splitting into {SEGMENT_LENGTH_SECONDS // 60}-minute segments...")
    print(f"Output folder: {output_dir}")
    print()

    subprocess.run(command, check=True)

    print()
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python split_audio.py "path/to/audio_file.m4a"')
        sys.exit(1)

    split_audio(sys.argv[1])