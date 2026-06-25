const state = {
  authMode: "login",
  token: window.localStorage.getItem("dyxn_token") || "",
  sessionId: window.localStorage.getItem("dyxn_session_id") || "",
  documentPollTimer: null,
};

const els = {
  authForm: document.querySelector("#authForm"),
  authSubmit: document.querySelector("#authSubmit"),
  authStatus: document.querySelector("#authStatus"),
  username: document.querySelector("#username"),
  password: document.querySelector("#password"),
  uploadForm: document.querySelector("#uploadForm"),
  uploadStatus: document.querySelector("#uploadStatus"),
  documentFile: document.querySelector("#documentFile"),
  fileName: document.querySelector("#fileName"),
  sourceType: document.querySelector("#sourceType"),
  chatForm: document.querySelector("#chatForm"),
  chatMessage: document.querySelector("#chatMessage"),
  chatThread: document.querySelector("#chatThread"),
  latexOutput: document.querySelector("#latexOutput"),
  sessionChip: document.querySelector("#sessionChip"),
  copyOutput: document.querySelector("#copyOutput"),
};

function setStatus(element, message, tone = "") {
  element.textContent = message;
  element.classList.remove("good", "bad");
  if (tone) {
    element.classList.add(tone);
  }
}

function setBusy(form, busy) {
  form.classList.toggle("is-loading", busy);
  for (const control of form.querySelectorAll("button, input, select, textarea")) {
    control.disabled = busy;
  }
}

function tokenHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : { detail: await response.text() };

  if (!response.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item) => item.msg || String(item)).join(", ")
      : body.detail || "Request failed";
    throw new Error(detail);
  }

  return body;
}

async function apiJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...tokenHeaders(),
      ...(options.headers || {}),
    },
  });

  return parseResponse(response);
}

async function login(username, password) {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const response = await fetch("/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });

  return parseResponse(response);
}

function updateSessionChip() {
  if (state.sessionId) {
    els.sessionChip.textContent = `Session ${state.sessionId.slice(0, 8)}`;
    els.sessionChip.classList.add("ready");
  } else {
    els.sessionChip.textContent = "No session";
    els.sessionChip.classList.remove("ready");
  }
}

function updateAuthUi() {
  if (state.token) {
    setStatus(els.authStatus, "Connected. Upload a PDF or ask a question.", "good");
  } else {
    setStatus(els.authStatus, "Not connected");
  }
  updateSessionChip();
}

function appendMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "Y" : "D";

  const body = document.createElement("div");
  const speaker = document.createElement("p");
  speaker.className = "speaker";
  speaker.textContent = role === "user" ? "You" : "DYXN";

  const content = document.createElement("p");
  content.textContent = text;

  body.append(speaker, content);
  article.append(avatar, body);
  els.chatThread.append(article);
  els.chatThread.scrollTop = els.chatThread.scrollHeight;
}

async function ensureSession() {
  if (state.sessionId) {
    return state.sessionId;
  }

  const data = await apiJson("/sessions", { method: "POST" });
  state.sessionId = data.id;
  window.localStorage.setItem("dyxn_session_id", state.sessionId);
  updateSessionChip();
  return state.sessionId;
}

function formatDocumentStatus(documentStatus) {
  const status = documentStatus.status || "unknown";
  const filename = documentStatus.filename || "Document";
  const embedded = Number(documentStatus.embedded_chunks || 0);
  const total = Number(documentStatus.total_chunks || 0);

  if (status === "ready") {
    return `${filename} is ready.`;
  }

  if (status === "failed") {
    return `${filename} failed: ${documentStatus.error || "check worker logs"}`;
  }

  if (total > 0) {
    return `${filename} is ${status}: ${embedded}/${total} chunks searchable.`;
  }

  return `${filename} is ${status}.`;
}

async function pollDocumentStatus(documentId) {
  if (state.documentPollTimer) {
    window.clearTimeout(state.documentPollTimer);
    state.documentPollTimer = null;
  }

  if (!state.token || !documentId) {
    return;
  }

  try {
    const documentStatus = await apiJson(`/documents/${documentId}/status`);
    const tone = documentStatus.status === "failed" ? "bad" : "good";
    setStatus(els.uploadStatus, formatDocumentStatus(documentStatus), tone);

    if (documentStatus.processing) {
      state.documentPollTimer = window.setTimeout(() => pollDocumentStatus(documentId), 2500);
    }
  } catch (error) {
    setStatus(els.uploadStatus, error.message, "bad");
  }
}

document.querySelectorAll("[data-scroll-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.querySelector(button.dataset.scrollTarget);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

document.querySelectorAll("[data-auth-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    state.authMode = button.dataset.authMode;
    document.querySelectorAll("[data-auth-mode]").forEach((item) => {
      item.classList.toggle("active", item === button);
    });
    els.authSubmit.textContent = state.authMode === "login" ? "Login" : "Create account";
    setStatus(
      els.authStatus,
      state.authMode === "login" ? "Use an existing account." : "Create a local account."
    );
  });
});

els.documentFile.addEventListener("change", () => {
  const file = els.documentFile.files[0];
  els.fileName.textContent = file ? file.name : "Choose PDF";
  setStatus(els.uploadStatus, file ? `${file.name} selected` : "Waiting for a PDF");
});

els.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = els.username.value.trim();
  const password = els.password.value;

  if (!username || !password) {
    setStatus(els.authStatus, "Username and password are required.", "bad");
    return;
  }

  setBusy(els.authForm, true);
  setStatus(els.authStatus, state.authMode === "login" ? "Signing in..." : "Creating account...");

  try {
    if (state.authMode === "register") {
      await apiJson("/register", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
    }

    const data = await login(username, password);
    state.token = data.access_token;
    state.sessionId = "";
    window.localStorage.setItem("dyxn_token", state.token);
    window.localStorage.removeItem("dyxn_session_id");
    updateAuthUi();
  } catch (error) {
    setStatus(els.authStatus, error.message, "bad");
  } finally {
    setBusy(els.authForm, false);
  }
});

els.uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!state.token) {
    setStatus(els.uploadStatus, "Login before uploading.", "bad");
    return;
  }

  const file = els.documentFile.files[0];
  if (!file) {
    setStatus(els.uploadStatus, "Choose a PDF first.", "bad");
    return;
  }

  const body = new FormData();
  body.set("file", file);
  body.set("source_type", els.sourceType.value);

  setBusy(els.uploadForm, true);
  setStatus(els.uploadStatus, "Uploading and queuing...");

  try {
    const response = await fetch("/documents/upload", {
      method: "POST",
      headers: tokenHeaders(),
      body,
    });
    const data = await parseResponse(response);
    setStatus(
      els.uploadStatus,
      `${data.filename} queued as ${data.source_type}.`,
      "good"
    );
    pollDocumentStatus(data.document_id);
  } catch (error) {
    setStatus(els.uploadStatus, error.message, "bad");
  } finally {
    setBusy(els.uploadForm, false);
  }
});

els.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!state.token) {
    appendMessage("ai", "Log in first so I can retrieve your uploaded sources.");
    return;
  }

  const message = els.chatMessage.value.trim();
  if (!message) {
    return;
  }

  els.chatMessage.value = "";
  appendMessage("user", message);
  setBusy(els.chatForm, true);

  try {
    const sessionId = await ensureSession();
    appendMessage("ai", "Retrieving source chunks...");
    const data = await apiJson(`/sessions/${sessionId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    appendMessage("ai", "Response ready. I placed the LaTeX output below.");
    els.latexOutput.textContent = data.response || "% Empty response.";
  } catch (error) {
    appendMessage("ai", error.message);
  } finally {
    setBusy(els.chatForm, false);
  }
});

els.copyOutput.addEventListener("click", async () => {
  const text = els.latexOutput.textContent.trim();
  if (!text) {
    return;
  }

  await navigator.clipboard.writeText(text);
  els.copyOutput.textContent = "Copied";
  window.setTimeout(() => {
    els.copyOutput.textContent = "Copy";
  }, 1200);
});

updateAuthUi();
