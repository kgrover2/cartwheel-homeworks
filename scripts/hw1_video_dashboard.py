"""Local presentation dashboard for the Homework 1 video.

Run from the repository root:

    uv run python scripts/hw1_video_dashboard.py
"""

from __future__ import annotations

import argparse
import html
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]


def _load_records() -> list[dict[str, Any]]:
    path = ROOT / "hw1-session.jsonl"
    records = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if line.strip():
            record = json.loads(line)
            record["_line"] = line_number
            records.append(record)
    return records


def _find(
    records: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
    *,
    last: bool = False,
) -> dict[str, Any] | None:
    matches = [record for record in records if predicate(record)]
    if not matches:
        return None
    return matches[-1] if last else matches[0]


def _tool_names(record: dict[str, Any]) -> list[str]:
    return [call["name"] for call in record.get("tool_calls", [])]


def _excerpt(path: Path, needle: str, before: int = 2, after: int = 3) -> dict[str, Any]:
    lines = path.read_text().splitlines()
    index = next(i for i, line in enumerate(lines) if needle in line)
    start = max(0, index - before)
    end = min(len(lines), index + after + 1)
    return {
        "path": str(path.relative_to(ROOT)),
        "start": start + 1,
        "end": end,
        "code": "\n".join(
            f"{line_number:>4}  {lines[line_number - 1]}"
            for line_number in range(start + 1, end + 1)
        ),
    }


def _dashboard_data() -> dict[str, Any]:
    records = _load_records()

    account_request = lambda record: "change the email address" in record["request"].lower()
    store_merchant = lambda record: (
        record["role"] == "merchant"
        and record["request"].lower() == "what is the return window of my store?"
    )
    store_support = lambda record: (
        record["role"] == "support"
        and "return window of store with storeid 2" in record["request"].lower()
    )

    selected = {
        "authorized": _find(
            records,
            lambda record: record["role"] == "shopper"
            and "4127" in record["request"]
            and record["met_requirement"],
        ),
        "denial": _find(
            records,
            lambda record: record["role"] == "merchant"
            and "4127" in record["request"]
            and "get_order" in _tool_names(record),
        ),
        "refund": _find(
            records,
            lambda record: "4455" in record["request"]
            and "issue_refund" in _tool_names(record),
            last=True,
        ),
        "account_before": _find(
            records,
            lambda record: account_request(record)
            and "escalate_to_human" not in _tool_names(record),
        ),
        "account_after": _find(
            records,
            lambda record: account_request(record)
            and "escalate_to_human" in _tool_names(record),
            last=True,
        ),
        "store_merchant_before": _find(
            records,
            lambda record: store_merchant(record)
            and "get_store_policy" not in _tool_names(record),
        ),
        "store_merchant_after": _find(
            records,
            lambda record: store_merchant(record)
            and "get_store_policy" in _tool_names(record),
            last=True,
        ),
        "store_support_before": _find(
            records,
            lambda record: store_support(record)
            and "get_store_policy" not in _tool_names(record),
        ),
        "store_support_after": _find(
            records,
            lambda record: store_support(record)
            and "get_store_policy" in _tool_names(record),
            last=True,
        ),
    }

    return {
        "record_count": len(records),
        "selected": selected,
        "excerpts": {
            "esc2": _excerpt(ROOT / "SPEC.md", "**ESC-2.**", before=1, after=2),
            "prompt": _excerpt(
                ROOT / "agent" / "agent.py",
                "For every account-change request",
                before=3,
                after=3,
            ),
            "store_tool": _excerpt(
                ROOT / "agent" / "tools.py",
                "def get_store_policy",
                before=1,
                after=39,
            ),
        },
    }


STYLE = """
:root {
  color-scheme: dark;
  --bg: #0b1020;
  --panel: #131a2e;
  --panel-2: #18213a;
  --text: #eef2ff;
  --muted: #a8b1cc;
  --line: #2c385d;
  --blue: #7dd3fc;
  --green: #6ee7b7;
  --red: #fca5a5;
  --amber: #fcd34d;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background:
    radial-gradient(circle at 15% -10%, #183264 0, transparent 34rem),
    var(--bg);
  color: var(--text);
  font: 15px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
}
nav {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 12px 24px;
  background: rgba(11, 16, 32, .9);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(14px);
}
nav strong { margin-right: auto; }
nav a, button {
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--panel);
  color: var(--text);
  padding: 7px 10px;
  text-decoration: none;
  cursor: pointer;
}
nav a:hover, button:hover { border-color: var(--blue); }
main { width: min(1180px, calc(100% - 36px)); margin: 36px auto 80px; }
header { margin-bottom: 32px; }
h1 { margin: 0 0 8px; font-size: clamp(30px, 5vw, 56px); letter-spacing: -.04em; }
h2 { margin: 48px 0 14px; font-size: 26px; }
h3 { margin: 0 0 12px; font-size: 18px; }
p { color: var(--muted); }
.stats, .grid { display: grid; gap: 14px; }
.stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.stat, .card {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: linear-gradient(145deg, var(--panel), #10172a);
  box-shadow: 0 18px 50px rgba(0, 0, 0, .18);
}
.stat { padding: 18px; }
.stat b { display: block; font-size: 30px; }
.stat span { color: var(--muted); }
.card { padding: 18px; min-width: 0; }
.card.wide { grid-column: 1 / -1; }
.meta { display: flex; gap: 7px; flex-wrap: wrap; margin-bottom: 12px; }
.pill {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 8px;
  color: var(--muted);
  font-size: 12px;
}
.pass { color: var(--green); border-color: #236b56; }
.fail { color: var(--red); border-color: #7a343b; }
.request {
  border-left: 3px solid var(--blue);
  padding: 8px 12px;
  background: var(--panel-2);
  border-radius: 0 8px 8px 0;
  color: white;
}
details { margin-top: 10px; }
summary { cursor: pointer; color: var(--blue); }
pre {
  overflow: auto;
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: #090e1a;
  color: #dbeafe;
  white-space: pre-wrap;
  word-break: break-word;
  font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace;
}
.response { color: var(--text); white-space: pre-wrap; }
.arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--amber);
  font-size: 28px;
}
.pair { display: grid; grid-template-columns: 1fr 42px 1fr; gap: 10px; align-items: stretch; }
.checklist { list-style: none; padding: 0; }
.checklist li {
  margin: 8px 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--panel);
}
.checklist li::before { content: "□"; color: var(--green); margin-right: 10px; }
.presenter .optional { display: none; }
@media (max-width: 780px) {
  .grid, .stats, .pair { grid-template-columns: 1fr; }
  .arrow { transform: rotate(90deg); }
  nav a { display: none; }
}
"""


SCRIPT = """
const DATA = __DATA__;

const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

function recordCard(record, title) {
  if (!record) return `<article class="card"><h3>${esc(title)}</h3><p>Record not found.</p></article>`;
  const status = record.met_requirement ? "pass" : "fail";
  const statusText = record.met_requirement ? "requirement met" : "observed failure";
  return `
    <article class="card">
      <h3>${esc(title)}</h3>
      <div class="meta">
        <span class="pill">line ${record._line}</span>
        <span class="pill">${esc(record.role)}</span>
        <span class="pill">${esc(record.requirement ?? "no requirement")}</span>
        <span class="pill ${status}">${statusText}</span>
      </div>
      <div class="request">${esc(record.request)}</div>
      <details open>
        <summary>Final response</summary>
        <p class="response">${esc(record.response)}</p>
      </details>
      <details>
        <summary>Tool calls (${record.tool_calls.length})</summary>
        <pre>${esc(JSON.stringify(record.tool_calls, null, 2))}</pre>
      </details>
      <details class="optional">
        <summary>Expected and assessment</summary>
        <p>${esc(record.expected)}</p>
        <p>Problem source: <strong>${esc(record.problem_source ?? "none")}</strong></p>
      </details>
    </article>`;
}

function pair(before, after, beforeTitle, afterTitle) {
  return `<div class="pair">
    ${recordCard(before, beforeTitle)}
    <div class="arrow">→</div>
    ${recordCard(after, afterTitle)}
  </div>`;
}

function excerptCard(excerpt, title) {
  return `<article class="card wide">
    <h3>${esc(title)}</h3>
    <div class="meta"><span class="pill">${esc(excerpt.path)}:${excerpt.start}-${excerpt.end}</span></div>
    <pre>${esc(excerpt.code)}</pre>
  </article>`;
}

function commandCard(command, label) {
  return `<article class="card">
    <h3>${esc(label)}</h3>
    <pre>${esc(command)}</pre>
    <button onclick='navigator.clipboard.writeText(${JSON.stringify(command)})'>Copy command</button>
  </article>`;
}

document.querySelector("#stats").innerHTML = `
  <div class="stat"><b>${DATA.record_count}</b><span>recorded conversations</span></div>`;

document.querySelector("#required").innerHTML = [
  recordCard(DATA.selected.authorized, "Authorized shopper request"),
  recordCard(DATA.selected.denial, "Merchant permission denial"),
  recordCard(DATA.selected.refund, "Above-threshold refund")
].join("");

document.querySelector("#part-c-pair").innerHTML = pair(
  DATA.selected.account_before,
  DATA.selected.account_after,
  "Before prompt change",
  "After prompt change"
);
document.querySelector("#part-c-code").innerHTML =
  excerptCard(DATA.excerpts.esc2, "Specification requirement") +
  excerptCard(DATA.excerpts.prompt, "Exact prompt revision");

document.querySelector("#store-pairs").innerHTML =
  `<h3>Merchant</h3>` +
  pair(DATA.selected.store_merchant_before, DATA.selected.store_merchant_after, "Before tool", "After tool") +
  `<h3 style="margin-top:22px">Support</h3>` +
  pair(DATA.selected.store_support_before, DATA.selected.store_support_after, "Before tool", "After tool");
document.querySelector("#store-code").innerHTML =
  excerptCard(DATA.excerpts.store_tool, "get_store_policy implementation");

document.querySelector("#commands").innerHTML =
  commandCard("uv run pytest --runxfail tests/test_hw_holes.py -k hw1", "Focused HW1 tests") +
  commandCard("uv run pytest tests/test_store_policy_tool.py", "Additional tool tests") +
  commandCard("wc -l hw1-session.jsonl", "Conversation count");

document.querySelector("#presenter").addEventListener("click", () => {
  document.body.classList.toggle("presenter");
});
"""


def _render_page() -> str:
    data = json.dumps(_dashboard_data()).replace("</", "<\\/")
    script = SCRIPT.replace("__DATA__", data)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cartwheel HW1 Video Dashboard</title>
  <style>{STYLE}</style>
</head>
<body>
  <nav>
    <strong>Cartwheel HW1</strong>
    <a href="#required-demo">Required demo</a>
    <a href="#part-c">Part C</a>
    <a href="#store-policy">Store policy</a>
    <a href="#finish">Finish</a>
    <button id="presenter">Presenter mode</button>
  </nav>
  <main>
    <header>
      <h1>Homework 1 evidence</h1>
      <p>A video-ready view generated from the current repository files.</p>
      <div id="stats" class="stats"></div>
    </header>

    <section id="required-demo">
      <h2>1. Required live examples</h2>
      <div id="required" class="grid"></div>
    </section>

    <section id="part-c">
      <h2>2. Part C — missing account-change instruction</h2>
      <p>ESC-2 required escalation. Before the revision the model merely refused;
      afterward it called <code>escalate_to_human</code>.</p>
      <div id="part-c-pair"></div>
      <div id="part-c-code" class="grid optional"></div>
    </section>

    <section id="store-policy">
      <h2>3. Additional tool — store policy lookup</h2>
      <p>The original tools could not map a store ID to its policy. The new public
      read tool resolves the store slug, loads its policy, and falls back to the
      platform return policy when no store-specific document exists.</p>
      <div id="store-pairs"></div>
      <div id="store-code" class="grid optional"></div>
    </section>

    <section id="finish">
      <h2>4. Tests and close</h2>
      <div id="commands" class="grid"></div>
      <h3 style="margin-top:28px">Video checklist</h3>
      <ul class="checklist">
        <li>Authorized request shown</li>
        <li>Permission denial shown</li>
        <li>Order 4455 queued for approval</li>
        <li>Part C failure and exact prompt edit explained</li>
        <li>Additional store-policy tool explained</li>
        <li>At least one test run</li>
        <li>JSONL record count shown</li>
      </ul>
    </section>
  </main>
  <script>{script}</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        try:
            body = _render_page().encode()
        except Exception as exc:  # pragma: no cover - visible runtime diagnostic
            body = (
                "<h1>Dashboard error</h1><pre>"
                + html.escape(str(exc))
                + "</pre>"
            ).encode()
            self.send_response(500)
        else:
            self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"HW1 dashboard: {url}")
    print("Press Ctrl-C to stop.")
    if not args.no_open:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
