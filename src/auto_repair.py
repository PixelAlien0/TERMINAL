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
    and guarantees cursor sits firmly at column 0.
    """
    time.sleep(0.015)
    # Home twice ensures column 0 (1st: first non-whitespace, 2nd: col 0)
    press_key(VK_HOME)
    time.sleep(0.008)
    press_key(VK_HOME)
    time.sleep(0.008)
    # Select from column 0 to end of line
    send_combo(VK_SHIFT, VK_END)
    time.sleep(0.008)
    # Delete all auto-indented whitespace
    press_key(VK_DELETE)
    time.sleep(0.008)
    # Ensure cursor is at column 0
    press_key(VK_HOME)
    time.sleep(0.008)


def send_char(char):
    """Sends a single character via Unicode input, handling newlines and tabs."""
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
        Assumes pos_system.py is ALREADY open in the active editor.
        Navigates to line_num:
        - If nearby (<= 5 lines away), uses natural Up/Down arrow travel.
        - Otherwise, jumps directly using Ctrl+G with realistic keystroke delays.
        """
        time.sleep(random.uniform(0.20, 0.35))
        if self.current_line is not None and abs(self.current_line - line_num) <= 5:
            delta = line_num - self.current_line
            vk = VK_DOWN if delta > 0 else VK_UP
            for _ in range(abs(delta)):
                press_key(vk)
                time.sleep(random.uniform(0.04, 0.08))
            press_key(VK_HOME)
            press_key(VK_HOME)
            time.sleep(0.08)
        else:
            # Go to line (Ctrl+G)
            send_combo(VK_CONTROL, ord("G"))
            time.sleep(random.uniform(0.25, 0.40))

            # Type line number deliberately
            for c in str(line_num):
                send_char(c)
                time.sleep(random.uniform(0.08, 0.15))
            time.sleep(random.uniform(0.20, 0.30))
            press_key(VK_RETURN)
            time.sleep(random.uniform(0.25, 0.40))
            press_key(VK_HOME)
            press_key(VK_HOME)
            time.sleep(0.05)

        self.current_line = line_num

    def delete_broken_lines(self, count):
        """
        Deletes `count` lines starting from the current cursor line
        by selecting from line start through line `count` end with continuous Shift hold,
        leaving a single empty line ready for typing without eating subsequent lines.
        """
        if count <= 0:
            return
        press_key(VK_HOME)
        time.sleep(0.015)
        press_key(VK_HOME)
        time.sleep(0.015)

        # Hold Shift continuously to guarantee unbroken selection across all lines
        key_down(VK_SHIFT)
        time.sleep(0.01)
        if count > 1:
            for _ in range(count - 1):
                press_key(VK_DOWN)
                time.sleep(0.015)
        press_key(VK_END)
        time.sleep(0.015)
        key_up(VK_SHIFT)
        time.sleep(0.01)

        press_key(VK_BACK)
        time.sleep(0.02)
        press_key(VK_HOME)
        time.sleep(0.01)

    def save_file(self):
        """Saves current file with Ctrl+S."""
        time.sleep(random.uniform(0.35, 0.55))
        send_combo(VK_CONTROL, ord("S"))
        time.sleep(random.uniform(0.40, 0.60))


# -------------------------------------------------------------
# HackerTyper Simulation: Mashing Random Keys Types the Real Fix
# -------------------------------------------------------------
class HackerTyper:
    def __init__(self, target_text):
        # Normalize line endings so every line boundary is a single clean '\n'
        self.text = target_text.replace("\r\n", "\n").replace("\r", "\n")
        self.index = 0
        self.total_len = len(self.text)
        self.finished = (self.total_len == 0)

    def is_at_newline(self):
        """Returns True if the next character waiting to be emitted is a newline."""
        return self.index < self.total_len and self.text[self.index] == "\n"

    def emit_char(self):
        """
        Emits EXACTLY 1 character from target_text into the editor per physical keystroke.
        Pauses at the end of the line (\\n) so the user can manually press Enter to go down.
        """
        if self.index >= self.total_len:
            self.finished = True
            return

        # End of current line reached: pause and wait for the user to physically hit Enter!
        if self.text[self.index] == "\n":
            return

        ch = self.text[self.index]
        self.index += 1
        send_char(ch)

        if self.index >= self.total_len:
            self.finished = True

    def emit_enter(self):
        """
        Emits a newline when the user physically presses the Enter key,
        moving the cursor down to the next line.
        """
        if self.index >= self.total_len:
            self.finished = True
            return

        if self.text[self.index] == "\n":
            self.index += 1
            send_char("\n")
        else:
            # Forgiving fallback if pressed mid-line
            ch = self.text[self.index]
            self.index += 1
            send_char(ch)

        if self.index >= self.total_len:
            self.finished = True

    def rewind_char(self):
        """
        Erases 1 character backward in the editor and decrements self.index
        when the user physically presses Backspace.
        """
        if self.index <= 0:
            return

        self.index -= 1
        press_key(VK_BACK)
        time.sleep(0.008)


def type_with_hacker_mode(target_text):
    """
    Two-Thread Bulletproof HackerTyper Engine:
    - Thread 1 (Dedicated Hook Thread): Runs pure Win32 hook with zero sleeps/delays.
      Swallows every physical key instant (<0.01ms), completely preventing Windows LowLevelHooksTimeout drops.
    - Thread 2 (Current Worker Thread): Pulls from thread-safe queue and emits inputs into editor.
    - Line Enter Control: Typing letters fills out the line and pauses at the end.
      The user physically presses Enter to go down to the next line.
    Zero real letters can EVER leak into the editor even under extreme key spamming!
    """
    if not target_text:
        return

    typer = HackerTyper(target_text)
    event_queue = queue.Queue()
    stop_event = threading.Event()
    abort_event = threading.Event()
    hook_installed = threading.Event()

    def hook_thread_worker():
        cb_holder = []

        def hook_proc(nCode, wParam, lParam):
            if nCode >= 0 and lParam:
                flags = lParam.contents.flags
                # Injected keystrokes from SendInput must pass directly to the editor!
                if flags & LLKHF_INJECTED:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                vk = lParam.contents.vkCode

                # Escape key aborts typing session immediately
                if vk == VK_ESCAPE:
                    abort_event.set()
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                # Standalone modifier keys (Shift, Ctrl, Alt, CapsLock) pass through
                if vk in (VK_SHIFT, 0xA0, 0xA1, VK_CONTROL, 0xA2, 0xA3, VK_MENU, 0xA4, 0xA5, 0x14):
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)

                # Physical Backspace key down: queue rewind event and swallow
                if vk == VK_BACK:
                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        event_queue.put("BACKSPACE")
                    return 1

                # Physical Enter key down: queue ENTER event and swallow
                if vk == VK_RETURN:
                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        event_queue.put("ENTER")
                    return 1

                # Any other physical key down: queue character advance event and swallow
                if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    event_queue.put("CHAR")
                    return 1

                # Physical key up: swallow to prevent Windows character echo
                if wParam in (WM_KEYUP, WM_SYSKEYUP):
                    return 1

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
                # Rapid non-blocking message pump
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.001)
        finally:
            user32.UnhookWindowsHookEx(hhook)

    # Spawn dedicated hook thread
    hook_thread = threading.Thread(target=hook_thread_worker, daemon=True)
    hook_thread.start()
    hook_installed.wait(timeout=1.0)

    try:
        # Worker execution loop
        while not typer.finished and not abort_event.is_set():
            try:
                event = event_queue.get(timeout=0.015)
            except queue.Empty:
                continue

            if event == "BACKSPACE":
                typer.rewind_char()
            elif event == "ENTER":
                typer.emit_enter()
            elif event == "CHAR":
                typer.emit_char()

    finally:
        stop_event.set()
        hook_thread.join(timeout=0.4)
        time.sleep(0.05)


# -------------------------------------------------------------
# Main Repair Workflow
# -------------------------------------------------------------
def perform_human_repair():
    """
    Executes the full automated repair sequence:
    1. Diagnoses error & diff in pos_system.py
    2. Brings editor to foreground
    3. Jumps directly to exact line (assuming file already open)
    4. Deletes broken code
    5. Activates HackerTyper mode: mash any random keys on keyboard to type real fix!
    6. Saves file and halts cleanly
    """
    print("\n" + "=" * 65)
    print("  [AUTO-REPAIR] Initiating diagnostic scan on pos_system.py...")
    print("=" * 65)

    # First bring IDE to front and trigger Ctrl+S so active buffer in editor is saved to disk
    focus_ide_window()
    time.sleep(0.2)
    send_combo(VK_CONTROL, ord("S"))
    time.sleep(0.35)

    diag = diagnose_pos_system()

    if not diag["has_error"]:
        print("[OK] pos_system.py is 100% clean and free of errors. No fix needed!")
        return True

    print(f"[!] Error detected in pos_system.py:")
    if diag["syntax_error"]:
        print(f"    Syntax Error : {diag['syntax_error']}")
    print(f"    Target Line  : {diag['error_line']}")
    print(f"    Diff Blocks  : {len(diag['diff_blocks'])} mutation(s) found")

    print("\n[*] Bringing code editor to front...")
    print("    (Prepare to mash keys like a hacker!)")
    time.sleep(0.5)

    focus_ide_window()
    time.sleep(0.2)

    typer = HumanTyper(wpm=36)
    opcodes = diag["diff_blocks"]

    if len(opcodes) > 0 and len(opcodes) <= 25:
        # Surgical fix of each diff block from bottom to top so line indices do not shift
        for tag, i1, i2, j1, j2 in reversed(opcodes):
            start_line = i1 + 1
            delete_count = i2 - i1
            clean_lines = diag["golden_lines"][j1:j2]
            clean_snippet = "".join(clean_lines).rstrip("\r\n")

            print(f"[*] Navigating directly to Line {start_line}...")
            typer.navigate_to_line(start_line)

            # Realistic programmer reading/inspection pause before fixing
            time.sleep(random.uniform(0.35, 0.60))

            if delete_count > 0:
                print(f"[*] Deleting {delete_count} broken line(s)...")
                typer.delete_broken_lines(delete_count)
                time.sleep(0.1)
            else:
                # Missing/deleted code insertion: open a clean blank line
                if start_line > len(diag["current_lines"]):
                    press_key(VK_END)
                    press_key(VK_RETURN)
                    reset_line_to_column_0()
                else:
                    press_key(VK_HOME)
                    press_key(VK_HOME)
                    press_key(VK_RETURN)
                    press_key(VK_UP)
                    reset_line_to_column_0()
                time.sleep(0.1)

            if clean_snippet:
                print(f"[*] HackerTyper active! Mash any keys to type fix ({len(clean_snippet)} chars)...")
                print("    (Press ENTER at the end of each line to go down to the next line)")
                type_with_hacker_mode(clean_snippet)
                time.sleep(0.2)

            typer.save_file()
            typer.current_line = start_line + len(clean_lines)
            time.sleep(0.3)

    else:
        # Heavy corruption: Clean reset
        print("[*] Multiple alterations detected. Rebuilding cleanly...")
        typer.navigate_to_line(1)
        send_combo(VK_CONTROL, ord("A"))
        time.sleep(0.15)
        press_key(VK_BACK)
        time.sleep(0.2)
        reset_line_to_column_0()

        clean_full_text = diag["golden_text"]
        print(f"[*] HackerTyper active! Mash any keys to type fix ({len(clean_full_text)} chars)...")
        print("    (Press ENTER at the end of each line to go down to the next line)")
        type_with_hacker_mode(clean_full_text)
        time.sleep(0.2)
        typer.save_file()

    # Verification
    time.sleep(0.3)
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
        print(f"[*] Hotkey Trigger   : Press [Ctrl + Shift + Asterisk] (or Ctrl + Keypad * / Ctrl + F9)")
        print(f"[*] Auto-Watch Mode  : {'ENABLED' if watch_mode else 'DISABLED (Use Hotkey)'}")
        print("=" * 65)
        print("\nWaiting for trigger... (Press Ctrl+C to exit)\n")

    while True:
        try:
            last_mtime = os.path.getmtime(TARGET_FILE) if os.path.exists(TARGET_FILE) else 0

            while True:
                # Check hotkey states across all keyboard layouts:
                ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                shift_down = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
                numpad_mult = bool(user32.GetAsyncKeyState(VK_MULTIPLY) & 0x8000)
                top_row_8 = bool(user32.GetAsyncKeyState(0x38) & 0x8000)  # Top-row '8' (Shift+8 is Asterisk)
                f9_down = bool(user32.GetAsyncKeyState(VK_F9) & 0x8000)
                oem_plus = bool(user32.GetAsyncKeyState(0xBB) & 0x8000)  # OEM '+' / '*' on ISO layouts

                # Hotkey triggers on:
                # 1. Ctrl + Shift + 8 (Standard laptop/desktop keyboard typing '*')
                # 2. Ctrl + Shift + Numpad *
                # 3. Ctrl + Numpad *
                # 4. Ctrl + 8 (direct number row fallback)
                # 5. Ctrl + Shift + '+' (international layouts)
                # 6. Ctrl + F9 (function key backup)
                is_triggered = (
                    (ctrl_down and shift_down and top_row_8) or
                    (ctrl_down and shift_down and numpad_mult) or
                    (ctrl_down and numpad_mult) or
                    (ctrl_down and top_row_8) or
                    (ctrl_down and shift_down and oem_plus) or
                    (ctrl_down and f9_down)
                )

                if is_triggered:
                    print("\n[>>] HOTKEY PRESSED! Starting human-typing auto-repair...")
                    # CRITICAL: Wait for physical modifier keys to be fully RELEASED
                    # so that subsequent editor navigation (Ctrl+G) is never tainted by Shift!
                    while (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) or \
                          (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) or \
                          (user32.GetAsyncKeyState(VK_MULTIPLY) & 0x8000) or \
                          (user32.GetAsyncKeyState(0x38) & 0x8000) or \
                          (user32.GetAsyncKeyState(0xBB) & 0x8000) or \
                          (user32.GetAsyncKeyState(VK_F9) & 0x8000):
                        time.sleep(0.04)
                    time.sleep(0.15)
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
        # Immediate repair execution
        perform_human_repair()
    elif "--watch" in args or "-w" in args:
        # Daemon with auto-watch on file save
        run_daemon(watch_mode=True, silent=True)
    else:
        # Standard background daemon with Ctrl + Keypad * hotkey listener
        run_daemon(watch_mode=False, silent=True)
