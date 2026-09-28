(function () {
  "use strict";

  const BACKEND_URL = "http://127.0.0.1:5000";
  const STORAGE_KEYS = { conversation: "rajConversation", history: "rajCommandHistory" };
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  const state = {
    online: false,
    listening: false,
    alwaysListening: true,
    recognition: null,
    conversation: load(STORAGE_KEYS.conversation, []),
    history: load(STORAGE_KEYS.history, []),
    lastCommand: "",
    lastResponse: "",
    toastTimer: null,
  };

  const elements = {
    orb: document.getElementById("assistantOrb"),
    orbLabel: document.getElementById("orbLabel"),
    micButton: document.getElementById("micButton"),
    voicePrompt: document.getElementById("voicePrompt"),
    voiceHint: document.getElementById("voiceHint"),
    commandInput: document.getElementById("commandInput"),
    sendButton: document.getElementById("sendButton"),
    alwaysToggle: document.getElementById("alwaysListeningToggle"),
    alwaysCaption: document.getElementById("alwaysListeningCaption"),
    alwaysMetric: document.getElementById("alwaysMetric"),
    microphoneMetric: document.getElementById("microphoneMetric"),
    globalStatus: document.getElementById("globalStatus"),
    globalStatusText: document.getElementById("globalStatusText"),
    backendStatus: document.getElementById("backendStatus"),
    backendStatusMeta: document.getElementById("backendStatusMeta"),
    backendMetric: document.getElementById("backendMetric"),
    lastCommand: document.getElementById("lastCommand"),
    lastResponse: document.getElementById("lastResponse"),
    conversationList: document.getElementById("conversationList"),
    historyList: document.getElementById("historyList"),
    historyCount: document.getElementById("historyCount"),
    clearHistoryButton: document.getElementById("clearHistoryButton"),
    toast: document.getElementById("toast"),
  };

  function load(key, fallback) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "null");
      return Array.isArray(value) ? value : fallback;
    } catch (_error) {
      return fallback;
    }
  }

  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_error) { /* Storage can be disabled. */ }
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character]));
  }

  function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function setOrb(stateName) {
    const value = stateName.toUpperCase();
    elements.orb.dataset.state = value;
    elements.orbLabel.textContent = value;
  }

  function addConversation(role, text) {
    state.conversation.push({ role, text, timestamp: Date.now() });
    state.conversation = state.conversation.slice(-60);
    save(STORAGE_KEYS.conversation, state.conversation);
    renderConversation();
  }

  function addHistory(command, success) {
    state.history.unshift({ command, success, timestamp: Date.now() });
    state.history = state.history.slice(0, 24);
    save(STORAGE_KEYS.history, state.history);
    renderHistory();
  }

  function renderConversation() {
    if (!state.conversation.length) {
      elements.conversationList.innerHTML = '<div class="empty-state">Your commands will appear here.</div>';
      return;
    }
    elements.conversationList.innerHTML = state.conversation.map((item) => `
      <div class="message ${item.role === "RAJ" ? "raj" : ""}">
        <span class="message-role">${escapeHtml(item.role)}</span>
        <span class="message-body">${escapeHtml(item.text)}</span>
        <time class="message-time">${formatTime(item.timestamp)}</time>
      </div>
    `).join("");
    elements.conversationList.scrollTop = elements.conversationList.scrollHeight;
  }

  function renderHistory() {
    elements.historyCount.textContent = String(state.history.length);
    if (!state.history.length) {
      elements.historyList.innerHTML = '<div class="empty-state">No recent commands.</div>';
      return;
    }
    elements.historyList.innerHTML = state.history.map((item) => `
      <div class="history-item">
        <span class="history-check">${item.success ? "✓" : "!"}</span>
        <div><p>${escapeHtml(item.command)}</p><time>${formatTime(item.timestamp)}</time></div>
      </div>
    `).join("");
  }

  function showToast(message) {
    clearTimeout(state.toastTimer);
    elements.toast.textContent = message;
    elements.toast.classList.add("visible");
    state.toastTimer = setTimeout(() => elements.toast.classList.remove("visible"), 3200);
  }

  function setOnline(isOnline) {
    state.online = isOnline;
    elements.globalStatus.classList.toggle("online", isOnline);
    elements.globalStatus.classList.toggle("offline", !isOnline);
    elements.globalStatusText.textContent = isOnline ? "ONLINE" : "OFFLINE";
    elements.backendStatus.textContent = isOnline ? "ONLINE" : "OFFLINE";
    elements.backendStatusMeta.textContent = isOnline ? "Local backend connected" : "Start start_raj.bat";
    elements.backendMetric.textContent = isOnline ? "CONNECTED" : "OFFLINE";
    if (!isOnline && !state.listening) setOrb("OFFLINE");
    if (isOnline && !state.listening) setOrb("READY");
  }

  function setListening(isListening) {
    state.listening = isListening;
    elements.micButton.classList.toggle("active", isListening);
    elements.microphoneMetric.textContent = isListening ? "LISTENING" : "READY";
    elements.voicePrompt.textContent = isListening ? "Listening…" : "Tap to Speak";
    elements.voiceHint.textContent = isListening ? "Say a command clearly" : "Use your voice or type a command below";
    if (isListening) setOrb("LISTENING");
    else if (state.online) setOrb("READY");
  }

  function normalizeCommand(raw) {
    let command = String(raw || "").trim().replace(/[.!?,;:]+$/g, "").replace(/\s+/g, " ");
    // Remove wake word even if speech recognition adds "hey/okay" before it.
    command = command.replace(/^(?:(?:hey|okay|ok)\s+)?(?:raj|raaj|rage)\b[\s,:-]*/i, "");
    return command.trim();
  }

  function containsWakeWord(raw) {
    // Speech recognition sometimes hears "Raj" as "Raaj" or "Rage".
    // Accept these close variants only in Always Listening mode.
    return /^(?:(?:hey|okay|ok)\s+)?(?:raj|raaj|rage)\b[\s,:-]*/i.test(String(raw || "").trim());
  }

  function speakResponse(text) {
    if (!("speechSynthesis" in window) || !text) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    utterance.voice = voices.find((voice) => /^en/i.test(voice.lang)) || voices[0] || null;
    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.onstart = () => setOrb("SPEAKING");
    utterance.onend = () => { if (state.online) setOrb("READY"); };
    window.speechSynthesis.speak(utterance);
  }

  async function requestBackend(path, options) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 7000);
    try {
      const response = await fetch(`${BACKEND_URL}${path}`, { ...options, signal: controller.signal, headers: { "Content-Type": "application/json", ...(options && options.headers ? options.headers : {}) } });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || `Backend returned ${response.status}`);
      return data;
    } finally {
      clearTimeout(timeout);
    }
  }

  let autoVoiceStarting = false;
  let lastAutoVoiceAttempt = 0;

  async function ensureAlwaysListening() {
    if (!state.online || !state.alwaysListening || state.listening || autoVoiceStarting) return;
    const now = Date.now();
    if (now - lastAutoVoiceAttempt < 4000) return;
    lastAutoVoiceAttempt = now;
    autoVoiceStarting = true;
    try {
      await requestBackend("/voice/start", {
        method: "POST",
        body: JSON.stringify({ always: true }),
      });
      setListening(true);
      elements.voiceHint.textContent = 'Always listening for “Raj” + your command…';
    } catch (error) {
      elements.voiceHint.textContent = error?.message || "Could not start the microphone.";
    } finally {
      autoVoiceStarting = false;
    }
  }

  async function checkBackend() {
    try {
      const data = await requestBackend("/status", { method: "GET" });
      setOnline(Boolean(data.online));
      if (data.voice) {
        if (data.voice.listening) setListening(true);
        else if (state.alwaysListening) ensureAlwaysListening();
      } else if (state.alwaysListening) {
        ensureAlwaysListening();
      }
    } catch (_error) {
      setOnline(false);
    }
  }

  async function sendCommand(rawCommand, source) {
    const command = normalizeCommand(rawCommand);
    if (!command) {
      showToast("Tell RAJ what you would like to do.");
      return;
    }
    if (!state.online) {
      const message = "RAJ backend is not connected.";
      addConversation("RAJ", message);
      showToast(message);
      speakResponse(message);
      return;
    }

    elements.commandInput.value = "";
    addConversation("YOU", command);
    state.lastCommand = command;
    elements.lastCommand.textContent = command;
    setOrb("THINKING");
    setTimeout(() => setOrb("EXECUTING"), 240);

    try {
      const data = await requestBackend("/command", { method: "POST", body: JSON.stringify({ command }) });
      const message = data.message || "Done.";
      const isConfirmation = Boolean(data.confirmation_required);
      addConversation("RAJ", message);
      state.lastResponse = message;
      elements.lastResponse.textContent = message;
      if (!isConfirmation) addHistory(command, Boolean(data.success));
      else showToast("Confirmation required");
      speakResponse(message);
      if (source === "voice" && !state.alwaysListening) setListening(false);
    } catch (_error) {
      const message = "RAJ encountered a problem.";
      addConversation("RAJ", message);
      elements.lastResponse.textContent = message;
      addHistory(command, false);
      speakResponse(message);
      setOnline(false);
    } finally {
      if (!("speechSynthesis" in window) || !window.speechSynthesis.speaking) setOrb(state.online ? "READY" : "OFFLINE");
    }
  }

  let lastVoiceId = 0;

  async function startRecognition() {
    if (!state.online) {
      showToast("RAJ backend is offline. Start start_raj.bat first.");
      return;
    }
    try {
      await requestBackend("/voice/start", {
        method: "POST",
        body: JSON.stringify({ always: state.alwaysListening }),
      });
      setListening(true);
      elements.voiceHint.textContent = state.alwaysListening
        ? 'Listening for “Raj” + your command…'
        : 'Listening… say your command now';
    } catch (error) {
      const message = error?.message || "Could not start the microphone.";
      elements.voiceHint.textContent = message;
      showToast(message);
      setListening(false);
    }
  }

  async function stopRecognition() {
    try {
      await requestBackend("/voice/stop", { method: "POST", body: JSON.stringify({}) });
    } catch (_error) { /* Backend may already be stopped. */ }
    setListening(false);
  }

  async function pollVoice() {
    if (!state.online) return;
    try {
      const data = await requestBackend("/voice/status", { method: "GET" });
      if (Boolean(data.listening) !== state.listening) setListening(Boolean(data.listening));

      if (data.error) {
        elements.voiceHint.textContent = data.error;
        // Do not spam the screen while Always Listening is idle.
        if (!state.listening) showToast(data.error);
      }

      if (data.id && data.id !== lastVoiceId && data.text) {
        lastVoiceId = data.id;
        const raw = String(data.text).trim();
        console.log("RAJ desktop microphone heard:", raw);
        elements.voiceHint.textContent = `Heard: “${raw}”`;

        if (state.alwaysListening && !containsWakeWord(raw)) {
          return;
        }

        const command = normalizeCommand(raw);
        if (!command) {
          speakResponse("Yes, I am listening.");
          return;
        }
        sendCommand(command, "voice");
      }
    } catch (_error) {
      // checkBackend() handles the visible online/offline state.
    }
  }

  function updateAlwaysListening() {
    const enabled = state.alwaysListening;
    elements.alwaysToggle.setAttribute("aria-checked", String(enabled));
    elements.alwaysMetric.textContent = enabled ? "ON" : "OFF";
    elements.alwaysCaption.textContent = enabled
      ? 'Always listening for “Raj”'
      : 'Always listening is OFF';

    if (enabled) ensureAlwaysListening();
    else stopRecognition();
  }

  elements.micButton.addEventListener("click", () => {
    if (state.listening) stopRecognition();
    else startRecognition();
  });
  elements.sendButton.addEventListener("click", () => sendCommand(elements.commandInput.value, "text"));
  elements.commandInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") sendCommand(elements.commandInput.value, "text");
  });
  elements.alwaysToggle.addEventListener("click", () => {
    state.alwaysListening = !state.alwaysListening;
    updateAlwaysListening();
  });
  elements.clearHistoryButton.addEventListener("click", () => {
    state.conversation = [];
    state.history = [];
    save(STORAGE_KEYS.conversation, []);
    save(STORAGE_KEYS.history, []);
    renderConversation();
    renderHistory();
    showToast("Conversation history cleared.");
  });
  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", () => sendCommand(button.dataset.command, "quick-action"));
  });

  renderConversation();
  renderHistory();
  // RAJ starts in Always Listening mode by default.
  elements.alwaysToggle.setAttribute("aria-checked", "true");
  elements.alwaysMetric.textContent = "ON";
  elements.alwaysCaption.textContent = 'Always listening for “Raj”';
  checkBackend();
  setInterval(checkBackend, 3000);
  setInterval(pollVoice, 400);
})();