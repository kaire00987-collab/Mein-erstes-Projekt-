// Kleiner, sicherer Markdown-Renderer (kein Internet nötig).
// Text wird zuerst escaped, danach werden nur bekannte Formatierungen erzeugt.
(function () {
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  function inline(s) {
    const codes = [];
    s = s.replace(/`([^`\n]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
    s = esc(s);
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
    s = s.replace(/(^|\W)_([^_\s][^_]*)_(?=\W|$)/g, "$1<em>$2</em>");
    s = s.replace(/~~([^~]+)~~/g, "<del>$1</del>");
    s = s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${esc(codes[+i])}</code>`);
    return s;
  }

  function table(rows) {
    const cells = (r) => r.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());
    const head = cells(rows[0]);
    let html = "<table><thead><tr>" + head.map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead><tbody>";
    for (const r of rows.slice(2)) html += "<tr>" + cells(r).map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>";
    return html + "</tbody></table>";
  }

  function render(src) {
    // Denk-Abschnitte von "Reasoning"-Modellen (<think>…</think>) einklappen
    let thinking = "";
    src = src.replace(/<think>([\s\S]*?)(<\/think>|$)/, (_, t) => { thinking = t.trim(); return ""; });

    const lines = src.replace(/\r\n/g, "\n").split("\n");
    const out = [];
    let i = 0;
    let para = [];
    const flush = () => { if (para.length) { out.push(`<p>${para.map(inline).join("<br>")}</p>`); para = []; } };

    while (i < lines.length) {
      const line = lines[i];
      let m;
      if ((m = line.match(/^\s*```(\S*)/))) {
        flush();
        const code = [];
        i++;
        while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) code.push(lines[i++]);
        i++;
        const lang = m[1] ? ` class="lang-${esc(m[1])}"` : "";
        out.push(`<pre><button class="copy" type="button">Kopieren</button><code${lang}>${esc(code.join("\n"))}</code></pre>`);
        continue;
      }
      if ((m = line.match(/^(#{1,6})\s+(.*)$/))) {
        flush();
        const lvl = Math.min(m[1].length, 3);
        out.push(`<h${lvl}>${inline(m[2])}</h${lvl}>`);
      } else if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) {
        flush();
        out.push("<hr>");
      } else if (/^\s*>/.test(line)) {
        flush();
        const q = [];
        while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, ""));
        out.push(`<blockquote>${render(q.join("\n"))}</blockquote>`);
        continue;
      } else if (/^\s*\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\s*\|?[\s:-]+\|[\s|:-]*$/.test(lines[i + 1])) {
        flush();
        const rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(lines[i++]);
        out.push(table(rows));
        continue;
      } else if (/^\s*([-*+]|\d+[.)])\s+/.test(line)) {
        flush();
        const ordered = /^\s*\d+[.)]/.test(line);
        const items = [];
        while (i < lines.length && (/^\s*([-*+]|\d+[.)])\s+/.test(lines[i]) || (/^\s{2,}\S/.test(lines[i]) && items.length))) {
          const l = lines[i++];
          const item = l.match(/^\s*(?:[-*+]|\d+[.)])\s+(.*)$/);
          if (item) items.push(item[1]);
          else items[items.length - 1] += " " + l.trim();
        }
        const tag = ordered ? "ol" : "ul";
        out.push(`<${tag}>${items.map((t) => `<li>${inline(t)}</li>`).join("")}</${tag}>`);
        continue;
      } else if (!line.trim()) {
        flush();
      } else {
        para.push(line);
      }
      i++;
    }
    flush();
    let html = out.join("\n");
    if (thinking) html = `<details class="thinking"><summary>Gedanken</summary>${render(thinking)}</details>` + html;
    return html;
  }

  window.renderMarkdown = render;
})();
