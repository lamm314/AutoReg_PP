#!/bin/zsh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Kiem tra moi truong macOS"

if ! command -v swiftc >/dev/null 2>&1; then
  echo
  echo "Khong tim thay swiftc."
  echo "May nay can cai Xcode Command Line Tools."
  echo "Dang mo hop thoai cai dat..."
  xcode-select --install || true
  echo
  echo "Sau khi cai dat xong, chay lai: ./setup.command"
  exit 1
fi

echo "==> Build ung dung"
./run_app.command

echo
echo "Hoan tat."
echo "Tu lan sau ban co the chay truc tiep: ./run_app.command"
