import "./styles/tokens.css";
import "./styles/components.css";
import "./styles/admin.css";
import { renderMessage } from "./render";
import { type ChatMessage, bindComposer, focusComposer, formatTime, initTheme, initials } from "./ui";

interface InboxRow {
  conversation_id: string;
  conversation_name: string;
  preview: string;
  updated_at: string;
  unread: number;
  needs_attention: boolean;
  count: number;
}

const gate = document.querySelector<HTMLElement>("#gate")!;
const loginForm = document.querySelector<HTMLFormElement>("#login-form")!;
const password = document.querySelector<HTMLInputElement>("#password")!;
const loginError = document.querySelector<HTMLElement>("#login-error")!;
const appbar = document.querySelector<HTMLElement>("#appbar")!;
const workspace = document.querySelector<HTMLElement>("#workspace")!;
const inbox = document.querySelector<HTMLElement>("#inbox")!;
const count = document.querySelector<HTMLElement>("#count")!;
const attentionCount = document.querySelector<HTMLElement>("#attention-count")!;
const unreadCount = document.querySelector<HTMLElement>("#unread-count")!;
const search = document.querySelector<HTMLInputElement>("#search")!;
const thread = document.querySelector<HTMLElement>("#thread")!;
const threadInner = document.querySelector<HTMLElement>("#thread-inner")!;
const threadHead = document.querySelector<HTMLElement>("#thread-head")!;
const threadName = document.querySelector<HTMLElement>("#thread-name")!;
const threadSub = document.querySelector<HTMLElement>("#thread-sub")!;
const threadInitials = document.querySelector<HTMLElement>("#thread-initials")!;
const attnFlag = document.querySelector<HTMLElement>("#attn-flag")!;
const resolveButton = document.querySelector<HTMLButtonElement>("#resolve")!;
const composerDock = document.querySelector<HTMLElement>("#composer-dock")!;
const draft = document.querySelector<HTMLTextAreaElement>("#draft")!;
const sendButton = document.querySelector<HTMLButtonElement>("#send")!;
const empty = document.querySelector<HTMLElement>("#empty-thread")!;
const ownerLabel = document.querySelector<HTMLElement>("#owner-label")!;
const storageNote = document.querySelector<HTMLElement>("#storage-note")!;

let ownerName = "Amna Ahmad";
let rows: InboxRow[] = [];
let filter: "all" | "attention" | "unread" = "all";
let selected = "";
let seen = new Set<number>();
let sending = false;

initTheme(document.querySelector<HTMLElement>("#theme-toggle")!);
bindComposer(draft, () => void send());
sendButton.addEventListener("click", () => void send());
loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  void login();
});
document.querySelector("#logout")!.addEventListener("click", () => void logout());
document.querySelector("#back")!.addEventListener("click", () => showInbox());
resolveButton.addEventListener("click", () => void markResolved());
search.addEventListener("input", () => paintInbox());
for (const chip of document.querySelectorAll<HTMLButtonElement>("[data-filter]")) {
  chip.addEventListener("click", () => {
    filter = chip.dataset.filter as typeof filter;
    for (const other of document.querySelectorAll("[data-filter]")) other.classList.remove("is-on");
    chip.classList.add("is-on");
    paintInbox();
  });
}
document.addEventListener("keydown", (event) => {
  if (gate.hidden === false) return;
  const target = event.target as HTMLElement;
  if (target.matches("input, textarea")) return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    move(event.key === "ArrowDown" ? 1 : -1);
  }
});

void boot();

async function boot(): Promise<void> {
  const session = await fetch("/admin/api/session");
  if (session.ok) {
    const body = await session.json();
    ownerName = body.owner_name || ownerName;
    showApp();
    return;
  }
  password.focus();
}

async function login(): Promise<void> {
  loginError.textContent = "";
  const response = await fetch("/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: password.value }),
  });
  if (!response.ok) {
    loginError.textContent = "That password doesn't match.";
    return;
  }
  const body = await response.json();
  ownerName = body.owner_name || ownerName;
  showApp();
}

function showApp(): void {
  gate.hidden = true;
  appbar.hidden = false;
  workspace.hidden = false;
  ownerLabel.textContent = ownerName.split(" ")[0] || ownerName;
  document.title = `${ownerName} · Admin`;
  void refreshInbox();
  window.setInterval(() => void refreshInbox(), 10_000);
  void fetch("/api/config")
    .then((response) => response.json())
    .then((config) => {
      if (config.storage === "memory") {
        storageNote.hidden = false;
        storageNote.textContent = "Local memory store. Conversations reset when the server restarts. Add Supabase to keep them.";
      }
    });
}

async function logout(): Promise<void> {
  await fetch("/admin/logout", { method: "POST" });
  location.reload();
}

async function refreshInbox(): Promise<void> {
  const response = await fetch("/admin/api/conversations");
  if (response.status === 401) {
    location.reload();
    return;
  }
  const body = await response.json();
  rows = body.conversations || [];
  count.textContent = String(rows.length);
  attentionCount.textContent = String(rows.filter((row) => row.needs_attention).length);
  unreadCount.textContent = String(rows.filter((row) => row.unread > 0).length);
  paintInbox();
  if (selected) await refreshThread();
}

function visibleRows(): InboxRow[] {
  const query = search.value.trim().toLowerCase();
  return rows.filter((row) => {
    if (filter === "attention" && !row.needs_attention) return false;
    if (filter === "unread" && row.unread < 1) return false;
    if (!query) return true;
    return `${row.conversation_name} ${row.preview}`.toLowerCase().includes(query);
  });
}

function paintInbox(): void {
  const visible = visibleRows();
  inbox.innerHTML = "";
  if (!visible.length) {
    const emptyRow = document.createElement("p");
    emptyRow.className = "storage-note";
    emptyRow.textContent = rows.length ? "Nothing matches." : "No conversations yet.";
    inbox.appendChild(emptyRow);
    return;
  }
  for (const row of visible) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "convo-item";
    if (row.conversation_id === selected) button.classList.add("is-active");
    if (row.unread > 0) button.classList.add("is-unread");
    if (row.needs_attention) button.classList.add("is-attention");
    const badge = row.needs_attention
      ? `<span class="badge badge--attention">Needs you</span>`
      : row.unread > 0
        ? `<span class="badge--dot"></span>`
        : "";
    button.innerHTML = `
      <span class="avatar-initials"></span>
      <div class="convo-main">
        <div class="convo-top"><span class="convo-name"></span></div>
        <div class="convo-preview"></div>
      </div>
      <div class="convo-side">
        <span class="msg-time"></span>
        ${badge}
      </div>`;
    button.querySelector(".avatar-initials")!.textContent = initials(row.conversation_name);
    button.querySelector(".convo-name")!.textContent = row.conversation_name || "Visitor";
    button.querySelector(".convo-preview")!.textContent = row.preview || "New conversation";
    button.querySelector(".msg-time")!.textContent = formatTime(row.updated_at);
    button.addEventListener("click", () => void openThread(row.conversation_id));
    inbox.appendChild(button);
  }
}

async function openThread(id: string): Promise<void> {
  selected = id;
  seen = new Set();
  workspace.classList.add("is-thread");
  paintInbox();
  const response = await fetch(`/admin/api/conversations/${id}`);
  if (!response.ok) return;
  const body = await response.json();
  threadHead.hidden = false;
  composerDock.hidden = false;
  empty.hidden = true;
  threadName.textContent = body.name || "Visitor";
  threadInitials.textContent = initials(body.name);
  const started = formatTime(body.started_at);
  threadSub.textContent = `${id.slice(0, 8)} · ${started} · ${body.count} messages`;
  const showAttention = Boolean(body.attention);
  attnFlag.hidden = !showAttention;
  resolveButton.hidden = !showAttention;
  threadInner.querySelectorAll(".msg").forEach((node) => node.remove());
  for (const message of body.messages as ChatMessage[]) {
    seen.add(message.id);
    threadInner.appendChild(renderMessage(message, ownerName, "admin"));
  }
  thread.scrollTop = thread.scrollHeight;
  focusComposer(draft);
  void refreshInbox();
}

async function refreshThread(): Promise<void> {
  if (!selected || sending) return;
  const response = await fetch(`/admin/api/conversations/${selected}`);
  if (!response.ok) return;
  const body = await response.json();
  let added = false;
  for (const message of body.messages as ChatMessage[]) {
    if (seen.has(message.id)) continue;
    seen.add(message.id);
    threadInner.appendChild(renderMessage(message, ownerName, "admin"));
    added = true;
  }
  if (added) thread.scrollTop = thread.scrollHeight;
  threadSub.textContent = `${selected.slice(0, 8)} · ${formatTime(body.started_at)} · ${body.count} messages`;
}

async function send(): Promise<void> {
  const content = draft.value.trim();
  if (!content || !selected || sending) return;
  sending = true;
  draft.value = "";
  draft.style.height = "auto";
  try {
    const response = await fetch(`/admin/api/conversations/${selected}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (!response.ok) return;
    const body = await response.json();
    const message = body.message as ChatMessage;
    if (!seen.has(message.id)) {
      seen.add(message.id);
      threadInner.appendChild(renderMessage(message, ownerName, "admin"));
      thread.scrollTop = thread.scrollHeight;
    }
  } finally {
    sending = false;
    focusComposer(draft);
  }
}

async function markResolved(): Promise<void> {
  if (!selected) return;
  await fetch(`/admin/api/conversations/${selected}/resolve`, { method: "POST" });
  attnFlag.hidden = true;
  resolveButton.hidden = true;
  void refreshInbox();
}

function showInbox(): void {
  workspace.classList.remove("is-thread");
}

function move(delta: number): void {
  const visible = visibleRows();
  if (!visible.length) return;
  const index = visible.findIndex((row) => row.conversation_id === selected);
  const next = visible[Math.min(visible.length - 1, Math.max(0, index + delta))];
  if (next) void openThread(next.conversation_id);
}
