import "./styles/tokens.css";
import "./styles/components.css";
import "./styles/visitor.css";
import { renderMessage, toolStatus } from "./render";
import { renderMarkdown } from "./markdown";
import { type ChatMessage, bindComposer, focusComposer, initTheme } from "./ui";

const FAST = 10_000;
const SLOW = 60_000;
const QUIET_AFTER = 5 * 60_000;

const nameInput = document.querySelector<HTMLInputElement>("#visitor-name")!;
const resetButton = document.querySelector<HTMLButtonElement>("#reset")!;
const draft = document.querySelector<HTMLTextAreaElement>("#draft")!;
const sendButton = document.querySelector<HTMLButtonElement>("#send")!;
const intro = document.querySelector<HTMLElement>("#intro")!;
const suggestions = document.querySelector<HTMLElement>("#suggestions")!;
const convo = document.querySelector<HTMLElement>("#convo")!;
const convoInner = document.querySelector<HTMLElement>("#convo-inner")!;
const notice = document.querySelector<HTMLElement>("#notice")!;
const brandName = document.querySelector<HTMLElement>("#brand-name")!;
const introTitle = document.querySelector<HTMLElement>("#intro-title")!;
const themeButton = document.querySelector<HTMLElement>("#theme-toggle")!;

let ownerName = "Amna Ahmad";
let conversationId = "";
let seen = new Set<number>();
let lastActivity = Date.now();
let pollTimer = 0;
let sending = false;
let pending: HTMLElement | null = null;

initTheme(themeButton);
nameInput.value = localStorage.getItem("avatar-visitor-name") || "";
bindComposer(draft, () => void send());
sendButton.addEventListener("click", () => void send());
resetButton.addEventListener("click", () => reset());
nameInput.addEventListener("input", () => {
  localStorage.setItem("avatar-visitor-name", nameInput.value);
});

void boot();
focusComposer(draft);

async function boot(): Promise<void> {
  const config = await fetch("/api/config").then((response) => response.json());
  ownerName = config.owner_name || ownerName;
  const first = ownerName.split(" ")[0] || ownerName;
  document.title = ownerName;
  brandName.textContent = ownerName;
  introTitle.innerHTML = `Hi, I'm ${escapeHtml(first)}'s <em>digital twin</em>`;
  draft.placeholder = `Message ${first}'s twin…`;
  for (const query of config.suggestions || []) {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.type = "button";
    chip.textContent = query;
    chip.addEventListener("click", () => void send(query));
    suggestions.appendChild(chip);
  }

  conversationId = crypto.randomUUID();
  clearCid();
  const existing = await loadThread(0);
  const deep = new URLSearchParams(location.search).get("q");
  if (deep && /^\d{1,2}$/.test(deep)) {
    history.replaceState({}, "", location.pathname);
    await send(`Q${deep}`);
  } else if (!existing) {
    focusComposer(draft);
  }
  schedulePoll();
}

async function loadThread(after: number): Promise<boolean> {
  const response = await fetch(`/api/conversations/${conversationId}?after=${after}`);
  if (!response.ok) return false;
  const body = await response.json();
  let added = false;
  for (const message of body.messages as ChatMessage[]) {
    if (seen.has(message.id)) continue;
    append(message);
    added = true;
  }
  if (added) scrollDown();
  intro.hidden = seen.size > 0;
  return added;
}

function append(message: ChatMessage): void {
  seen.add(message.id);
  convoInner.appendChild(renderMessage(message, ownerName, "visitor"));
}

async function send(preset?: string): Promise<void> {
  const content = (preset ?? draft.value).trim();
  if (!content || sending) return;
  sending = true;
  notice.textContent = "";
  if (!preset) {
    draft.value = "";
    draft.style.height = "auto";
  }
  const optimistic = document.createElement("div");
  optimistic.className = "msg msg--visitor";
  optimistic.innerHTML = `<span class="avatar-initials"></span><div class="msg-body"><div class="bubble"><p></p></div></div>`;
  optimistic.querySelector(".avatar-initials")!.textContent = initialsOf(nameInput.value);
  optimistic.querySelector("p")!.textContent = content;
  convoInner.appendChild(optimistic);
  intro.hidden = true;
  scrollDown();
  focusComposer(draft);

  const shell = startAvatarShell();
  try {
    const response = await fetch(`/api/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, name: nameInput.value.trim() || null }),
    });
    if (response.status === 429) {
      optimistic.remove();
      shell.root.remove();
      pending = null;
      const body = await response.json().catch(() => ({ detail: "You're sending messages too quickly." }));
      if (!preset) draft.value = content;
      notice.textContent = body.detail || "You're sending messages too quickly. Give it a moment and try again.";
      intro.hidden = seen.size > 0;
      return;
    }
    if (!response.ok || !response.body) {
      throw new Error("request failed");
    }
    let raw = "";
    await readSse(response, (event) => {
      if (event.type === "tool") {
        const existing = shell.tools.querySelector<HTMLElement>(`[data-tool="${CSS.escape(event.name)}"]:not(.is-done)`);
        if (event.state === "done" && existing) {
          existing.classList.add("is-done");
          const span = existing.querySelector("span");
          if (span) {
            span.classList.remove("dots");
            span.textContent = `${event.name} · ${event.detail || "done"}`;
          }
        } else if (event.state !== "done") {
          shell.tools.appendChild(toolStatus(event.name, "", false));
        } else {
          shell.tools.appendChild(toolStatus(event.name, event.detail || "done", true));
        }
      } else if (event.type === "delta") {
        raw += event.text || "";
        shell.bubble.innerHTML = renderMarkdown(raw);
        scrollDown();
      } else if (event.type === "done") {
        if (event.visitor?.id) {
          seen.add(event.visitor.id);
          optimistic.dataset.id = String(event.visitor.id);
        }
        if (event.message) {
          shell.root.replaceWith(renderMessage(event.message as ChatMessage, ownerName, "visitor"));
          seen.add(event.message.id);
          pending = null;
        }
      } else if (event.type === "error") {
        notice.textContent = event.detail || "Something went wrong.";
      }
    });
    lastActivity = Date.now();
  } catch {
    shell.root.remove();
    pending = null;
    notice.textContent = "The message didn't go through. Try again.";
  } finally {
    sending = false;
    focusComposer(draft);
    schedulePoll();
  }
}

function startAvatarShell(): { root: HTMLElement; tools: HTMLElement; bubble: HTMLElement } {
  const root = document.createElement("div");
  root.className = "msg msg--avatar";
  root.innerHTML = `
    <div class="avatar avatar-twin" style="background-image:url('/avatar-robot-round.png')"></div>
    <div class="msg-body">
      <div class="msg-meta"><span class="msg-time"></span></div>
      <div class="tool-slot"></div>
      <div class="bubble"><span class="typing-dots" role="status" aria-label="Amna is replying"><span></span><span></span><span></span></span></div>
    </div>`;
  convoInner.appendChild(root);
  pending = root;
  scrollDown();
  return {
    root,
    tools: root.querySelector(".tool-slot")!,
    bubble: root.querySelector(".bubble")!,
  };
}

function reset(): void {
  conversationId = crypto.randomUUID();
  seen = new Set();
  pending = null;
  for (const node of [...convoInner.querySelectorAll(".msg")]) node.remove();
  intro.hidden = false;
  notice.textContent = "";
  lastActivity = Date.now();
  focusComposer(draft);
}

function schedulePoll(): void {
  window.clearTimeout(pollTimer);
  const wait = Date.now() - lastActivity > QUIET_AFTER ? SLOW : FAST;
  pollTimer = window.setTimeout(async () => {
    if (!sending && !document.hidden) {
      const after = Math.max(0, ...seen);
      const added = await loadThread(after);
      if (added) lastActivity = Date.now();
    }
    schedulePoll();
  }, wait);
}

async function readSse(response: Response, onEvent: (event: Record<string, unknown>) => void): Promise<void> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let split = buffer.indexOf("\n\n");
    while (split !== -1) {
      const raw = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      const data = raw
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim())
        .join("\n");
      if (data) onEvent(JSON.parse(data));
      split = buffer.indexOf("\n\n");
    }
  }
}

function scrollDown(): void {
  convo.scrollTop = convo.scrollHeight;
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "V";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function clearCid(): void {
  document.cookie = "avatar_cid=; Path=/; Max-Age=0; SameSite=Lax";
}
