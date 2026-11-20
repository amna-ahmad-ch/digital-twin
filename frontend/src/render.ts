import { renderMarkdown } from "./markdown";
import { type ChatMessage, formatTime, icon, initials } from "./ui";

export function renderMessage(message: ChatMessage, ownerName: string, surface: "visitor" | "admin"): HTMLElement {
  const node = document.createElement("div");
  node.className = `msg msg--${message.role}`;
  node.dataset.id = String(message.id);
  const who = message.conversation_name || "Visitor";
  const time = formatTime(message.created_at);

  if (message.role === "visitor") {
    node.innerHTML = `
      <span class="avatar-initials">${initials(who)}</span>
      <div class="msg-body">
        <div class="msg-meta"><span class="msg-time">${time}</span></div>
        <div class="bubble"><p></p></div>
      </div>`;
    const paragraph = node.querySelector("p");
    if (paragraph) paragraph.textContent = message.content;
    return node;
  }

  if (message.role === "human") {
    const tag = surface === "admin" ? "You · sent to visitor" : `${ownerName} · live`;
    node.innerHTML = `
      <div class="avatar avatar-human" style="background-image:url('/avatar-human.png')">
        <span class="spark-badge">${icon("i-spark")}</span>
      </div>
      <div class="msg-body">
        <div class="msg-meta">
          <span class="human-tag">${icon("i-live")} ${escapeText(tag)}</span>
          <span class="msg-time">${time}</span>
        </div>
        <div class="bubble"></div>
      </div>`;
  } else {
    node.innerHTML = `
      <div class="avatar avatar-twin" style="background-image:url('/avatar-robot-round.png')"></div>
      <div class="msg-body">
        <div class="msg-meta">
          <span class="msg-time">${time}</span>
        </div>
        <div class="bubble"></div>
      </div>`;
    const meta = node.querySelector(".msg-meta");
    const instant = (message.tool_calls || []).find((call) => call.name === "instant");
    if (instant && meta) {
      const tag = document.createElement("span");
      tag.className = "instant-tag";
      tag.textContent = `instant · ${instant.detail || "Qn"}`;
      meta.insertBefore(tag, meta.querySelector(".msg-time"));
    }
    const body = node.querySelector(".msg-body");
    const bubble = node.querySelector(".bubble");
    for (const call of message.tool_calls || []) {
      if (call.name === "instant" || !body || !bubble) continue;
      body.insertBefore(toolStatus(call.name, call.detail || "done", true), bubble);
    }
  }

  const bubble = node.querySelector(".bubble");
  if (bubble) bubble.innerHTML = renderMarkdown(message.content);
  return node;
}

export function toolStatus(name: string, detail: string, done: boolean): HTMLElement {
  const row = document.createElement("div");
  row.className = done ? "tool-status is-done" : "tool-status";
  row.dataset.tool = name;
  const glyph = name === "push_tool" ? "i-mail" : done ? "i-check" : "i-tool";
  const label = done ? `${name} · ${detail}` : `Calling ${name}`;
  row.innerHTML = `${icon(glyph)} <span></span>`;
  const span = row.querySelector("span");
  if (span) span.textContent = label;
  if (!done) span?.classList.add("dots");
  return row;
}

function escapeText(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
