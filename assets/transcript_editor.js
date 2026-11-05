// Transcript editor: links an audio player and editable transcript text.
//
// Listening highlights the current passage and word. Clicking text moves the audio
// to that point. Text edits and speaker changes are sent back to Python, where they
// feed the exports.
//
// Security: transcript text and speaker names are always inserted as text
// (textContent), never as HTML.

const SPEAKER_COLORS = ["#4e79a7", "#e15759", "#59a14f", "#b07aa1", "#f28e2b", "#76b7b2", "#9c755f", "#edc948"];
const SKIP_SECONDS = 5;
const SPEEDS = [0.75, 1, 1.25, 1.5, 2];
const SAVE_DELAY_MS = 500;
const MEDIA_EVENTS = ["timeupdate", "seeked", "play", "pause", "ended"];

function formatTime(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const pad = (value) => String(value).padStart(2, "0");
  return `${pad(Math.floor(total / 3600))}:${pad(Math.floor(total / 60) % 60)}:${pad(total % 60)}`;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// Returns the last item whose start is at or before `time`, or -1.
function findLastStarted(items, time) {
  let low = 0;
  let high = items.length - 1;
  let found = -1;
  while (low <= high) {
    const middle = (low + high) >> 1;
    if (items[middle].start <= time) {
      found = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return found;
}

class TranscriptEditor {
  constructor(root, data) {
    this.root = root;
    this.runId = data.runId;
    this.hasAudio = data.hasAudio;
    this.playerSelector = data.playerSelector;
    this.speakers = data.speakers;
    this.edits = {};
    this.speakerChanges = {};
    this.setState = () => {};
    this.saveTimers = new Map();
    this.activeSegment = null;
    this.activeWord = null;
    this.frame = null;
    this.pressedInFocusedText = false;

    this.onMediaEvent = this.onMediaEvent.bind(this);
    this.onBeforeUnload = this.onBeforeUnload.bind(this);
    this.tick = this.tick.bind(this);

    this.build(data.segments);
    // Media events don't bubble, but they can be captured. Listening on the document
    // keeps this working if Streamlit replaces the player element or mounts it later.
    MEDIA_EVENTS.forEach((name) => document.addEventListener(name, this.onMediaEvent, true));
    window.addEventListener("beforeunload", this.onBeforeUnload);
  }

  destroy() {
    MEDIA_EVENTS.forEach((name) => document.removeEventListener(name, this.onMediaEvent, true));
    window.removeEventListener("beforeunload", this.onBeforeUnload);
    cancelAnimationFrame(this.frame);
    this.saveTimers.forEach((timer) => clearTimeout(timer));
  }

  get audio() {
    return document.querySelector(this.playerSelector);
  }

  build(segments) {
    this.root.textContent = "";
    this.root.classList.toggle("scribe-no-audio", !this.hasAudio);
    this.root.append(this.buildToolbar());

    this.list = element("div", "scribe-list");
    this.root.append(this.list);

    this.segments = segments.map((segment) => {
      const item = { ...segment, label: element("div", "scribe-speaker") };
      this.list.append(item.label);
      this.buildSegment(item);
      return item;
    });
    this.refreshSpeakers();

    // Stops Streamlit's page shortcuts, such as "c" and "r", firing while typing.
    ["keydown", "keyup", "keypress"].forEach((name) => {
      this.root.addEventListener(name, (event) => event.stopPropagation());
    });
    this.root.addEventListener("keydown", (event) => this.onKeyDown(event));
  }

  buildToolbar() {
    const toolbar = element("div", "scribe-toolbar");
    this.status = element("span", "scribe-status");

    if (this.hasAudio) {
      this.playButton = element("button", "", "▶ Play");
      this.playButton.type = "button";
      this.playButton.title = "Play or pause (Esc)";
      this.playButton.onclick = () => this.togglePlay();

      const back = element("button", "", `−${SKIP_SECONDS}s`);
      back.type = "button";
      back.title = `Back ${SKIP_SECONDS} seconds (Alt+Left)`;
      back.onclick = () => this.skip(-SKIP_SECONDS);

      const forward = element("button", "", `+${SKIP_SECONDS}s`);
      forward.type = "button";
      forward.title = `Forward ${SKIP_SECONDS} seconds (Alt+Right)`;
      forward.onclick = () => this.skip(SKIP_SECONDS);

      const speed = element("select");
      speed.title = "Playback speed";
      speed.setAttribute("aria-label", "Playback speed");
      SPEEDS.forEach((value) => {
        const option = element("option", "", `${value}×`);
        option.value = value;
        option.selected = value === 1;
        speed.append(option);
      });
      speed.onchange = () => {
        if (this.audio) this.audio.playbackRate = Number(speed.value);
      };

      const followLabel = element("label");
      this.followBox = element("input");
      this.followBox.type = "checkbox";
      this.followBox.checked = true;
      followLabel.append(this.followBox, "Follow audio");

      toolbar.append(this.playButton, back, forward, speed, followLabel);
    }

    toolbar.append(this.status);
    this.updateStatus();
    return toolbar;
  }

  buildSegment(item) {
    item.row = element("div", "scribe-segment");

    const time = element("button", "scribe-time", formatTime(item.start));
    time.type = "button";
    if (this.hasAudio) time.title = "Play from here";
    time.onclick = () => this.seek(item.start, true);

    item.textNode = element("div", "scribe-text");
    item.textNode.contentEditable = "true";
    item.textNode.spellcheck = true;
    item.textNode.setAttribute("role", "textbox");
    item.textNode.setAttribute("aria-label", `Transcript passage at ${formatTime(item.start)}`);

    item.speakerMenu = element("select", "scribe-who");
    item.speakerMenu.title = "Change who said this passage";
    item.speakerMenu.setAttribute("aria-label", `Speaker of the passage at ${formatTime(item.start)}`);
    item.speakerMenu.hidden = this.speakers.length < 2;
    this.speakers.forEach(({ id }) => {
      const option = element("option");
      option.value = id;
      item.speakerMenu.append(option);
    });
    item.speakerMenu.onchange = () => this.changeSpeaker(item, item.speakerMenu.value);

    const revert = element("button", "scribe-revert", "↺");
    revert.type = "button";
    revert.title = "Restore the original text and speaker";
    revert.setAttribute("aria-label", "Restore the original text and speaker");
    revert.onclick = () => this.revert(item);

    item.row.append(time, item.textNode, item.speakerMenu, revert);
    this.list.append(item.row);
    this.renderText(item);

    const text = item.textNode;
    text.addEventListener("pointerdown", () => {
      this.pressedInFocusedText = document.activeElement === text;
    });
    text.addEventListener("click", (event) => this.onTextClick(event, item));
    text.addEventListener("input", () => this.scheduleSave(item));
    text.addEventListener("blur", () => this.finishEditing(item));
    text.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        text.blur();
      }
    });
    text.addEventListener("paste", (event) => {
      event.preventDefault();
      const pasted = event.clipboardData.getData("text/plain").replace(/\s+/g, " ");
      document.execCommand("insertText", false, pasted);
    });
    text.addEventListener("drop", (event) => event.preventDefault());
  }

  // Shows word-by-word timing for untouched passages, and plain text for edited ones,
  // because timings no longer match once the words have changed.
  renderText(item) {
    const node = item.textNode;
    node.textContent = "";
    item.words = [];
    item.dirty = false;

    if (item.id in this.edits) {
      node.textContent = this.edits[item.id];
      return;
    }
    item.parts.forEach(([text, start, end]) => {
      if (start === null) {
        node.append(text);
        return;
      }
      const span = element("span", "scribe-word", text);
      item.words.push({ node: span, start, end });
      node.append(span);
    });
  }

  currentText(item) {
    return item.textNode.textContent.replace(/\s+/g, " ").trim();
  }

  scheduleSave(item) {
    item.dirty = true;
    clearTimeout(this.saveTimers.get(item.id));
    this.saveTimers.set(item.id, setTimeout(() => this.applyEdit(item), SAVE_DELAY_MS));
  }

  finishEditing(item) {
    clearTimeout(this.saveTimers.get(item.id));
    if (!item.dirty) return;
    this.applyEdit(item);
    this.renderText(item);
    this.markActive(this.audio?.currentTime);
  }

  applyEdit(item) {
    const text = this.currentText(item);
    const wasEdited = item.id in this.edits;
    const previous = this.edits[item.id];

    if (text === item.text) {
      delete this.edits[item.id];
    } else {
      this.edits[item.id] = text;
    }

    const isEdited = item.id in this.edits;
    if (wasEdited === isEdited && previous === this.edits[item.id]) return;
    this.markChanged(item);
    this.updateStatus();
    this.setState("edits", { ...this.edits });
  }

  changeSpeaker(item, speakerId) {
    if (speakerId === item.speakerId) {
      delete this.speakerChanges[item.id];
    } else {
      this.speakerChanges[item.id] = speakerId;
    }
    this.markChanged(item);
    this.refreshSpeakers();
    this.updateStatus();
    this.setState("speaker_changes", { ...this.speakerChanges });
  }

  revert(item) {
    clearTimeout(this.saveTimers.get(item.id));
    const hadEdit = item.id in this.edits;
    const hadSpeakerChange = item.id in this.speakerChanges;
    delete this.edits[item.id];
    delete this.speakerChanges[item.id];

    this.markChanged(item);
    this.renderText(item);
    this.refreshSpeakers();
    this.updateStatus();
    if (hadEdit) this.setState("edits", { ...this.edits });
    if (hadSpeakerChange) this.setState("speaker_changes", { ...this.speakerChanges });
    this.markActive(this.audio?.currentTime);
  }

  markChanged(item) {
    item.row.classList.toggle("scribe-edited", item.id in this.edits);
    item.row.classList.toggle("scribe-speaker-changed", item.id in this.speakerChanges);
  }

  // Applies the current speakers and names to every passage. A heading appears only
  // where the speaker changes, so one reassigned passage can split or merge groups.
  refreshSpeakers() {
    let previous = null;
    this.segments.forEach((item) => {
      const speakerId = this.speakerChanges[item.id] ?? item.speakerId;
      const index = Math.max(0, this.speakers.findIndex(({ id }) => id === speakerId));
      const color = SPEAKER_COLORS[index % SPEAKER_COLORS.length];

      item.row.style.setProperty("--scribe-speaker-color", color);
      item.label.style.setProperty("--scribe-speaker-color", color);
      item.label.textContent = this.speakers[index].name;
      item.label.hidden = speakerId === previous;
      previous = speakerId;

      [...item.speakerMenu.options].forEach((option, position) => {
        option.textContent = this.speakers[position].name;
      });
      item.speakerMenu.value = speakerId;
    });
  }

  changedPassageCount() {
    return new Set([...Object.keys(this.edits), ...Object.keys(this.speakerChanges)]).size;
  }

  updateStatus() {
    const count = this.changedPassageCount();
    if (count > 0) {
      this.status.textContent = `${count} ${count === 1 ? "passage" : "passages"} edited`;
    } else {
      this.status.textContent = this.hasAudio ? "Click any word to hear it" : "Click any passage to edit it";
    }
  }

  // Called on every Streamlit rerun. Passages are left alone here, because the browser
  // holds the latest changes and the user may be typing. Only speaker names can change.
  update(data, setState) {
    this.setState = setState;
    const renamed = data.speakers.some(({ name }, index) => this.speakers[index]?.name !== name);
    if (renamed) {
      this.speakers = data.speakers;
      this.refreshSpeakers();
    }
  }

  // Playback

  togglePlay() {
    const audio = this.audio;
    if (!audio) return;
    if (audio.paused) audio.play();
    else audio.pause();
  }

  skip(seconds) {
    const audio = this.audio;
    if (audio) this.seek(audio.currentTime + seconds, false);
  }

  seek(time, play) {
    const audio = this.audio;
    if (!audio) return;
    audio.currentTime = Math.max(0, time);
    if (play) audio.play();
    this.markActive(audio.currentTime);
  }

  onTextClick(event, item) {
    if (!this.hasAudio) return;
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) return;

    const word = item.words.find(({ node }) => node === event.target);
    if (word) this.seek(word.start, false);
    else if (!this.pressedInFocusedText) this.seek(item.start, false);
  }

  onKeyDown(event) {
    if (!this.hasAudio) return;
    if (event.key === "Escape") {
      event.preventDefault();
      this.togglePlay();
    } else if (event.altKey && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
      event.preventDefault();
      this.skip(event.key === "ArrowLeft" ? -SKIP_SECONDS : SKIP_SECONDS);
    }
  }

  onMediaEvent(event) {
    if (!this.root.isConnected) {
      this.destroy();
      return;
    }
    if (event.target !== this.audio) return;

    if (event.type === "play") {
      this.playButton.textContent = "❚❚ Pause";
      cancelAnimationFrame(this.frame);
      this.frame = requestAnimationFrame(this.tick);
    } else if (event.type === "pause" || event.type === "ended") {
      this.playButton.textContent = "▶ Play";
      cancelAnimationFrame(this.frame);
    }
    this.markActive(event.target.currentTime);
  }

  // The player's own time updates are too infrequent for word-by-word highlighting.
  tick() {
    const audio = this.audio;
    if (!audio || audio.paused) return;
    this.markActive(audio.currentTime);
    this.frame = requestAnimationFrame(this.tick);
  }

  markActive(time) {
    if (time === undefined) return;
    const index = findLastStarted(this.segments, time);
    const segment = index < 0 ? null : this.segments[index];

    if (segment !== this.activeSegment) {
      this.activeSegment?.row.classList.remove("scribe-active");
      segment?.row.classList.add("scribe-active");
      this.activeSegment = segment;
      if (segment) this.follow(segment);
    }

    let word = null;
    if (segment && time <= segment.end) {
      const wordIndex = findLastStarted(segment.words, time);
      word = wordIndex < 0 ? null : segment.words[wordIndex];
    }
    if (word !== this.activeWord) {
      this.activeWord?.node.classList.remove("scribe-active");
      word?.node.classList.add("scribe-active");
      this.activeWord = word;
    }
  }

  // Scrolls only the transcript list, and leaves the view alone while someone is typing.
  follow(segment) {
    if (!this.followBox?.checked) return;
    if (document.activeElement?.classList.contains("scribe-text")) return;

    const row = segment.row.getBoundingClientRect();
    const list = this.list.getBoundingClientRect();
    if (row.top < list.top + 24 || row.bottom > list.bottom - 24) {
      const top = this.list.scrollTop + row.top - list.top - list.height / 3;
      this.list.scrollTo({ top, behavior: "smooth" });
    }
  }

  // Results live only in this session, so warn before unsaved corrections are lost.
  onBeforeUnload(event) {
    if (this.root.isConnected && this.changedPassageCount() > 0) {
      event.preventDefault();
      event.returnValue = "";
    }
  }
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  const root = parentElement.querySelector(".scribe-editor");
  if (!root || !data) return;

  // Streamlit calls this function on every rerun, so the editor is created only once
  // per transcript and is updated after that. Rebuilding it would interrupt typing.
  if (root.scribeEditor?.runId !== data.runId) {
    root.scribeEditor?.destroy();
    root.scribeEditor = new TranscriptEditor(root, data);
  }
  root.scribeEditor.update(data, setStateValue);
}
