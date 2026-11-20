export function renderMarkdown(source: string): string {
  let text = source.replace(/\r\n/g, "\n");
  const fences: string[] = [];
  text = text.replace(/```([\s\S]*?)```/g, (_match, code: string) => {
    fences.push(`<pre><code>${escapeHtml(String(code).trim())}</code></pre>`);
    return `\u0000F${fences.length - 1}\u0000`;
  });
  text = escapeHtml(text);
  text = text.replace(/\u0000F(\d+)\u0000/g, (_match, index: string) => fences[Number(index)] ?? "");
  text = text.replace(/`([^`]+)`/g, (_match, code: string) => `<code>${code}</code>`);
  text = text.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_match, label: string, url: string) => {
    if (!/^(https?:|mailto:)/i.test(url)) return label;
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
  });
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>");

  return text
    .split(/\n{2,}/)
    .map((block) => {
      if (block.startsWith("<pre>")) return block;
      const lines = block.split("\n");
      if (lines.every((line) => /^\s*[-*] /.test(line))) {
        const items = lines.map((line) => `<li>${line.replace(/^\s*[-*] /, "")}</li>`).join("");
        return `<ul>${items}</ul>`;
      }
      return `<p>${lines.join("<br>")}</p>`;
    })
    .join("");
}

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
