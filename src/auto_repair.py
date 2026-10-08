"""
auto_repair.py - Background Human-Simulated Code Auto-Repair Engine
Watches pos_system.py, detects errors/diffs, focuses the IDE, jumps to the
exact line, and types out the fix with natural human typing cadence.
Zero third-party pip dependencies (Pure Python + Windows ctypes/Win32).
"""

import ast
import ctypes
from ctypes import wintypes
import difflib
import os
import random
import sys
import time

# -------------------------------------------------------------
# Path Configurations
# -------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) in ("src", "core") else SCRIPT_DIR
TARGET_FILE = os.path.join(PROJECT_ROOT, "pos_system.py")
GOLDEN_FILE = os.path.join(SCRIPT_DIR, "pos_system_golden.py")

# Ensure project modules are importable
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# -------------------------------------------------------------
# Windows Win32 API Definitions via ctypes
# -------------------------------------------------------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_EXTENDEDKEY = 0x0001

# Virtual Keycodes
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_DELETE = 0x2E
VK_F9 = 0x78
VK_MULTIPLY = 0x6A  # Numeric keypad '*' (Asterisk)

# SendInput C Structs
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


def _send_input(inputs):
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def key_down(vk=0, scan=0, flags=0):
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None
    _send_input([inp])


def key_up(vk=0, scan=0, flags=0):
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags | KEYEVENTF_KEYUP
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None
    _send_input([inp])


def press_key(vk, delay=0.03):
    key_down(vk=vk)
    time.sleep(delay)
    key_up(vk=vk)


def send_combo(*vks, hold_delay=0.05):
    """Presses multiple keys down in order, then releases them in reverse order."""
    for vk in vks:
        key_down(vk=vk)
        time.sleep(0.015)
    time.sleep(hold_delay)
    for vk in reversed(vks):
        key_up(vk=vk)
        time.sleep(0.015)


def send_char(char):
    """Sends a single character via Unicode input, handling newlines and tabs."""
    if char == "\n":
        press_key(VK_RETURN)
    elif char == "\t":
        press_key(VK_TAB)
    else:
        code = ord(char)
        key_down(vk=0, scan=code, flags=KEYEVENTF_UNICODE)
        time.sleep(0.01)
        key_up(vk=0, scan=code, flags=KEYEVENTF_UNICODE)


# -------------------------------------------------------------
# IDE Window Focusing
# -------------------------------------------------------------
def focus_ide_window():
    """
    Finds and focuses Visual Studio Code or any window editing pos_system.py.
    Uses Win32 EnumWindows and fallback to WScript.Shell.
    """
    found_hwnds = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_windows_callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()
                if "pos_system" in title or "visual studio code" in title or " - code" in title:
                    found_hwnds.append((hwnd, buff.value))
        return True

    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)

    if found_hwnds:
        target_hwnd = found_hwnds[0][0]
        # Force window to foreground using AttachThreadInput technique
        user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
        cur_thread = kernel32.GetCurrentThreadId()
        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
        user32.AttachThreadInput(cur_thread, fg_thread, True)
        user32.SetForegroundWindow(target_hwnd)
        user32.AttachThreadInput(cur_thread, fg_thread, False)
        time.sleep(0.3)
        return True

    # Fallback via PowerShell / WScript.Shell AppActivate
    try:
        cmd = 'powershell -Command "$ws = New-Object -ComObject WScript.Shell; $ws.AppActivate(\'Visual Studio Code\') -or $ws.AppActivate(\'pos_system\')"'
        os.system(cmd)
        time.sleep(0.3)
        return True
    except Exception:
        return False


# -------------------------------------------------------------
# Diagnostic & Diff Engine
# -------------------------------------------------------------
def load_golden_source():
    """Loads the golden reference of pos_system.py."""
    if os.path.exists(GOLDEN_FILE):
        with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
            return f.read()
    # Fallback to git HEAD
    try:
        import subprocess
        out = subprocess.check_output(["git", "show", "HEAD:pos_system.py"], cwd=PROJECT_ROOT, text=True)
        return out
    except Exception:
        return None


def diagnose_pos_system():
    """
    Inspects pos_system.py for syntax errors and diffs against the golden copy.
    Returns:
        dict: {
            'has_error': bool,
            'syntax_error': str or None,
            'error_line': int,
            'diff_blocks': list of (tag, i1, i2, j1, j2),
            'current_lines': list of str,
            'golden_lines': list of str
        }
    """
    if not os.path.exists(TARGET_FILE):
        return {"has_error': True, 'error_msg': 'File pos_system.py not found!"}

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        current_text = f.read()

    golden_text = load_golden_source()
    if golden_text is None:
        golden_text = current_text

    current_lines = current_text.splitlines(keepends=True)
    golden_lines = golden_text.splitlines(keepends=True)

    # 1. Check Python syntax
    syntax_err = None
    syntax_line = 1
    try:
        ast.parse(current_text, filename="pos_system.py")
    except SyntaxError as e:
        syntax_err = f"{e.msg} at line {e.lineno}"
        syntax_line = e.lineno or 1

    # 2. Check diff against golden baseline
    matcher = difflib.SequenceMatcher(None, current_lines, golden_lines)
    opcodes = [op for op in matcher.get_opcodes() if op[0] != "equal"]

    has_error = (syntax_err is not None) or (len(opcodes) > 0)
    primary_line = syntax_line if syntax_err else (opcodes[0][1] + 1 if opcodes else 1)

    return {
        "has_error": has_error,
        "syntax_error": syntax_err,
        "error_line": primary_line,
        "diff_blocks": opcodes,
        "current_lines": current_lines,
        "golden_lines": golden_lines,
        "current_text": current_text,
        "golden_text": golden_text,
    }


# -------------------------------------------------------------
# Human-like Typing Simulator
# -------------------------------------------------------------
class HumanTyper:
    def __init__(self, wpm=65, typo_chance=0.015):
        self.wpm = wpm
        self.typo_chance = typo_chance
        # Base delay between keystrokes in seconds (~55-75ms for 60-80 WPM)
        self.base_delay = 60.0 / (self.wpm * 5.0)

    def type_string(self, text):
        """Types a string character-by-character with organic human pacing."""
        lines = text.split("\n")
        total_lines = len(lines)

        for line_idx, line in enumerate(lines):
            # Type each character in the line
            col = 0
            while col < len(line):
                char = line[col]

                # Occasional simulated human typo
                if self.typo_chance > 0 and char.isalpha() and random.random() < self.typo_chance:
                    wrong_char = chr(ord(char) + (1 if random.random() > 0.5 else -1))
                    send_char(wrong_char)
                    time.sleep(random.uniform(0.12, 0.22))
                    # Realize mistake, press backspace
                    press_key(VK_BACK)
                    time.sleep(random.uniform(0.08, 0.16))

                send_char(char)

                # Micro-jitter between keys
                jitter = random.gauss(self.base_delay, self.base_delay * 0.25)
                jitter = max(0.025, min(0.12, jitter))

                # Human rhythm: slight pause after punctuation or spaces
                if char in " ,;:().[]{}=":
                    jitter += random.uniform(0.06, 0.18)

                time.sleep(jitter)
                col += 1

            # End of line newline (if not the last line)
            if line_idx < total_lines - 1:
                press_key(VK_RETURN)
                # Pause after newline to read/think before typing next line
                time.sleep(random.uniform(0.25, 0.55))

    def navigate_to_line(self, line_num):
        """Navigates to pos_system.py and jumps to line_num in VS Code."""
        # Open Quick Open (Ctrl+P)
        send_combo(VK_CONTROL, ord("P"))
        time.sleep(0.3)

        # Type 'pos_system.py' and hit Enter
        for c in "pos_system.py":
            send_char(c)
            time.sleep(0.03)
        time.sleep(0.15)
        press_key(VK_RETURN)
        time.sleep(0.4)

        # Go to line (Ctrl+G)
        send_combo(VK_CONTROL, ord("G"))
        time.sleep(0.25)

        # Type line number
        for c in str(line_num):
            send_char(c)
            time.sleep(0.04)
        time.sleep(0.15)
        press_key(VK_RETURN)
        time.sleep(0.3)

    def delete_broken_lines(self, count):
        """Removes `count` lines using VS Code line delete (Ctrl+Shift+K)."""
        if count <= 0:
            return
        # Go to start of line
        press_key(VK_HOME)
        time.sleep(0.05)
        press_key(VK_HOME)
        time.sleep(0.05)

        for _ in range(count):
            # In VS Code, Ctrl+Shift+K deletes current line cleanly
            send_combo(VK_CONTROL, VK_SHIFT, ord("K"))
            time.sleep(0.12)

    def save_file(self):
        """Saves current file with Ctrl+S."""
        send_combo(VK_CONTROL, ord("S"))
        time.sleep(0.3)


# -------------------------------------------------------------
# Main Repair Workflow
# -------------------------------------------------------------
def perform_human_repair():
    """
    Executes the full automated repair sequence:
    1. Diagnoses error & diff in pos_system.py
    2. Brings VS Code to foreground
    3. Jumps to exact line
    4. Deletes broken code & types replacement with human cadence
    5. Saves file
    """
    print("\n" + "=" * 65)
    print("  [AUTO-REPAIR] Initiating diagnostic scan on pos_system.py...")
    print("=" * 65)

    diag = diagnose_pos_system()

    if not diag["has_error"]:
        print("[OK] pos_system.py is 100% clean and free of errors. No fix needed!")
        return True

    print(f"[!] Error detected in pos_system.py:")
    if diag["syntax_error"]:
        print(f"    Syntax Error : {diag['syntax_error']}")
    print(f"    Target Line  : {diag['error_line']}")
    print(f"    Diff Blocks  : {len(diag['diff_blocks'])} mutation(s) found")

    print("\n[*] Bringing code editor to front in 1.5 seconds...")
    print("    (Hands off the keyboard! Just pretend you are typing!)")
    time.sleep(1.5)

    focus_ide_window()
    time.sleep(0.4)

    typer = HumanTyper(wpm=70)

    # Process each diff block (or replace whole content if corrupted heavily)
    opcodes = diag["diff_blocks"]

    if len(opcodes) > 0 and len(opcodes) <= 5:
        # Surgical fix of each diff block
        for tag, i1, i2, j1, j2 in opcodes:
            start_line = i1 + 1
            delete_count = i2 - i1
            clean_lines = diag["golden_lines"][j1:j2]
            clean_snippet = "".join(clean_lines).rstrip("\r\n")

            print(f"[*] Navigating to Line {start_line}...")
            typer.navigate_to_line(start_line)

            if delete_count > 0:
                print(f"[*] Deleting {delete_count} broken line(s)...")
                typer.delete_broken_lines(delete_count)
                time.sleep(0.3)

            if clean_snippet:
                print(f"[*] Typing repair code ({len(clean_snippet)} chars)...")
                typer.type_string(clean_snippet)
                time.sleep(0.4)

            typer.save_file()
            time.sleep(0.4)

    else:
        # High corruption: Select all and retype cleanly with speed
        print("[*] Multiple alterations detected. Rebuilding cleanly...")
        typer.navigate_to_line(1)
        send_combo(VK_CONTROL, ord("A"))
        time.sleep(0.15)
        press_key(VK_BACK)
        time.sleep(0.2)

        # Type clean code
        clean_full_text = diag["golden_text"].rstrip("\r\n")
        typer.type_string(clean_full_text)
        time.sleep(0.3)
        typer.save_file()

    # Final Verification
    time.sleep(0.5)
    post_diag = diagnose_pos_system()
    if not post_diag["has_error"]:
        print("\n" + "=" * 65)
        print("  [SUCCESS] pos_system.py has been completely repaired!")
        print("  Syntax validated: OK | Baseline sync: OK")
        print("=" * 65 + "\n")
        return True
    else:
        print("[*] Performing direct file fallback sync...")
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            f.write(diag["golden_text"])
        print("[OK] Direct file sync completed.")
        return True


# -------------------------------------------------------------
# Background Daemon & Hotkey Listener
# -------------------------------------------------------------
def run_daemon(watch_mode=False):
    """
    Runs in the background:
    - Listens for [Ctrl + Keypad *] hotkey to trigger repair on demand.
    - If watch_mode=True, also triggers when pos_system.py is saved with errors.
    """
    print("=" * 65)
    print("       AUTO-REPAIR SYSTEM DAEMON (STANDBY MODE)")
    print("=" * 65)
    print(f"[*] Monitored Target : {TARGET_FILE}")
    print(f"[*] Golden Reference : {GOLDEN_FILE}")
    print(f"[*] Hotkey Trigger   : Press [Ctrl + Keypad *] anytime to trigger human repair")
    print(f"[*] Auto-Watch Mode  : {'ENABLED' if watch_mode else 'DISABLED (Use [Ctrl + Keypad *])'}")
    print("=" * 65)
    print("\nWaiting for trigger... (Press Ctrl+C to exit)\n")

    last_mtime = os.path.getmtime(TARGET_FILE) if os.path.exists(TARGET_FILE) else 0

    try:
        while True:
            # Check Ctrl + Keypad Asterisk hotkey state
            # GetAsyncKeyState returns highest bit set (0x8000) if key is currently down
            ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
            numpad_mult_down = bool(user32.GetAsyncKeyState(VK_MULTIPLY) & 0x8000)

            if ctrl_down and numpad_mult_down:
                print("\n[>>] [Ctrl + Keypad *] HOTKEY PRESSED! Starting human-typing auto-repair...")
                time.sleep(0.35)  # Wait for keys to release
                perform_human_repair()
                print("\nResuming standby mode. Waiting for next trigger...")
                time.sleep(1.0)

            # Auto-watch check if enabled
            if watch_mode and os.path.exists(TARGET_FILE):
                cur_mtime = os.path.getmtime(TARGET_FILE)
                if cur_mtime != last_mtime:
                    last_mtime = cur_mtime
                    # File was modified; check if it has errors
                    time.sleep(1.0)  # Let writer finish saving
                    diag = diagnose_pos_system()
                    if diag["has_error"]:
                        print("\n[>>] Code error detected after save! Starting auto-repair...")
                        perform_human_repair()
                        last_mtime = os.path.getmtime(TARGET_FILE)
                        print("\nResuming standby mode...")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[!] Daemon stopped by user.")


# -------------------------------------------------------------
# Entry Point
# -------------------------------------------------------------
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--now" in args or "-n" in args:
        # Immediate repair execution
        perform_human_repair()
    elif "--watch" in args or "-w" in args:
        # Daemon with auto-watch on file save
        run_daemon(watch_mode=True)
    else:
        # Standard background daemon with Ctrl + Keypad * hotkey listener
        run_daemon(watch_mode=False)
