#!/usr/bin/env python3

from __future__ import annotations

import csv
import io
import json
import sys
import textwrap
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "app_config.json"
SHEET_NAME = "people"
RESULT_LIMIT = 20
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


def load_config() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return {"sheet_url": "", "proxy_key": ""}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sheet_url": "", "proxy_key": ""}


def save_config(config: dict[str, str]) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def extract_spreadsheet_id(sheet_url: str) -> str:
    marker = "/d/"
    if marker not in sheet_url:
        raise ValueError("Google Sheet URL khong hop le.")
    tail = sheet_url.split(marker, 1)[1]
    spreadsheet_id = tail.split("/", 1)[0].strip()
    if not spreadsheet_id:
        raise ValueError("Khong tim thay spreadsheet id trong URL.")
    return spreadsheet_id


def build_csv_url(sheet_url: str) -> str:
    spreadsheet_id = extract_spreadsheet_id(sheet_url)
    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(SHEET_NAME)}"
    )


def fetch_sheet_rows(sheet_url: str) -> list[list[str]]:
    request = Request(
        build_csv_url(sheet_url),
        headers={"User-Agent": "Mozilla/5.0"},
    )
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
                "Row": str(index),
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
    if not api_key.strip():
        raise ValueError("Ban chua nhap Proxy API key.")

    endpoint = f"https://app.proxyno1.com/api/change-key-ip/{quote(api_key.strip())}"
    request = Request(
        endpoint,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")

    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Phan hoi proxy khong hop le.")
    return data


def divider() -> None:
    print("=" * 110)


def show_header() -> None:
    divider()
    print("Sheet + Proxy CLI")
    print("Don gian, nhanh, khong GUI, khong port, khong can cai them thu vien.")
    divider()


def show_config(config: dict[str, str]) -> None:
    print(f"Sheet URL : {config.get('sheet_url', '') or '(chua nhap)'}")
    print(f"Proxy key : {config.get('proxy_key', '') or '(chua nhap)'}")
    print(f"Sheet name: {SHEET_NAME}")
    print(f"So dong   : {RESULT_LIMIT}")


def prompt_update_config(config: dict[str, str]) -> dict[str, str]:
    print("\nNhap cau hinh. Enter de giu nguyen gia tri cu.\n")
    sheet_url = input(f"Google Sheet URL [{config.get('sheet_url', '')}]: ").strip()
    proxy_key = input(f"Proxy API key [{config.get('proxy_key', '')}]: ").strip()

    if sheet_url:
        config["sheet_url"] = sheet_url
    if proxy_key:
        config["proxy_key"] = proxy_key

    save_config(config)
    print(f"\nDa luu vao {CONFIG_PATH.name}\n")
    return config


def truncate(value: str, width: int) -> str:
    clean = " ".join(value.split())
    if len(clean) <= width:
        return clean.ljust(width)
    return (clean[: width - 1] + "…") if width > 1 else clean[:width]


def print_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("\nKhong tim thay dong nao co cot L trong.\n")
        return

    columns = [
        ("Row", 6),
        ("B", 18),
        ("C", 18),
        ("D", 12),
        ("E", 12),
        ("I", 16),
        ("J", 16),
        ("K", 22),
    ]

    print()
    print("Ket qua:")
    print("-" * 130)
    print(" | ".join(name.ljust(width) for name, width in columns))
    print("-" * 130)
    for row in rows:
        print(" | ".join(truncate(row.get(name, ""), width) for name, width in columns))
    print("-" * 130)
    print(f"Tong so dong hien thi: {len(rows)}\n")


def fetch_and_print_rows(config: dict[str, str]) -> None:
    sheet_url = config.get("sheet_url", "").strip()
    if not sheet_url:
        print("\nBan chua nhap Google Sheet URL.\n")
        return

    print("\nDang doc sheet...\n")
    try:
        rows = fetch_sheet_rows(sheet_url)
        selected = pick_empty_l_rows(rows, RESULT_LIMIT)
    except ValueError as exc:
        print(f"Loi: {exc}\n")
        return
    except HTTPError as exc:
        print("Loi: Khong doc duoc Google Sheet.")
        print("Kiem tra lai link hoac quyen truy cap.")
        print(f"HTTP {exc.code}\n")
        return
    except URLError as exc:
        print(f"Loi ket noi: {exc.reason}\n")
        return
    except Exception as exc:
        print(f"Loi khong xac dinh: {exc}\n")
        return

    print_rows(selected)


def run_change_proxy(config: dict[str, str]) -> None:
    proxy_key = config.get("proxy_key", "").strip()
    if not proxy_key:
        print("\nBan chua nhap Proxy API key.\n")
        return

    print("\nDang doi proxy...\n")
    try:
        payload = change_proxy_ip(proxy_key)
        status = payload.get("status")
        message = str(payload.get("message", "Khong co message"))
        if status == 0:
            print(f"status=0 | {message}")
            print("Cho them 5 giay de ket noi on dinh...\n")
            time.sleep(5)
        else:
            print(f"status={status} | {message}\n")
    except HTTPError as exc:
        print(f"HTTP {exc.code} khi doi proxy.\n")
    except URLError as exc:
        print(f"Loi ket noi proxy: {exc.reason}\n")
    except Exception as exc:
        print(f"Loi khong xac dinh: {exc}\n")


def main() -> int:
    config = load_config()

    while True:
        show_header()
        show_config(config)
        print(
            textwrap.dedent(
                """

                Chon thao tac:
                1. Sua / luu cau hinh
                2. Lay 20 dong tu Google Sheet
                3. Doi proxy
                4. Xem cau hinh hien tai
                0. Thoat
                """
            ).strip()
        )

        choice = input("\nNhap lua chon: ").strip()

        if choice == "1":
            config = prompt_update_config(config)
        elif choice == "2":
            fetch_and_print_rows(config)
        elif choice == "3":
            run_change_proxy(config)
        elif choice == "4":
            print()
            show_config(config)
            print()
        elif choice == "0":
            print("\nThoat.\n")
            return 0
        else:
            print("\nLua chon khong hop le.\n")

        input("Nhan Enter de tiep tuc...")
        print()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n\nDa dung.\n")
        sys.exit(130)
