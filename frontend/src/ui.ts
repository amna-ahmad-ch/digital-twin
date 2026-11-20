export interface ToolCall {
  name: string;
  detail?: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: string;
  conversation_name: string | null;
  role: "visitor" | "avatar" | "human";
  content: string;
  tool_calls: ToolCall[] | null;
  needs_attention: boolean;
  read: boolean;
  created_at: string;
}

export function initials(name: string | null | undefined): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "V";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function icon(id: string, className = "icon"): string {
  return `<svg class="${className}"><use href="/icons.svg#${id}"/></svg>`;
}

export function initTheme(button: HTMLElement): void {
  const root = document.documentElement;
  const saved = localStorage.getItem("avatar-theme");
  root.setAttribute("data-theme", saved === "light" ? "light" : "dark");
  const sync = () => {
    const dark = root.getAttribute("data-theme") !== "light";
    const moon = button.querySelector<HTMLElement>(".theme-moon");
    const sun = button.querySelector<HTMLElement>(".theme-sun");
    if (moon) moon.style.display = dark ? "inline-block" : "none";
    if (sun) sun.style.display = dark ? "none" : "inline-block";
  };
  sync();
  button.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("avatar-theme", next);
    sync();
  });
}

export function bindComposer(textarea: HTMLTextAreaElement, onSend: () => void): void {
  const grow = () => {
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  };
  textarea.addEventListener("input", grow);
  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  });
}

export function focusComposer(textarea: HTMLTextAreaElement): void {
  textarea.focus({ preventScroll: true });
}
