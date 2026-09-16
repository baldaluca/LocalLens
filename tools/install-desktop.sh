#!/usr/bin/env bash
# Installa voce .desktop + icone LocalLens in ~/.local (GNOME/dock).
# Uso: tools/install-desktop.sh [dir-bundle-con-eseguibile]
set -euo pipefail
BUNDLE="${1:-dist/locallens}"
EXE="$(realpath "$BUNDLE/locallens")"
APP=~/.local/share/applications
ICONS=~/.local/share/icons/hicolor
mkdir -p "$APP"
sed "s|^Exec=.*|Exec=$EXE|" assets/locallens.desktop > "$APP/locallens.desktop"
for s in 16 32 48 64 128 256 512; do
  d="$ICONS/${s}x${s}/apps"
  mkdir -p "$d"
  cp "assets/icons/locallens-$s.png" "$d/locallens.png"
done
command -v update-desktop-database >/dev/null && update-desktop-database "$APP" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "$ICONS" || true
echo "installato: $APP/locallens.desktop -> $EXE"
