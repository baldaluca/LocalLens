"""Token semantici + QSS per tema. Design system: Flat, primary #2563EB (vedi skill)."""

TEMI = {
    "chiaro": {
        "background": "#F8FAFC",
        "surface": "#FFFFFF",
        "foreground": "#0F172A",
        "muted": "#475569",
        "primary": "#2563EB",
        "on_primary": "#FFFFFF",
        "accent": "#0891B2",
        "border": "#E4ECFC",
        "warning_bg": "#FFF3CD",
        "warning_fg": "#664D03",
        "success": "#15803D",
        "input_bg": "#FFFFFF",
    },
    "scuro": {
        "background": "#0F172A",
        "surface": "#1E293B",
        "foreground": "#F1F5F9",
        "muted": "#94A3B8",
        "primary": "#2563EB",
        "on_primary": "#FFFFFF",
        "accent": "#22D3EE",
        "border": "#334155",
        "warning_bg": "#453008",
        "warning_fg": "#FDE68A",
        "success": "#4ADE80",
        "input_bg": "#1E293B",
    },
}

NOMI_TEMI = ("chiaro", "scuro")


def qss(nome: str) -> str:
    try:
        t = TEMI[nome]
    except KeyError:
        raise ValueError(f"tema ignoto: {nome} (chiaro|scuro)") from None
    return f"""
QMainWindow, QWidget#centrale {{ background: {t['background']}; }}
QLabel {{ color: {t['foreground']}; }}
QLabel#banner {{ background: {t['warning_bg']}; color: {t['warning_fg']};
  padding: 8px 12px; border-radius: 8px; font-weight: 600; }}
QListWidget {{ background: {t['surface']}; color: {t['foreground']};
  border: 1px solid {t['border']}; border-radius: 8px; padding: 4px; }}
QListWidget::item {{ padding: 6px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {t['primary']}; color: {t['on_primary']}; }}
QPlainTextEdit {{ background: {t['surface']}; color: {t['foreground']};
  border: 1px solid {t['border']}; border-radius: 8px;
  selection-background-color: {t['primary']}; }}
QPushButton {{ background: {t['primary']}; color: {t['on_primary']};
  border: none; border-radius: 8px; padding: 8px 16px; font-weight: 600; }}
QPushButton:hover {{ background: {t['accent']}; }}
QPushButton:pressed {{ padding-top: 9px; padding-bottom: 7px; }}
QPushButton:disabled {{ background: {t['border']}; color: {t['muted']}; }}
QPushButton[secondario="true"] {{ background: {t['surface']}; color: {t['primary']};
  border: 1px solid {t['border']}; }}
QPushButton[secondario="true"]:hover {{ border-color: {t['primary']};
  background: {t['surface']}; }}
QProgressBar {{ background: {t['surface']}; border: 1px solid {t['border']};
  border-radius: 6px; text-align: center; color: {t['muted']}; }}
QProgressBar::chunk {{ background: {t['primary']}; border-radius: 5px; }}
QStatusBar {{ background: {t['surface']}; color: {t['muted']}; }}
QLineEdit, QComboBox {{ background: {t['input_bg']}; color: {t['foreground']};
  border: 1px solid {t['border']}; border-radius: 8px; padding: 6px 10px; }}
QLabel#avviso {{ color: #DC2626; }}
"""
