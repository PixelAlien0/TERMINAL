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
# Mouse Movement & Wanderer Simulation
# -------------------------------------------------------------
class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def get_mouse_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_mouse_pos(x, y):
    user32.SetCursorPos(int(round(x)), int(round(y)))


def smooth_mouse_move(target_x, target_y, duration=0.25, steps=18):
    """Smoothly moves mouse cursor toward target using smoothstep ease."""
    x0, y0 = get_mouse_pos()
    if x0 == target_x and y0 == target_y:
        return
    for i in range(1, steps + 1):
        t = i / float(steps)
        ease = t * t * (3.0 - 2.0 * t)  # Smoothstep easing
        cx = x0 + (target_x - x0) * ease
        cy = y0 + (target_y - y0) * ease
        set_mouse_pos(cx, cy)
        time.sleep(duration / float(steps))


class MouseWanderer:
    """
    Subtle background mouse wanderer:
    Simulates realistic, unnoticeable mouse micro-movements (10-28px gentle drifts
    and occasional resting palm tremor) while typing is active.
    Never clicks or changes window focus.
    """
    def __init__(self):
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._wander_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.6)

    def _wander_loop(self):
        time.sleep(0.6)
        while self.running:
            # Random resting pause between moves (1.2 to 3.2 seconds)
            pause = random.uniform(1.2, 3.2)
            start_t = time.time()
            while self.running and (time.time() - start_t < pause):
                time.sleep(0.06)
                # Subtle 1-pixel sensor jitter every ~1 sec (hand resting on desk)
                if random.random() < 0.04:
                    cx, cy = get_mouse_pos()
                    set_mouse_pos(cx + random.choice([-1, 0, 1]), cy + random.choice([-1, 0, 1]))

            if not self.running:
                break

            # Gentle, short drift (8 to 26 pixels) in organic angle
            cx, cy = get_mouse_pos()
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(8, 26)
            tx = cx + dist * math.cos(angle)
            ty = cy + dist * math.sin(angle)

            # Safety bounds: stay within middle desktop area away from taskbar edges
            tx = max(80, min(1820, tx))
            ty = max(80, min(980, ty))

            move_dur = random.uniform(0.18, 0.35)
            move_steps = random.randint(12, 20)
            smooth_mouse_move(tx, ty, duration=move_dur, steps=move_steps)


# -------------------------------------------------------------
# Human-like Typing Simulator
# -------------------------------------------------------------
class HumanTyper:
    def __init__(self, wpm=36, typo_chance=0.025):
        self.wpm = wpm
        self.typo_chance = typo_chance
        self.chars_since_pause = 0

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
                # Realistic thought pause before starting to type the next line
                time.sleep(random.uniform(0.70, 1.40))
                self.chars_since_pause = 0

    def navigate_to_line(self, line_num):
        """
        Assumes pos_system.py is ALREADY open in the active editor.
        Jumps directly to line_num using Ctrl+G with realistic keystroke delays.
        """
        time.sleep(random.uniform(0.25, 0.45))
        # Go to line (Ctrl+G)
        send_combo(VK_CONTROL, ord("G"))
        time.sleep(random.uniform(0.30, 0.50))

        # Type line number deliberately
        for c in str(line_num):
            send_char(c)
            time.sleep(random.uniform(0.10, 0.18))
        time.sleep(random.uniform(0.25, 0.40))
        press_key(VK_RETURN)
        time.sleep(random.uniform(0.35, 0.60))

    def delete_broken_lines(self, count):
        """Removes `count` lines using VS Code line delete (Ctrl+Shift+K) with visible human pacing."""
        if count <= 0:
            return
        press_key(VK_HOME)
        time.sleep(0.10)
        press_key(VK_HOME)
        time.sleep(0.10)

        for _ in range(count):
            send_combo(VK_CONTROL, VK_SHIFT, ord("K"))
            time.sleep(random.uniform(0.25, 0.45))

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
        self.text = target_text
        self.index = 0
        self.total_len = len(target_text)
        self.finished = (self.total_len == 0)
        self.last_input_time = time.time()

    def emit_next_chunk(self):
        """Emits the next 1 to 3 characters of the target code into the editor."""
        if self.index >= self.total_len:
            self.finished = True
            return

        # At newline, emit newline alone so the line break looks deliberate
        if self.text[self.index] == "\n":
            chunk = "\n"
            self.index += 1
        elif self.text[self.index] in " \t":
            # Indent / space: emit space plus next char if not newline
            if self.index + 1 < self.total_len and self.text[self.index + 1] != "\n":
                chunk = self.text[self.index:self.index + 2]
                self.index += 2
            else:
                chunk = self.text[self.index]
                self.index += 1
        else:
            # 1 to 3 characters of code per keystroke
            chunk_len = random.choice([1, 2, 2, 3])
            # Don't cut past newline
            nl_pos = self.text.find("\n", self.index, self.index + chunk_len)
            if nl_pos != -1:
                chunk_len = max(1, nl_pos - self.index)
            chunk = self.text[self.index:self.index + chunk_len]
            self.index += len(chunk)

        for ch in chunk:
            send_char(ch)
            time.sleep(0.01)

        if self.index >= self.total_len:
            self.finished = True


def type_with_hacker_mode(target_text, auto_fallback_seconds=12.0):
    """
    HackerTyper engine:
    Intercepts any random physical key the person mashes on the keyboard,
    eats the physical key, and types the next chunk (1-3 chars) of the real fix!
    """
    if not target_text:
        return

    typer = HackerTyper(target_text)
    cb_holder = []

    def hook_proc(nCode, wParam, lParam):
        if nCode >= 0 and lParam:
            flags = lParam.contents.flags
            # If injected by SendInput, let it pass through to the editor!
            if flags & LLKHF_INJECTED:
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            vk = lParam.contents.vkCode

            # Escape key cancels HackerTyper immediately
            if vk == VK_ESCAPE:
                typer.finished = True
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            # Standalone modifier keys (Shift, Ctrl, Alt, CapsLock) pass through
            if vk in (VK_SHIFT, 0xA0, 0xA1, VK_CONTROL, 0xA2, 0xA3, VK_MENU, 0xA4, 0xA5, 0x14):
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            # Physical key down: swallow the key and emit the next real code chunk!
            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                typer.last_input_time = time.time()
                typer.emit_next_chunk()
                return 1

            # Physical key up: swallow key up so Windows doesn't echo it
            if wParam in (WM_KEYUP, WM_SYSKEYUP):
                return 1

        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    hook_func = HOOKPROC(hook_proc)
    cb_holder.append(hook_func)
    hhook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_func, None, 0)

    try:
        msg = wintypes.MSG()
        start_time = time.time()
        while not typer.finished:
            # Process Windows message queue so hook dispatches smoothly
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):  # PM_REMOVE = 1
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            # Auto-advance fallback if user stops typing for > auto_fallback_seconds
            now = time.time()
            if (now - typer.last_input_time) > auto_fallback_seconds and (now - start_time) > auto_fallback_seconds:
                typer.emit_next_chunk()
                time.sleep(random.uniform(0.12, 0.22))

            time.sleep(0.01)

    finally:
        if hhook:
            user32.UnhookWindowsHookEx(hhook)
        time.sleep(0.15)


# -------------------------------------------------------------
# Main Repair Workflow
# -------------------------------------------------------------
def perform_human_repair():
    """
    Executes the full automated repair sequence:
    1. Diagnoses error & diff in pos_system.py
    2. Brings editor to foreground & starts subtle mouse wanderer
    3. Jumps directly to exact line (assuming file already open)
    4. Deletes broken code
    5. Activates HackerTyper mode: mash any random keys on keyboard to type real fix!
    6. Saves file and halts cleanly
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

    print("\n[*] Bringing code editor to front...")
    print("    (Prepare to mash keys like a hacker!)")
    time.sleep(1.0)

    focus_ide_window()
    time.sleep(0.3)

    # Start subtle mouse movement in background while repair runs
    wanderer = MouseWanderer()
    wanderer.start()

    try:
        typer = HumanTyper(wpm=36)
        opcodes = diag["diff_blocks"]

        if len(opcodes) > 0 and len(opcodes) <= 5:
            # Surgical fix of each diff block
            for tag, i1, i2, j1, j2 in opcodes:
                start_line = i1 + 1
                delete_count = i2 - i1
                clean_lines = diag["golden_lines"][j1:j2]
                clean_snippet = "".join(clean_lines).rstrip("\r\n")

                print(f"[*] Navigating directly to Line {start_line}...")
                typer.navigate_to_line(start_line)

                if delete_count > 0:
                    print(f"[*] Deleting {delete_count} broken line(s)...")
                    typer.delete_broken_lines(delete_count)
                    time.sleep(random.uniform(0.35, 0.55))

                if clean_snippet:
                    print(f"[*] HackerTyper active! Mash any keys to type fix ({len(clean_snippet)} chars)...")
                    type_with_hacker_mode(clean_snippet)
                    time.sleep(0.3)

                typer.save_file()
                time.sleep(0.4)

        else:
            # Heavy corruption: Clean reset
            print("[*] Multiple alterations detected. Rebuilding cleanly...")
            typer.navigate_to_line(1)
            send_combo(VK_CONTROL, ord("A"))
            time.sleep(0.15)
            press_key(VK_BACK)
            time.sleep(0.2)

            clean_full_text = diag["golden_text"].rstrip("\r\n")
            print(f"[*] HackerTyper active! Mash any keys to type fix ({len(clean_full_text)} chars)...")
            type_with_hacker_mode(clean_full_text)
            time.sleep(0.3)
            typer.save_file()

        # Verification
        time.sleep(0.4)
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

    finally:
        wanderer.stop()


# -------------------------------------------------------------
# Background Daemon & Hotkey Listener
# -------------------------------------------------------------
def run_daemon(watch_mode=False, silent=False):
    """
    Runs in the background:
    - Listens for [Ctrl + Keypad *] hotkey to trigger repair on demand.
    - If watch_mode=True, also triggers when pos_system.py is saved with errors.
    """
    if not silent:
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
