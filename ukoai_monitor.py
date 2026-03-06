"""
UKOAI Exam Keystroke Monitor
Monitors keystrokes during UKOAI exams to ensure exam integrity.
Cross-platform: Windows, macOS, Linux.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import datetime
import os
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path

IS_MAC = platform.system() == "Darwin"

try:
    from pynput import keyboard
except ImportError:
    keyboard = None


TIMESTAMP_INTERVAL_SECONDS = 30


class KeystrokeMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("UKOAI Exam Monitor")
        self.root.resizable(False, False)

        self.recording = False
        self.paused = False
        self.listener = None
        self.log_entries = []
        self.keys_since_timestamp = 0
        self.last_timestamp = None
        self.pause_alert_job = None
        self.session_start = None

        self._build_ui()
        self._update_status("Ready")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.root.configure(bg="#f0f0f0")

        # Title
        title = tk.Label(
            self.root, text="UKOAI Exam Monitor",
            font=("Helvetica", 16, "bold"), bg="#f0f0f0", fg="#333"
        )
        title.pack(pady=(15, 5))

        subtitle = tk.Label(
            self.root, text="Keystroke monitoring for exam integrity",
            font=("Helvetica", 9), bg="#f0f0f0", fg="#888"
        )
        subtitle.pack(pady=(0, 10))

        # Status indicator
        status_frame = tk.Frame(self.root, bg="#f0f0f0")
        status_frame.pack(pady=5)

        self.status_dot = tk.Canvas(
            status_frame, width=14, height=14,
            bg="#f0f0f0", highlightthickness=0
        )
        self.status_dot.pack(side=tk.LEFT, padx=(0, 6))
        self.dot_id = self.status_dot.create_oval(2, 2, 12, 12, fill="gray", outline="")

        self.status_label = tk.Label(
            status_frame, text="Ready", font=("Helvetica", 11),
            bg="#f0f0f0", fg="#333"
        )
        self.status_label.pack(side=tk.LEFT)

        # Key count
        self.count_label = tk.Label(
            self.root, text="Keystrokes: 0", font=("Helvetica", 10),
            bg="#f0f0f0", fg="#666"
        )
        self.count_label.pack(pady=(2, 10))

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#f0f0f0")
        btn_frame.pack(pady=(0, 15))

        btn_style = {"font": ("Helvetica", 10), "width": 10}
        if not IS_MAC:
            btn_style["cursor"] = "hand2"

        if IS_MAC:
            # macOS tkinter ignores fg/bg on buttons, use default styling
            self.record_btn = tk.Button(
                btn_frame, text="Record",
                command=self._start_recording, **btn_style
            )
            self.pause_btn = tk.Button(
                btn_frame, text="Pause",
                command=self._toggle_pause, state=tk.DISABLED, **btn_style
            )
            self.stop_btn = tk.Button(
                btn_frame, text="Stop",
                command=self._stop_recording, state=tk.DISABLED, **btn_style
            )
        else:
            self.record_btn = tk.Button(
                btn_frame, text="Record", bg="#4CAF50", fg="white",
                activebackground="#45a049", command=self._start_recording,
                **btn_style
            )
            self.pause_btn = tk.Button(
                btn_frame, text="Pause", bg="#FF9800", fg="white",
                activebackground="#e68a00", command=self._toggle_pause,
                state=tk.DISABLED, **btn_style
            )
            self.stop_btn = tk.Button(
                btn_frame, text="Stop", bg="#f44336", fg="white",
                activebackground="#d32f2f", command=self._stop_recording,
                state=tk.DISABLED, **btn_style
            )
        self.record_btn.grid(row=0, column=0, padx=4, pady=3)
        self.pause_btn.grid(row=0, column=1, padx=4, pady=3)
        self.stop_btn.grid(row=0, column=2, padx=4, pady=3)

        # Set minimum window size
        self.root.update_idletasks()
        self.root.minsize(380, 200)

    def _update_status(self, text, color=None):
        colors = {
            "Ready": "gray",
            "Recording": "#4CAF50",
            "Paused": "#FF9800",
            "Stopped": "#f44336",
        }
        c = color or colors.get(text, "gray")
        self.status_label.config(text=text)
        self.status_dot.itemconfig(self.dot_id, fill=c)

    def _update_count(self):
        total = sum(1 for e in self.log_entries if not e.startswith("["))
        self.count_label.config(text=f"Keystrokes: {total}")

    # ── Recording ────────────────────────────────────────────

    def _start_recording(self):
        if keyboard is None:
            messagebox.showerror(
                "Missing dependency",
                "The 'pynput' library is required.\nInstall it with: pip install pynput"
            )
            return

        self.recording = True
        self.paused = False
        self.log_entries = []
        self.keys_since_timestamp = 0
        self.session_start = datetime.datetime.now()
        self.last_timestamp = self.session_start

        self.log_entries.append(
            f"[Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}]"
        )

        self.record_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL, text="Pause")
        self.stop_btn.config(state=tk.NORMAL)
        self._update_status("Recording")
        self._update_count()

        try:
            self.listener = keyboard.Listener(on_press=self._on_key_press)
            self.listener.start()
        except Exception as e:
            self._recording_failed(str(e))
            return

        # On macOS, check if the listener is working
        if IS_MAC:
            # Check if listener thread died (permissions denied)
            self.root.after(1000, self._check_listener_alive)
            # Also check if keystrokes are actually being captured
            self.root.after(5000, self._check_keystrokes_arriving)

    def _show_mac_permission_help(self):
        """Show clear instructions and open the correct System Settings page."""
        self.recording = False
        self.record_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self._update_status("Ready")

        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

        messagebox.showwarning(
            "Accessibility Permission Required",
            "This app needs Accessibility permission to capture keystrokes.\n\n"
            "How to fix:\n\n"
            "1. Click OK — System Settings will open to the right page\n"
            "2. Click the + button at the bottom of the list\n"
            "3. Find and select UKOAI_Exam_Monitor.app\n"
            "4. Make sure the toggle next to it is ON\n"
            "5. QUIT and REOPEN this app (permissions require a restart)\n"
            "6. Click Record again",
            parent=self.root,
        )
        try:
            subprocess.Popen([
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
            ])
        except Exception:
            messagebox.showinfo(
                "Manual Navigation",
                "Could not open System Settings automatically.\n\n"
                "Please open it manually:\n"
                "Apple menu > System Settings > Privacy & Security > Accessibility",
                parent=self.root,
            )

    def _recording_failed(self, error_msg=""):
        if IS_MAC:
            self._show_mac_permission_help()
        else:
            self.recording = False
            self.record_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self._update_status("Ready")
            messagebox.showerror(
                "Permission Error",
                f"Unable to start keystroke capture.\n{error_msg}",
                parent=self.root,
            )

    def _check_listener_alive(self):
        if self.recording and self.listener and not self.listener.is_alive():
            self._show_mac_permission_help()

    def _check_keystrokes_arriving(self):
        """If recording for 5 seconds with 0 keystrokes, permissions are likely missing."""
        if not self.recording or self.paused or not IS_MAC:
            return
        keystroke_count = sum(1 for e in self.log_entries if not e.startswith("["))
        if keystroke_count == 0:
            result = messagebox.askyesno(
                "No Keystrokes Detected",
                "Recording is active but no keystrokes have been captured.\n\n"
                "This usually means Accessibility permissions haven't been granted.\n\n"
                "Would you like help setting up permissions?",
                parent=self.root,
            )
            if result:
                self._show_mac_permission_help()

    def _on_key_press(self, key):
        if not self.recording or self.paused:
            return

        now = datetime.datetime.now()

        # Insert periodic timestamp
        elapsed = (now - self.last_timestamp).total_seconds()
        if elapsed >= TIMESTAMP_INTERVAL_SECONDS:
            self.log_entries.append(
                f"\n[{now.strftime('%H:%M:%S')}]"
            )
            self.last_timestamp = now

        # Format the key
        try:
            char = key.char
            if char is not None:
                self.log_entries.append(char)
            else:
                self.log_entries.append(f"[{key}]")
        except AttributeError:
            name = str(key).replace("Key.", "").upper()
            special_map = {
                "SPACE": " ",
                "ENTER": "\n",
                "TAB": "\t",
            }
            self.log_entries.append(special_map.get(name, f"[{name}]"))

        self.keys_since_timestamp += 1

        # Update UI from main thread
        self.root.after(0, self._update_count)

    # ── Pause / Resume ───────────────────────────────────────

    def _toggle_pause(self):
        if not self.recording:
            return

        if not self.paused:
            self._do_pause()
        else:
            self._do_resume()

    def _do_pause(self):
        self.paused = True
        now = datetime.datetime.now()
        self.log_entries.append(f"\n[Paused at {now.strftime('%H:%M:%S')}]")
        self.pause_btn.config(text="Resume")
        self._update_status("Paused")
        self._schedule_pause_alert()

    def _do_resume(self):
        self.paused = False
        now = datetime.datetime.now()
        self.log_entries.append(f"\n[Resumed at {now.strftime('%H:%M:%S')}]")
        self.last_timestamp = now
        self.pause_btn.config(text="Pause")
        self._update_status("Recording")
        self._cancel_pause_alert()

    def _schedule_pause_alert(self):
        self._cancel_pause_alert()
        self.pause_alert_job = self.root.after(60000, self._pause_alert_tick)

    def _cancel_pause_alert(self):
        if self.pause_alert_job is not None:
            self.root.after_cancel(self.pause_alert_job)
            self.pause_alert_job = None

    def _pause_alert_tick(self):
        if self.paused and self.recording:
            messagebox.showinfo(
                "Monitor Paused",
                "The keystroke monitor is still paused.\nResume when ready.",
                parent=self.root,
            )
            self._schedule_pause_alert()

    # ── Stop ─────────────────────────────────────────────────

    def _stop_recording(self):
        if not self.recording:
            return

        result = messagebox.askyesno(
            "Stop Recording",
            "Are you sure you want to stop?\n\n"
            "If the exam session isn't over, consider\n"
            "pausing instead.\n\n"
            "Stop recording?",
            parent=self.root,
        )
        if not result:
            return

        self._cancel_pause_alert()
        self.recording = False
        self.paused = False

        if self.listener:
            self.listener.stop()
            self.listener = None

        now = datetime.datetime.now()
        self.log_entries.append(
            f"\n[Session ended: {now.strftime('%Y-%m-%d %H:%M:%S')}]"
        )

        self._update_status("Stopped")
        self.record_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="Pause")
        self.stop_btn.config(state=tk.DISABLED)

        self._offer_save()

    # ── Save / Export ────────────────────────────────────────

    def _build_log_text(self):
        header = (
            "UKOAI Exam Keystroke Log\n"
            "========================\n"
            f"Date: {self.session_start.strftime('%Y-%m-%d')}\n"
            f"Start: {self.session_start.strftime('%H:%M:%S')}\n"
            f"End:   {datetime.datetime.now().strftime('%H:%M:%S')}\n"
            f"Platform: {platform.system()} {platform.release()}\n"
            "========================\n\n"
        )
        return header + "".join(self.log_entries) + "\n"

    def _offer_save(self):
        log_text = self._build_log_text()
        timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
        default_name = f"ukoai_keylog_{timestamp}.txt"

        save = messagebox.askyesno(
            "Save Log",
            f"Recording complete.\n\n"
            f"Save the keystroke log?\n\n"
            f"If you choose No, the file will be\n"
            f"placed in your system trash/recycle bin\n"
            f"so it can be recovered if needed.",
            parent=self.root,
        )

        if save:
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=default_name,
                title="Save Keystroke Log",
                parent=self.root,
            )
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(log_text)
                messagebox.showinfo("Saved", f"Log saved to:\n{path}", parent=self.root)
            else:
                # User cancelled the save dialog — put in trash
                self._send_to_trash(log_text, default_name)
        else:
            self._send_to_trash(log_text, default_name)

    def _send_to_trash(self, log_text, filename):
        """Write the log to a temp file and move it to trash/recycle bin."""
        tmp_path = os.path.join(tempfile.gettempdir(), filename)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(log_text)

        moved = False
        try:
            # Try send2trash if available
            from send2trash import send2trash
            send2trash(tmp_path)
            moved = True
        except ImportError:
            pass

        if not moved:
            # Fallback: platform-specific trash
            system = platform.system()
            if system == "Linux":
                trash_dir = Path.home() / ".local" / "share" / "Trash" / "files"
                trash_dir.mkdir(parents=True, exist_ok=True)
                dest = trash_dir / filename
                shutil.move(tmp_path, str(dest))
                moved = True
            elif system == "Darwin":
                trash_dir = Path.home() / ".Trash"
                dest = trash_dir / filename
                shutil.move(tmp_path, str(dest))
                moved = True
            elif system == "Windows":
                # On Windows without send2trash, just keep in temp
                pass

        if moved:
            messagebox.showinfo(
                "Sent to Trash",
                f"Log file '{filename}' has been moved to\n"
                f"your trash/recycle bin for recovery.",
                parent=self.root,
            )
        else:
            messagebox.showinfo(
                "Temporary File",
                f"Log saved to temporary folder:\n{tmp_path}\n\n"
                f"You can recover it from there.",
                parent=self.root,
            )

    # ── Window close ─────────────────────────────────────────

    def _on_close(self):
        if self.recording:
            messagebox.showwarning(
                "Recording Active",
                "Please stop the recording before closing.",
                parent=self.root,
            )
            return
        self.root.destroy()


def main():
    root = tk.Tk()

    # Center window on screen
    w, h = 380, 220
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    KeystrokeMonitor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
