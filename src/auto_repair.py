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
import math
import os
import queue
import random
import sys
import threading
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

# -----------------------------------------------------------------
# Behaviour Flags
# -----------------------------------------------------------------
# Set to True if VS Code auto-closes brackets/quotes as you type.
# When True, send_char() will press Delete after each opening
# bracket so the phantom auto-inserted closing char is removed.
VS_CODE_AUTOCLOSING = True
# Only opening brackets auto-close in VS Code (quotes step over and do not delete):
_AUTOCLOSING_OPENERS = set('([{')

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

# Low-Level Keyboard Hook Definitions (WH_KEYBOARD_LL)
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT))
WH_KEYBOARD_LL = 13
LLKHF_INJECTED = 0x10
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105


EXTENDED_VKS = {
    VK_HOME, VK_END, VK_DELETE, VK_LEFT, VK_RIGHT, VK_UP, VK_DOWN,
    0x21, 0x22, 0x2D  # PageUp, PageDown, Insert
}


def _send_input(inputs):
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def key_down(vk=0, scan=0, flags=0):
    if vk in EXTENDED_VKS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if vk and not scan:
        scan = user32.MapVirtualKeyW(vk, 0)
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None
    _send_input([inp])


def key_up(vk=0, scan=0, flags=0):
    if vk in EXTENDED_VKS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if vk and not scan:
        scan = user32.MapVirtualKeyW(vk, 0)
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags | KEYEVENTF_KEYUP
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None
    _send_input([inp])


def press_key(vk, delay=0.02):
    key_down(vk=vk)
    time.sleep(delay)
    key_up(vk=vk)


def send_combo(*vks, hold_delay=0.03):
    """Presses multiple keys down in order, then releases them in reverse order."""
    for vk in vks:
        key_down(vk=vk)
        time.sleep(0.01)
    time.sleep(hold_delay)
    for vk in reversed(vks):
        key_up(vk=vk)
        time.sleep(0.01)


def reset_line_to_column_0():
    """
    Clears any auto-indented whitespace on the current line in VS Code
    and guarantees cursor sits firmly at column 0 without touching text to the right.
    """
    time.sleep(0.015)
    # Select from current cursor back to column 0 (only the auto-indented whitespace)
    send_combo(VK_SHIFT, VK_HOME)
    time.sleep(0.008)
    press_key(VK_DELETE)
    time.sleep(0.008)
    press_key(VK_HOME)
    time.sleep(0.008)


def send_char(char):
    """Sends a single character via Unicode input, handling newlines and tabs.

    When VS_CODE_AUTOCLOSING is True, automatically presses Delete after
    injecting any bracket or quote opener to remove the phantom auto-closing
    character VS Code inserts, preventing doubled closers like )) or "".
    """
    if char == "\r":
        return
    if char == "\n":
        press_key(VK_RETURN)
        time.sleep(0.02)
        reset_line_to_column_0()
    elif char == "\t":
        press_key(VK_TAB)
    else:
        code = ord(char)
        key_down(vk=0, scan=code, flags=KEYEVENTF_UNICODE)
        time.sleep(0.006)
        key_up(vk=0, scan=code, flags=KEYEVENTF_UNICODE)
        # Compensate for VS Code auto-closing pairs
        if VS_CODE_AUTOCLOSING and char in _AUTOCLOSING_OPENERS:
            time.sleep(0.012)
            press_key(VK_DELETE)


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


def merge_opcodes(opcodes, max_gap=2):
    """Merges adjacent diff blocks separated by <= max_gap lines into a single cohesive repair block."""
    if not opcodes:
        return []
    merged = [list(opcodes[0])]
    for tag, i1, i2, j1, j2 in opcodes[1:]:
        prev = merged[-1]
        if i1 - prev[2] <= max_gap and j1 - prev[4] <= max_gap:
            prev[0] = "replace"
            prev[2] = i2
            prev[4] = j2
        else:
            merged.append([tag, i1, i2, j1, j2])
    return [tuple(m) for m in merged]


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
        return {"has_error": True, "error_msg": "File pos_system.py not found!"}

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

    # 2. Check diff against golden baseline (filtering blank line anchors and merging adjacent fragments)
    matcher = difflib.SequenceMatcher(lambda s: s.strip() == "", current_lines, golden_lines)
    raw_opcodes = [op for op in matcher.get_opcodes() if op[0] != "equal"]
    opcodes = merge_opcodes(raw_opcodes, max_gap=2)

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
# Human-like Navigation & Editing Helpers
# -------------------------------------------------------------
class HumanTyper:
    def __init__(self, wpm=36, typo_chance=0.025):
        self.wpm = wpm
        self.typo_chance = typo_chance
        self.chars_since_pause = 0
        self.current_line = None

    def type_string(self, text):
        """Types a string character-by-character with a much slower, deliberate human pacing and realistic random delays."""
        lines = text.split("\n")
        total_lines = len(lines)

        for line_idx, line in enumerate(lines):
            col = 0
            is_leading_indent = True

            while col < len(line):
                char = line[col]

                # Check if still in leading whitespace indentation
                if char not in " \t":
                    is_leading_indent = False

                # Occasional simulated human typo with deliberate reaction and backspace correction
                if not is_leading_indent and self.typo_chance > 0 and char.isalpha() and random.random() < self.typo_chance:
                    wrong_char = chr(ord(char) + (1 if random.random() > 0.5 else -1))
                    send_char(wrong_char)
                    # Natural human delay before noticing the typo
                    time.sleep(random.uniform(0.22, 0.40))
                    press_key(VK_BACK)
                    time.sleep(random.uniform(0.15, 0.28))

                send_char(char)
                self.chars_since_pause += 1

                # Much slower, natural keystroke delays
                if is_leading_indent:
                    # Clear, visible indentation steps
                    delay = random.uniform(0.08, 0.16)
                else:
                    # Deliberate human character speed (~32-40 WPM, 130ms - 260ms per key)
                    delay = random.uniform(0.13, 0.27)

                    # Distinct pause when typing syntax symbols & operators
                    if char in " ,;:().[]{}='\"":
                        delay += random.uniform(0.20, 0.45)

                    # Organic thinking pause every 18 to 32 characters (thinking of next token)
                    if self.chars_since_pause > random.randint(18, 32):
                        delay += random.uniform(0.50, 1.10)
                        self.chars_since_pause = 0

                time.sleep(delay)
                col += 1

            # End of line newline
            if line_idx < total_lines - 1:
                press_key(VK_RETURN)
                time.sleep(0.02)
                reset_line_to_column_0()
                time.sleep(random.uniform(0.70, 1.40))
                self.chars_since_pause = 0

    def navigate_to_line(self, line_num):
        """
        Jumps to line_num using Ctrl+G (Go to Line) unconditionally.

        The previous optimisation of using Up/Down arrow keys for nearby
        lines (<= 5 apart) caused cursor drift because current_line tracking
        could be off by one after typing.  Absolute Ctrl+G navigation is
        always correct and removes that entire class of bug.
        """
        time.sleep(random.uniform(0.20, 0.35))
        send_combo(VK_CONTROL, ord("G"))
        time.sleep(random.uniform(0.25, 0.40))

        # Type line number digit by digit
        for c in str(line_num):
            send_char(c)
            time.sleep(random.uniform(0.08, 0.15))
        time.sleep(random.uniform(0.20, 0.30))
        press_key(VK_RETURN)
        time.sleep(random.uniform(0.25, 0.40))
        # Double-Home: first jump goes to first non-whitespace, second to col 0
        press_key(VK_HOME)
        press_key(VK_HOME)
        time.sleep(0.05)

        self.current_line = line_num

    def delete_broken_lines(self, count):
        """
        Deletes `count` whole lines starting from the current cursor line,
        including their trailing newline characters.

        Previous approach used Shift+End+Backspace which erased line *content*
        but left the newline itself behind, resulting in empty phantom lines that
        prevented the diff from ever resolving cleanly.

        VS Code's Ctrl+Shift+K ("Delete Line") removes the entire line including
        its newline in one keystroke, which is exactly what we need.
        """
        if count <= 0:
            return
        # Make sure we are at the start of the line before deleting
        press_key(VK_HOME)
        time.sleep(0.015)
        press_key(VK_HOME)
        time.sleep(0.015)
        for _ in range(count):
            send_combo(VK_CONTROL, VK_SHIFT, ord("K"))
            time.sleep(0.04)

    def save_file(self):
        """Saves current file with Ctrl+S."""
        time.sleep(random.uniform(0.35, 0.55))
        send_combo(VK_CONTROL, ord("S"))
        time.sleep(random.uniform(0.40, 0.60))


# -------------------------------------------------------------
# Direct Navigation & Editing Helpers
# -------------------------------------------------------------
def navigate_to_line_direct(line_num):
    """
    Smooth, deterministic navigation to line_num using VS Code's Ctrl+G (Go to Line).
    Sends line number with proper dialog settling times, presses Enter, and positions
    cursor firmly at column 0.
    """
    time.sleep(0.15)
    send_combo(VK_CONTROL, ord("G"))
    time.sleep(0.28)  # Let Quick Open dialog open and focus
    for digit in str(line_num):
        code = ord(digit)
        key_down(vk=0, scan=code, flags=KEYEVENTF_UNICODE)
        time.sleep(0.02)
        key_up(vk=0, scan=code, flags=KEYEVENTF_UNICODE)
        time.sleep(0.03)
    time.sleep(0.15)
    press_key(VK_RETURN)
    time.sleep(0.22)  # Let VS Code jump and settle
    press_key(VK_HOME)
    time.sleep(0.02)
    press_key(VK_HOME)
    time.sleep(0.05)


def delete_lines_direct(count):
    """Deletes `count` whole lines using Ctrl+Shift+K starting from current line."""
    if count <= 0:
        return
    press_key(VK_HOME)
    time.sleep(0.015)
    press_key(VK_HOME)
    time.sleep(0.015)
    for _ in range(count):
        send_combo(VK_CONTROL, VK_SHIFT, ord("K"))
        time.sleep(0.05)


# -------------------------------------------------------------
# Unified HackerTyper Engine
# -------------------------------------------------------------
def repair_with_hacker_mode(opcodes, current_lines, golden_lines, golden_text):
    """
    Unified HackerTyper engine:
    1. Single persistent low-level keyboard hook installed for the whole session.
    2. Navigation & setup (Ctrl+G, line jump, line deletion) runs AUTOMATICALLY
       and securely — the hook SWALLOWS all physical user keystrokes during this
       phase so user mashing CAN NEVER corrupt VS Code dialogs or leak into code!
    3. Typing phase is USER-DRIVEN — the user mashes any keys on their keyboard,
       and each keypress types the next character of the clean fix into the editor!
       Backspace rewinds a character. Escape aborts immediately.
    4. Auto-saves (Ctrl+S) securely and releases the hook when finished.
    """
    abort_event = threading.Event()
    stop_event = threading.Event()
    hook_installed = threading.Event()
    event_queue = queue.Queue()

    # When accept_typing[0] is True, user keystrokes feed into the code typing queue.
    # When False (during navigation, dialogs, saving), all keystrokes are swallowed and discarded.
    accept_typing = [False]

    def hook_thread_worker():
        cb_holder = []

        def hook_proc(nCode, wParam, lParam):
            if nCode >= 0 and lParam:
                flags = lParam.contents.flags
                # Let our own injected SendInput keystrokes pass straight through
                if flags & LLKHF_INJECTED:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                vk = lParam.contents.vkCode

                # Escape aborts the entire session immediately
                if vk == VK_ESCAPE:
                    abort_event.set()
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                # Ignore pure modifier keys (Shift, Ctrl, Alt, CapsLock)
                if vk in (VK_SHIFT, 0xA0, 0xA1,
                          VK_CONTROL, 0xA2, 0xA3,
                          VK_MENU, 0xA4, 0xA5,
                          0x14):
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    # ALWAYS swallow physical keydown so user keys NEVER reach VS Code directly!
                    if accept_typing[0]:
                        if vk == VK_BACK:
                            event_queue.put("BACKSPACE")
                        else:
                            event_queue.put("ADVANCE")
                    return 1

                if wParam in (WM_KEYUP, WM_SYSKEYUP):
                    return 1  # Swallow keyup as well

            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        hook_func = HOOKPROC(hook_proc)
        cb_holder.append(hook_func)
        hhook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_func, None, 0)
        hook_installed.set()

        if not hhook:
            return

        try:
            msg = wintypes.MSG()
            while not stop_event.is_set() and not abort_event.is_set():
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.001)
        finally:
            user32.UnhookWindowsHookEx(hhook)

    hook_thread = threading.Thread(target=hook_thread_worker, daemon=True)
    hook_thread.start()
    hook_installed.wait(timeout=1.0)

    def flush_queue():
        while not event_queue.empty():
            try:
                event_queue.get_nowait()
            except queue.Empty:
                break

    try:
        if len(opcodes) > 0 and len(opcodes) <= 25:
            # Process diff blocks from BOTTOM to TOP so earlier line numbers remain intact
            for block_num, (tag, i1, i2, j1, j2) in enumerate(reversed(opcodes), 1):
                if abort_event.is_set():
                    break

                start_line = i1 + 1
                delete_count = i2 - i1
                clean_lines = golden_lines[j1:j2]
                clean_chars = "".join(clean_lines)

                # ---- PHASE 1: Navigation & Line Prep (Automatic, Swallow all keys) ----
                accept_typing[0] = False
                flush_queue()

                print(f"[*] Navigating to Line {start_line} (Block {block_num}/{len(opcodes)})...")
                focus_ide_window()
                navigate_to_line_direct(start_line)

                if delete_count > 0:
                    print(f"[*] Removing {delete_count} broken line(s)...")
                    delete_lines_direct(delete_count)
                    time.sleep(0.08)

                if delete_count == 0 and start_line > len(current_lines):
                    # EOF append: jump to end and create new line
                    press_key(VK_END)
                    press_key(VK_RETURN)
                    reset_line_to_column_0()
                    time.sleep(0.05)

                flush_queue()

                # ---- PHASE 2: Hacker Mode Typing (Driven by User Keypresses) ----
                if clean_chars:
                    print(f"[>>] HACKER MODE READY! Mash any key to type fix ({len(clean_chars)} chars)...")
                    accept_typing[0] = True
                    flush_queue()

                    char_idx = 0
                    total_chars = len(clean_chars)

                    while char_idx < total_chars and not abort_event.is_set():
                        try:
                            evt = event_queue.get(timeout=0.03)
                        except queue.Empty:
                            continue

                        if abort_event.is_set():
                            break

                        if evt == "BACKSPACE":
                            if char_idx > 0:
                                char_idx -= 1
                                press_key(VK_BACK)
                                time.sleep(0.008)
                        elif evt == "ADVANCE":
                            ch = clean_chars[char_idx]
                            send_char(ch)
                            char_idx += 1

                # ---- PHASE 3: Save (Automatic, Protected) ----
                accept_typing[0] = False
                flush_queue()
                time.sleep(0.10)
                send_combo(VK_CONTROL, ord("S"))
                time.sleep(0.25)
                flush_queue()

        else:
            # Full file reconstruction for heavy corruption
            accept_typing[0] = False
            flush_queue()
            print("[*] Heavy corruption detected. Resetting entire file...")
            focus_ide_window()
            navigate_to_line_direct(1)
            send_combo(VK_CONTROL, ord("A"))
            time.sleep(0.12)
            press_key(VK_BACK)
            time.sleep(0.15)
            reset_line_to_column_0()

            print(f"[>>] HACKER MODE READY! Mash any key to rebuild file ({len(golden_text)} chars)...")
            accept_typing[0] = True
            flush_queue()

            char_idx = 0
            total_chars = len(golden_text)
            while char_idx < total_chars and not abort_event.is_set():
                try:
                    evt = event_queue.get(timeout=0.03)
                except queue.Empty:
                    continue

                if abort_event.is_set():
                    break

                if evt == "BACKSPACE":
                    if char_idx > 0:
                        char_idx -= 1
                        press_key(VK_BACK)
                        time.sleep(0.008)
                elif evt == "ADVANCE":
                    ch = golden_text[char_idx]
                    send_char(ch)
                    char_idx += 1

            accept_typing[0] = False
            flush_queue()
            time.sleep(0.15)
            send_combo(VK_CONTROL, ord("S"))
            time.sleep(0.30)
            flush_queue()

    finally:
        accept_typing[0] = False
        stop_event.set()
        hook_thread.join(timeout=0.5)
        time.sleep(0.05)


# -------------------------------------------------------------
# Main Repair Workflow
# -------------------------------------------------------------
def perform_human_repair(auto_type=False):
    """
    Executes the full automated repair sequence:
    1. Diagnoses errors & diffs in pos_system.py
    2. Brings editor to foreground
    3. Pre-builds the ENTIRE repair as a flat list of atomic steps
       (Ctrl+G, digit chars, Enter, Ctrl+Shift+K, code chars, Ctrl+S, etc.)
    4. auto_type=False: runs repair_with_hacker_mode() — the single persistent
       keyboard hook drives ALL steps (navigation AND typing) from physical key
       presses.  The hook is NEVER dropped between steps, so the user can mash
       freely without any keystrokes ever bleeding into VS Code dialogs.
    5. auto_type=True: HumanTyper auto-types everything at ~36 WPM (watch daemon).
    6. Post-repair verify; falls back to direct disk write if still broken.

    Args:
        auto_type (bool): When True, types fixes automatically without keyboard input.
                          Use this for unattended watch-mode or --auto CLI flag.
    """
    print("\n" + "=" * 65)
    print("  [AUTO-REPAIR] Initiating diagnostic scan on pos_system.py...")
    print("=" * 65)

    # Bring IDE to front and flush the editor buffer to disk before reading
    focus_ide_window()
    time.sleep(0.2)
    send_combo(VK_CONTROL, ord("S"))
    time.sleep(0.40)

    diag = diagnose_pos_system()

    if not diag["has_error"]:
        print("[OK] pos_system.py is 100% clean and free of errors. No fix needed!")
        return True

    print(f"[!] Error detected in pos_system.py:")
    if diag["syntax_error"]:
        print(f"    Syntax Error : {diag['syntax_error']}")
    print(f"    Target Line  : {diag['error_line']}")
    print(f"    Diff Blocks  : {len(diag['diff_blocks'])} mutation(s) found")

    focus_ide_window()
    time.sleep(0.2)

    opcodes      = diag["diff_blocks"]
    cur_lines    = diag["current_lines"]
    gold_lines   = diag["golden_lines"]
    golden_text  = diag["golden_text"]

    if auto_type:
        # ----------------------------------------------------------------
        # AUTO mode: drive everything with HumanTyper (no user interaction)
        # ----------------------------------------------------------------
        print("\n[*] AUTO MODE: Typing fixes automatically...")
        typer = HumanTyper(wpm=36)

        if len(opcodes) > 0 and len(opcodes) <= 25:
            for tag, i1, i2, j1, j2 in reversed(opcodes):
                start_line   = i1 + 1
                delete_count = i2 - i1
                clean_lines  = gold_lines[j1:j2]
                clean_snippet = "".join(clean_lines)

                print(f"[*] Navigating to Line {start_line} (tag={tag}, del={delete_count}, ins={len(clean_lines)})...")
                typer.navigate_to_line(start_line)
                time.sleep(random.uniform(0.20, 0.35))

                if delete_count > 0:
                    print(f"[*] Removing {delete_count} broken line(s) with Ctrl+Shift+K...")
                    typer.delete_broken_lines(delete_count)
                    time.sleep(0.10)

                if delete_count == 0 and start_line > len(cur_lines):
                    press_key(VK_END)
                    press_key(VK_RETURN)
                    reset_line_to_column_0()
                    time.sleep(0.05)

                if clean_snippet:
                    print(f"[*] Auto-typing fix ({len(clean_snippet)} chars)...")
                    typer.type_string(clean_snippet)
                    time.sleep(0.15)

                typer.save_file()
                time.sleep(0.25)
        else:
            print("[*] Heavy mutation detected (>25 diff blocks). Rebuilding entire file...")
            typer.navigate_to_line(1)
            send_combo(VK_CONTROL, ord("A"))
            time.sleep(0.15)
            press_key(VK_BACK)
            time.sleep(0.20)
            reset_line_to_column_0()
            print(f"[*] Auto-typing full file ({len(golden_text)} chars)...")
            typer.type_string(golden_text)
            time.sleep(0.20)
            typer.save_file()

    else:
        # ----------------------------------------------------------------
        # HACKER mode: single persistent hook drives code typing key-by-key
        # Navigation is 100% automated with zero-leak key swallowing
        # ----------------------------------------------------------------
        print("\n[*] Initializing HackerTyper mode...")
        print("    Mash any key to type out the fixes!")
        print("    Backspace rewinds characters. Escape aborts.")
        print("    Physical keys are safely intercepted and will never corrupt dialogs.\n")

        repair_with_hacker_mode(opcodes, cur_lines, gold_lines, golden_text)

    # Post-repair verification
    time.sleep(0.35)
    post_diag = diagnose_pos_system()
    if not post_diag["has_error"]:
        print("\n" + "=" * 65)
        print("  [SUCCESS] pos_system.py has been completely repaired!")
        print("  Syntax validated: OK | Baseline sync: OK")
        print("=" * 65 + "\n")
        return True
    else:
        # Last resort: write the golden content directly to disk.
        print("[!] Verification still failed after typing. Falling back to direct disk write...")
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            f.write(diag["golden_text"])
        print("[OK] Direct file sync completed. File is now clean.")
        return True


# -------------------------------------------------------------
# Background Daemon & Hotkey Listener (Resilient Watchdog)
# -------------------------------------------------------------
def run_daemon(watch_mode=False, silent=False):
    """
    Runs in the background with auto-recovery watchdog:
    - Listens for [Ctrl + Keypad *] or [Ctrl + F9] hotkey to trigger repair on demand.
    - If watch_mode=True, also triggers when pos_system.py is saved with errors.
    """
    if not silent:
        print("=" * 65)
        print("       AUTO-REPAIR SYSTEM DAEMON (STANDBY MODE)")
        print("=" * 65)
        print(f"[*] Monitored Target : {TARGET_FILE}")
        print(f"[*] Golden Reference : {GOLDEN_FILE}")
        print(f"[*] Hotkey Trigger   : Press [Ctrl + Keypad *] or [Ctrl + F9] to trigger human repair")
        print(f"[*] Auto-Watch Mode  : {'ENABLED' if watch_mode else 'DISABLED (Use Hotkey)'}")
        print("=" * 65)
        print("\nWaiting for trigger... (Press Ctrl+C to exit)\n")

    while True:
        try:
            last_mtime = os.path.getmtime(TARGET_FILE) if os.path.exists(TARGET_FILE) else 0

            while True:
                # Check Ctrl + Keypad Asterisk or Ctrl + F9 hotkey state
                ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                numpad_mult_down = bool(user32.GetAsyncKeyState(VK_MULTIPLY) & 0x8000)
                f9_down = bool(user32.GetAsyncKeyState(VK_F9) & 0x8000)

                if (ctrl_down and numpad_mult_down) or (ctrl_down and f9_down):
                    print("\n[>>] HOTKEY PRESSED! Starting human-typing auto-repair...")
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
                            print("\n[>>] Code error detected after save! Starting auto-repair (auto-type)...")
                            # In watch mode nobody is there to mash keys, so auto_type=True
                            perform_human_repair(auto_type=True)
                            last_mtime = os.path.getmtime(TARGET_FILE)
                            print("\nResuming standby mode...")

                time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n[!] Daemon stopped by user.")
            break
        except Exception:
            # Resilient auto-recovery on transient Win32 API glitches
            time.sleep(1.0)


# -------------------------------------------------------------
# Headless Console Management
# -------------------------------------------------------------
def hide_console():
    """Hides any visible console/CMD window associated with this process."""
    try:
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
    except Exception:
        pass


def make_headless():
    """Hides the console window and silences standard outputs so it runs invisibly."""
    hide_console()
    try:
        devnull = open(os.devnull, "w", encoding="utf-8")
        sys.stdout = devnull
        sys.stderr = devnull
    except Exception:
        pass


# -------------------------------------------------------------
# Entry Point
# -------------------------------------------------------------
if __name__ == "__main__":
    args = sys.argv[1:]

    # By default, run 100% headless (invisible CMD) unless explicitly passed --visible
    if "--visible" not in args:
        make_headless()

    if "--now" in args or "-n" in args:
        # Immediate repair: interactive HackerTyper (mash keys to drive typing)
        perform_human_repair(auto_type=False)
    elif "--auto" in args or "-a" in args:
        # Immediate repair: fully automatic, no keyboard interaction required
        perform_human_repair(auto_type=True)
    elif "--watch" in args or "-w" in args:
        # Daemon with auto-watch on file save (uses auto_type=True internally)
        run_daemon(watch_mode=True, silent=True)
    else:
        # Standard background daemon with Ctrl+Keypad* / Ctrl+F9 hotkey
        # Interactive HackerTyper is used when triggered by hotkey.
        run_daemon(watch_mode=False, silent=True)
