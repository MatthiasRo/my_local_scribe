# Contributing to My Local Scribe

Thanks for your interest in improving this project. It's in active pre-release development, so large parts may still change. If you're planning a bigger change, please open an issue to discuss it first.

## Protect people's data

This project handles confidential recordings, so these rules apply to every contribution:

- **Never attach real recordings or transcripts** to an issue or pull request, or commit them. Use audio you created yourself for testing, or a recording that's clearly public.
- **Never share a Hugging Face token.** If you share one by accident, revoke it straight away in your [Hugging Face settings](https://huggingface.co/settings/tokens).
- **Check error messages and logs before posting them.** They can contain file names, people's names or pieces of a transcript.
- **Keep the privacy promises true.** Any change that adds a network connection, stores data on disk or adds a dependency with telemetry must also update [docs/privacy.md](docs/privacy.md).

The `.gitignore` file blocks common audio, video, transcript and token files, but it's only a safety net. Check `git status` before you commit.

## Reporting problems

Please [open an issue](https://github.com/MatthiasRo/my_local_scribe/issues) and include:

- what you did and what you expected to happen,
- your operating system, Python version, and whether you use a GPU or CPU,
- the error from the app's **Technical details** section, with anything private removed,
- the settings you used, and the rough length and format of the file.

**For a security or privacy problem,** please don't describe it in a public issue. Use [GitHub's private vulnerability reporting](https://github.com/MatthiasRo/my_local_scribe/security/advisories/new) instead.

## Development setup

1. Follow the [installation guide](docs/installation.md). If you plan to submit changes, fork the repository and clone your fork.
2. Read [How it works](docs/how-it-works.md), especially the design decisions.
3. Create a branch for your change:

    ```bash
    git checkout -b short-description-of-change
    ```

4. Run the app from the project folder. Streamlit offers to rerun the app whenever you save the file.

    ```bash
    python -m streamlit run local_transcriber_app.py
    ```

## Testing your change

The project doesn't have automated tests yet, so please check your change by hand with a short, non-confidential clip and the `tiny` model:

- [ ] The app starts with no errors, and a clip runs through to the end.
- [ ] Speakers can be renamed, and the new names appear in the downloads.
- [ ] During playback, the highlight follows the audio, and clicking a word moves the audio.
- [ ] A correction appears in the downloads, and typing isn't interrupted when it saves.
- [ ] A passage can be moved to another speaker, and the headings and downloads follow.
- [ ] Every download button works, and the files open correctly.
- [ ] A missing token gives a clear error rather than a crash.

If you've changed model loading, also test a first run with an empty cache, which you can do by setting the `HF_HOME` environment variable to an empty folder.

## Pull requests

- Keep each pull request focused on one change.
- Explain what changed and why, and say how you tested it.
- Update the documentation if users will notice the change.
- Add a line under `Unreleased` in [CHANGELOG.md](CHANGELOG.md).

## License

By contributing, you agree that your work is licensed under the project's [Apache License 2.0](LICENSE.md).
