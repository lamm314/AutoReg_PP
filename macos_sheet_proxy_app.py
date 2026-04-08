#!/usr/bin/env python3

from __future__ import annotations

import csv
import html
import io
import json
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "app_config.json"
SHEET_NAME = "people"
RESULT_LIMIT = 20
HOST = "127.0.0.1"
PORT = 8765
DISPLAY_COLUMNS = {
    "B": 1,
    "C": 2,
    "D": 3,
    "E": 4,
    "I": 8,
    "J": 9,
    "K": 10,
    "L": 11,
}

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sheet + Proxy Dashboard</title>
  <style>
    :root {
      --bg: #eef4fb;
      --panel: #ffffff;
      --panel-soft: #f5f9ff;
      --text: #11233d;
      --muted: #60738f;
      --line: #d7e1ee;
      --accent: #1f6feb;
      --accent-dark: #185cc6;
      --success-bg: #e3f8f0;
      --success: #17674f;
      --shadow: 0 18px 50px rgba(17, 35, 61, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top right, #dbe8ff 0, transparent 28%),
        linear-gradient(180deg, #f7fbff 0%, var(--bg) 100%);
      color: var(--text);
    }
    .wrap {
      max-width: 1240px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid rgba(215, 225, 238, 0.9);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }
    .hero {
      padding: 28px 30px;
      background: linear-gradient(135deg, #1f6feb 0%, #0f4fb2 100%);
      color: #fff;
    }
    .hero h1 {
      margin: 0;
      font-size: 32px;
      line-height: 1.15;
    }
    .hero p {
      margin: 10px 0 0;
      color: rgba(255,255,255,0.82);
      max-width: 720px;
      font-size: 15px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-top: 16px;
    }
    .card {
      background: var(--panel-soft);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      min-height: 112px;
    }
    .card-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .card-value {
      margin-top: 10px;
      font-size: 24px;
      font-weight: 700;
      line-height: 1.2;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 16px;
      margin-top: 16px;
    }
    .panel {
      padding: 22px;
    }
    .panel h2 {
      margin: 0;
      font-size: 20px;
    }
    .hint {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    label {
      display: block;
      margin-top: 16px;
      margin-bottom: 8px;
      font-size: 13px;
      color: var(--muted);
      font-weight: 600;
    }
    input {
      width: 100%;
      height: 48px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 0 14px;
      font-size: 15px;
      color: var(--text);
      background: #fff;
      outline: none;
    }
    input:focus {
      border-color: #8eb6ff;
      box-shadow: 0 0 0 4px rgba(31, 111, 235, 0.12);
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
    }
    button {
      border: 0;
      border-radius: 14px;
      padding: 13px 18px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.12s ease, background 0.12s ease;
    }
    button:hover { transform: translateY(-1px); }
    .primary {
      background: var(--accent);
      color: #fff;
    }
    .primary:hover { background: var(--accent-dark); }
    .secondary {
      background: #dbe8ff;
      color: var(--accent);
    }
    .status {
      margin-top: 16px;
      border-radius: 14px;
      padding: 14px 16px;
      background: #f7faff;
      border: 1px solid var(--line);
      white-space: pre-wrap;
      line-height: 1.5;
    }
    .proxy-pill {
      display: inline-block;
      margin-top: 16px;
      padding: 10px 14px;
      border-radius: 999px;
      background: var(--success-bg);
      color: var(--success);
      font-weight: 700;
      max-width: 100%;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .table-panel {
      margin-top: 16px;
    }
    .table-wrap {
      overflow: auto;
      margin-top: 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: #fff;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 900px;
    }
    th, td {
      padding: 14px 16px;
      text-align: left;
      border-bottom: 1px solid #edf2f9;
      font-size: 14px;
      vertical-align: top;
    }
    th {
      position: sticky;
      top: 0;
      background: #ebf3ff;
      z-index: 1;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    tr:nth-child(even) td {
      background: #fbfdff;
    }
    .empty {
      padding: 24px;
      color: var(--muted);
      text-align: center;
    }
    @media (max-width: 980px) {
      .cards, .grid {
        grid-template-columns: 1fr;
      }
      .wrap {
        padding: 16px;
      }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Sheet + Proxy Dashboard</h1>
      <p>Doc sheet people, lay 20 dong co cot L trong, hien thi cot B C D E I J K va doi proxy nhanh tren macOS ma khong can cai them GUI framework.</p>
    </section>

    <section class="cards">
      <div class="card">
        <div class="card-label">Sheet</div>
        <div class="card-value">people</div>
      </div>
      <div class="card">
        <div class="card-label">So Dong</div>
        <div class="card-value" id="summary-value">Chua tai du lieu</div>
      </div>
      <div class="card">
        <div class="card-label">Proxy</div>
        <div class="card-value" id="proxy-card-value">Chua doi proxy</div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Cau hinh du lieu</h2>
        <p class="hint">Nhap link Google Sheet va API key proxy. Cau hinh duoc luu tai may trong file <code>app_config.json</code>.</p>

        <label for="sheet_url">Google Sheet URL</label>
        <input id="sheet_url" placeholder="https://docs.google.com/spreadsheets/d/..." />

        <label for="proxy_key">Proxy API key</label>
        <input id="proxy_key" placeholder="TEST0123456789" />

        <div class="actions">
          <button class="secondary" id="save-config">Luu cau hinh</button>
          <button class="primary" id="fetch-rows">Lay 20 dong</button>
        </div>

        <div class="status" id="status-box">San sang.</div>
      </div>

      <div class="panel">
        <h2>Quan ly proxy</h2>
        <p class="hint">Nhay IP qua API proxyno1. Khi status = 0, nen doi them 5-10 giay de ket noi on dinh truoc khi su dung.</p>

        <div class="actions">
          <button class="primary" id="change-proxy">Doi proxy</button>
        </div>

        <div class="proxy-pill" id="proxy-status">Chua doi proxy.</div>
      </div>
    </section>

    <section class="panel table-panel">
      <h2>Ket qua 20 dong dau tien</h2>
      <p class="hint">Hien thi cac cot B, C, D, E, I, J, K cua nhung dong ma cot L chua co gia tri.</p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Row</th>
              <th>B</th>
              <th>C</th>
              <th>D</th>
              <th>E</th>
              <th>I</th>
              <th>J</th>
              <th>K</th>
            </tr>
          </thead>
          <tbody id="results-body">
            <tr><td colspan="8" class="empty">Chua co du lieu</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>

  <script>
    const state = {
      rows: [],
      status: "San sang.",
      proxyStatus: "Chua doi proxy.",
      summary: "Chua tai du lieu",
    };

    const els = {
      sheetUrl: document.getElementById("sheet_url"),
      proxyKey: document.getElementById("proxy_key"),
      statusBox: document.getElementById("status-box"),
      proxyStatus: document.getElementById("proxy-status"),
      proxyCardValue: document.getElementById("proxy-card-value"),
      summaryValue: document.getElementById("summary-value"),
      resultsBody: document.getElementById("results-body"),
      saveBtn: document.getElementById("save-config"),
      fetchBtn: document.getElementById("fetch-rows"),
      proxyBtn: document.getElementById("change-proxy"),
    };

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function renderRows() {
      if (!state.rows.length) {
        els.resultsBody.innerHTML = '<tr><td colspan="8" class="empty">Chua co du lieu</td></tr>';
        return;
      }

      els.resultsBody.innerHTML = state.rows.map((row) => `
        <tr>
          <td>${escapeHtml(row.sheet_row)}</td>
          <td>${escapeHtml(row.B)}</td>
          <td>${escapeHtml(row.C)}</td>
          <td>${escapeHtml(row.D)}</td>
          <td>${escapeHtml(row.E)}</td>
          <td>${escapeHtml(row.I)}</td>
          <td>${escapeHtml(row.J)}</td>
          <td>${escapeHtml(row.K)}</td>
        </tr>
      `).join("");
    }

    function renderState() {
      els.statusBox.textContent = state.status;
      els.proxyStatus.textContent = state.proxyStatus;
      els.proxyCardValue.textContent = state.proxyStatus;
      els.summaryValue.textContent = state.summary;
      renderRows();
    }

    async function loadConfig() {
      const res = await fetch("/api/config");
      const data = await res.json();
      els.sheetUrl.value = data.sheet_url || "";
      els.proxyKey.value = data.proxy_key || "";
    }

    async function saveConfig() {
      const payload = {
        sheet_url: els.sheetUrl.value.trim(),
        proxy_key: els.proxyKey.value.trim(),
      };
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      state.status = data.message;
      renderState();
      return data;
    }

    async function fetchRows() {
      await saveConfig();
      state.status = "Dang doc sheet...";
      renderState();

      const params = new URLSearchParams({ sheet_url: els.sheetUrl.value.trim() });
      const res = await fetch(`/api/fetch?${params.toString()}`);
      const data = await res.json();
      state.status = data.message;
      state.rows = data.rows || [];
      state.summary = data.summary || "Chua tai du lieu";
      renderState();
    }

    async function changeProxy() {
      await saveConfig();
      state.proxyStatus = "Dang doi proxy...";
      renderState();

      const params = new URLSearchParams({ proxy_key: els.proxyKey.value.trim() });
      const res = await fetch(`/api/change-proxy?${params.toString()}`);
      const data = await res.json();
      state.proxyStatus = data.message;
      renderState();
    }

    els.saveBtn.addEventListener("click", saveConfig);
    els.fetchBtn.addEventListener("click", fetchRows);
    els.proxyBtn.addEventListener("click", changeProxy);

    loadConfig().catch((error) => {
      state.status = `Khong the tai cau hinh: ${error}`;
      renderState();
    });

    renderState();
  </script>
</body>
</html>
"""


def load_config() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return {"sheet_url": "", "proxy_key": ""}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sheet_url": "", "proxy_key": ""}
    return {
        "sheet_url": str(data.get("sheet_url", "")),
        "proxy_key": str(data.get("proxy_key", "")),
    }


def save_config(data: dict[str, str]) -> None:
    config = {
        "sheet_url": data.get("sheet_url", "").strip(),
        "proxy_key": data.get("proxy_key", "").strip(),
    }
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_spreadsheet_id(sheet_url: str) -> str:
    marker = "/d/"
    if marker not in sheet_url:
        raise ValueError("Google Sheet URL khong hop le.")
    tail = sheet_url.split(marker, 1)[1]
    spreadsheet_id = tail.split("/", 1)[0].strip()
    if not spreadsheet_id:
        raise ValueError("Khong tim thay spreadsheet id trong URL.")
    return spreadsheet_id


def build_csv_url(sheet_url: str, sheet_name: str) -> str:
    spreadsheet_id = extract_spreadsheet_id(sheet_url)
    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(sheet_name)}"
    )


def fetch_sheet_rows(sheet_url: str, sheet_name: str) -> list[list[str]]:
    csv_url = build_csv_url(sheet_url, sheet_name)
    request = Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8-sig")
    return list(csv.reader(io.StringIO(payload)))


def normalize_row(row: list[str], min_length: int) -> list[str]:
    if len(row) < min_length:
        return row + [""] * (min_length - len(row))
    return row


def pick_empty_l_rows(rows: list[list[str]], limit: int) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for index, raw_row in enumerate(rows, start=1):
        row = normalize_row(raw_row, DISPLAY_COLUMNS["L"] + 1)
        if not any(cell.strip() for cell in row):
            continue
        if index == 1:
            continue
        if row[DISPLAY_COLUMNS["L"]].strip():
            continue
        selected.append(
            {
                "sheet_row": str(index),
                "B": row[DISPLAY_COLUMNS["B"]].strip(),
                "C": row[DISPLAY_COLUMNS["C"]].strip(),
                "D": row[DISPLAY_COLUMNS["D"]].strip(),
                "E": row[DISPLAY_COLUMNS["E"]].strip(),
                "I": row[DISPLAY_COLUMNS["I"]].strip(),
                "J": row[DISPLAY_COLUMNS["J"]].strip(),
                "K": row[DISPLAY_COLUMNS["K"]].strip(),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def change_proxy_ip(api_key: str) -> dict[str, object]:
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("Ban chua nhap Proxy API key.")
    endpoint = f"https://app.proxyno1.com/api/change-key-ip/{quote(api_key)}"
    request = Request(endpoint, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Phan hoi proxy khong hop le.")
    return data


def json_response(handler: BaseHTTPRequestHandler, payload: dict[str, object], status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._serve_html()
            return
        if parsed.path == "/api/config":
            json_response(self, load_config())
            return
        if parsed.path == "/api/fetch":
            self._handle_fetch(parsed.query)
            return
        if parsed.path == "/api/change-proxy":
            self._handle_change_proxy(parsed.query)
            return

        json_response(self, {"message": "Not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/config":
            json_response(self, {"message": "Not found"}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            json_response(self, {"message": "JSON khong hop le."}, status=400)
            return

        try:
            save_config(
                {
                    "sheet_url": str(payload.get("sheet_url", "")),
                    "proxy_key": str(payload.get("proxy_key", "")),
                }
            )
        except OSError as exc:
            json_response(self, {"message": f"Khong the luu cau hinh: {exc}"}, status=500)
            return

        json_response(self, {"message": f"Da luu cau hinh vao {CONFIG_PATH.name}."})

    def _serve_html(self) -> None:
        body = HTML_PAGE.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_fetch(self, query: str) -> None:
        params = parse_qs(query)
        sheet_url = params.get("sheet_url", [""])[0].strip()
        if not sheet_url:
            json_response(self, {"message": "Ban chua nhap Google Sheet URL.", "rows": [], "summary": "Khong tai du lieu"}, status=400)
            return

        try:
            rows = fetch_sheet_rows(sheet_url, SHEET_NAME)
            selected = pick_empty_l_rows(rows, RESULT_LIMIT)
        except ValueError as exc:
            json_response(self, {"message": str(exc), "rows": [], "summary": "Khong tai du lieu"}, status=400)
            return
        except HTTPError as exc:
            message = (
                "Khong doc duoc Google Sheet. Kiem tra lai link hoac quyen truy cap. "
                f"Neu sheet khong public, endpoint CSV se bi chan. HTTP {exc.code}"
            )
            json_response(self, {"message": message, "rows": [], "summary": "Khong tai du lieu"}, status=400)
            return
        except URLError as exc:
            json_response(
                self,
                {"message": f"Loi ket noi: {exc.reason}", "rows": [], "summary": "Khong tai du lieu"},
                status=502,
            )
            return
        except Exception as exc:
            json_response(
                self,
                {"message": f"Loi khong xac dinh: {exc}", "rows": [], "summary": "Khong tai du lieu"},
                status=500,
            )
            return

        json_response(
            self,
            {
                "message": f"Da lay {len(selected)} dong tu sheet '{SHEET_NAME}' co cot L trong.",
                "rows": selected,
                "summary": f"{len(selected)}/{RESULT_LIMIT} dong",
            },
        )

    def _handle_change_proxy(self, query: str) -> None:
        params = parse_qs(query)
        proxy_key = params.get("proxy_key", [""])[0].strip()
        try:
            payload = change_proxy_ip(proxy_key)
            status = payload.get("status")
            message = str(payload.get("message", "Khong co message"))
            if status == 0:
                time.sleep(5)
                result = f"status=0 | {message} | Da doi proxy, nen cho on dinh them 5-10 giay."
            else:
                result = f"status={status} | {message}"
        except ValueError as exc:
            json_response(self, {"message": str(exc)}, status=400)
            return
        except HTTPError as exc:
            json_response(self, {"message": f"HTTP {exc.code} khi doi proxy."}, status=502)
            return
        except URLError as exc:
            json_response(self, {"message": f"Loi ket noi proxy: {exc.reason}"}, status=502)
            return
        except json.JSONDecodeError:
            json_response(self, {"message": "Phan hoi proxy khong phai JSON hop le."}, status=502)
            return
        except Exception as exc:
            json_response(self, {"message": f"Loi khong xac dinh: {exc}"}, status=500)
            return

        json_response(self, {"message": result})


def start_server() -> None:
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"App dang chay tai http://{HOST}:{PORT}")
    threading.Timer(0.6, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    server.serve_forever()


if __name__ == "__main__":
    start_server()
