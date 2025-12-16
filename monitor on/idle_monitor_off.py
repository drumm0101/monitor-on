# system_control_panel.py
# Monitör / Mouse / Klavye / Alarm / Ekran Görseli / Rocket League / Hızlı Başlat / Hızlı Kapat

import time
import ctypes
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import os
import subprocess

from PIL import ImageGrab
import pytesseract
import win32gui
import win32process

# ================== OCR AYAR ==================
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

ROCKET_LEAGUE_TITLE = "Rocket League"
GOAL_REGION = (650, 180, 1250, 380)

# ================== WIN API ==================
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ------------------ IDLE ------------------
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

def get_idle_seconds():
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    user32.GetLastInputInfo(ctypes.byref(lii))
    return (kernel32.GetTickCount() - lii.dwTime) / 1000.0

# ------------------ SYSTEM ------------------
def turn_off_monitor():
    user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)

def hide_cursor(hide=True):
    while user32.ShowCursor(not hide) != -1:
        pass

def block_keyboard(block=True):
    user32.BlockInput(block)

# ------------------ ACTIVE WINDOW ------------------
def get_active_window_title():
    hwnd = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(hwnd)

def is_rocket_league_active():
    return ROCKET_LEAGUE_TITLE.lower() in get_active_window_title().lower()

# ================== APP ==================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("System Control Panel")
        self.root.geometry("600x460")
        self.root.resizable(False, False)

        self.monitor_on = False
        self.mouse_on = False
        self.keyboard_on = False
        self.alarm_on = False
        self.screen_on = False
        self.rocket_on = False

        self.monitor_minutes = tk.IntVar(value=15)
        self.mouse_minutes = tk.IntVar(value=5)
        self.keyboard_minutes = tk.IntVar(value=5)
        self.alarm_minutes = tk.IntVar(value=10)
        self.screen_interval = tk.IntVar(value=10)

        self.launch_path = tk.StringVar()
        self.launch_delay = tk.IntVar(value=5)

        self.monitor_status = tk.StringVar(value="Kapalı")
        self.mouse_status = tk.StringVar(value="Kapalı")
        self.keyboard_status = tk.StringVar(value="Kapalı")
        self.alarm_status = tk.StringVar(value="Kapalı")
        self.screen_status = tk.StringVar(value="Kapalı")
        self.rocket_status = tk.StringVar(value="Kapalı")

        self.capture_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(self.capture_dir, exist_ok=True)

        self.build_ui()

    # ------------------ UI ------------------
    def build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both")

        def simple_tab(title, label, var, toggle, status):
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=title)
            ttk.Label(tab, text=label).pack(pady=6)
            ttk.Spinbox(tab, from_=1, to=300, textvariable=var).pack()
            ttk.Button(tab, text="Aç / Kapat", command=toggle).pack(pady=8)
            ttk.Label(tab, textvariable=status).pack()

        simple_tab("🖥 Monitör", "Idle Süresi (dk)", self.monitor_minutes, self.toggle_monitor, self.monitor_status)
        simple_tab("🖱 Mouse", "Idle Süresi (dk)", self.mouse_minutes, self.toggle_mouse, self.mouse_status)
        simple_tab("⌨ Klavye", "Idle Süresi (dk)", self.keyboard_minutes, self.toggle_keyboard, self.keyboard_status)
        simple_tab("⏰ Alarm", "Alarm Süresi (dk)", self.alarm_minutes, self.toggle_alarm, self.alarm_status)

        # SCREENSHOT
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🖼 Ekran Görseli")
        ttk.Label(tab, text="Çekim Aralığı (sn)").pack(pady=6)
        ttk.Spinbox(tab, from_=5, to=600, textvariable=self.screen_interval).pack()
        ttk.Button(tab, text="Başlat / Durdur", command=self.toggle_screen).pack(pady=8)
        ttk.Label(tab, textvariable=self.screen_status).pack()

        # ROCKET LEAGUE
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🚀 Rocket League")
        ttk.Button(tab, text="Analizi Aç / Kapat", command=self.toggle_rocket).pack(pady=12)
        ttk.Label(tab, textvariable=self.rocket_status).pack()

        # HIZLI BAŞLAT
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="⚡ Hızlı Başlat")
        ttk.Label(tab, text="Uygulama (.exe) Yolu").pack(pady=4)
        ttk.Entry(tab, textvariable=self.launch_path, width=55).pack()
        ttk.Label(tab, text="Gecikme (dk)").pack(pady=4)
        ttk.Spinbox(tab, from_=0, to=180, textvariable=self.launch_delay).pack()
        ttk.Button(tab, text="Zamanla Başlat", command=self.start_delayed_launch).pack(pady=10)

        # HIZLI KAPAT
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="🛑 Hızlı Kapat")
        self.process_list = tk.Listbox(tab, width=65, height=14)
        self.process_list.pack(pady=6)
        ttk.Button(tab, text="Yenile", command=self.refresh_process_list).pack()
        ttk.Button(tab, text="Seçileni Kapat", command=self.kill_selected_process).pack(pady=6)

    # ------------------ TOGGLES ------------------
    def toggle_monitor(self):
        self.monitor_on = not self.monitor_on
        self.monitor_status.set("Aktif" if self.monitor_on else "Kapalı")
        threading.Thread(target=self.monitor_worker, daemon=True).start()

    def toggle_mouse(self):
        self.mouse_on = not self.mouse_on
        self.mouse_status.set("Aktif" if self.mouse_on else "Kapalı")
        threading.Thread(target=self.mouse_worker, daemon=True).start()

    def toggle_keyboard(self):
        self.keyboard_on = not self.keyboard_on
        self.keyboard_status.set("Aktif" if self.keyboard_on else "Kapalı")
        threading.Thread(target=self.keyboard_worker, daemon=True).start()

    def toggle_alarm(self):
        self.alarm_on = not self.alarm_on
        self.alarm_status.set("Aktif" if self.alarm_on else "Kapalı")
        threading.Thread(target=self.alarm_worker, daemon=True).start()

    def toggle_screen(self):
        self.screen_on = not self.screen_on
        self.screen_status.set("Aktif" if self.screen_on else "Kapalı")
        threading.Thread(target=self.screen_worker, daemon=True).start()

    def toggle_rocket(self):
        self.rocket_on = not self.rocket_on
        self.rocket_status.set("Aktif" if self.rocket_on else "Kapalı")
        threading.Thread(target=self.rocket_league_worker, daemon=True).start()

    # ------------------ WORKERS ------------------
    def monitor_worker(self):
        while self.monitor_on:
            if get_idle_seconds() >= self.monitor_minutes.get() * 60:
                turn_off_monitor()
            time.sleep(2)

    def mouse_worker(self):
        while self.mouse_on:
            hide_cursor(get_idle_seconds() >= self.mouse_minutes.get() * 60)
            time.sleep(2)

    def keyboard_worker(self):
        while self.keyboard_on:
            block_keyboard(get_idle_seconds() >= self.keyboard_minutes.get() * 60)
            time.sleep(2)

    def alarm_worker(self):
        time.sleep(self.alarm_minutes.get() * 60)
        self.show_fullscreen_alarm()

    def screen_worker(self):
        while self.screen_on:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            ImageGrab.grab().save(os.path.join(self.capture_dir, f"{ts}.png"))
            time.sleep(self.screen_interval.get())

    def rocket_league_worker(self):
        notified = False
        last_goal = 0
        while self.rocket_on:
            if is_rocket_league_active():
                if not notified:
                    self.show_popup("🎮 Rocket League Analizi Aktif")
                    notified = True

                img = ImageGrab.grab(bbox=GOAL_REGION).convert("L")
                img = img.point(lambda x: 0 if x < 160 else 255)
                text = pytesseract.image_to_string(img, config="--psm 6").upper()

                if "GOAL" in text and time.time() - last_goal > 7:
                    last_goal = time.time()
                    self.show_popup("⚽ GOL! Klip Alındı")
                    self.trigger_clip_hotkey()
            else:
                notified = False
            time.sleep(0.5)

    # ------------------ HIZLI BAŞLAT ------------------
    def start_delayed_launch(self):
        path = self.launch_path.get()
        delay = self.launch_delay.get() * 60
        if os.path.exists(path):
            threading.Thread(target=self.delayed_launch, args=(path, delay), daemon=True).start()
            self.show_popup("⏳ Uygulama Zamanlandı")

    def delayed_launch(self, path, delay):
        time.sleep(delay)
        os.startfile(path)
        self.show_popup("🚀 Uygulama Başlatıldı")

    # ------------------ HIZLI KAPAT ------------------
    def refresh_process_list(self):
        self.process_list.delete(0, tk.END)
        def enum(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    self.process_list.insert(tk.END, f"{pid} | {title}")
        win32gui.EnumWindows(enum, None)

    def kill_selected_process(self):
        sel = self.process_list.curselection()
        if not sel:
            return
        pid = int(self.process_list.get(sel[0]).split("|")[0])
        try:
            os.kill(pid, 9)
            self.show_popup("🛑 Uygulama Kapatıldı")
            self.refresh_process_list()
        except:
            self.show_popup("❌ Kapatılamadı")

    # ------------------ CLIP ------------------
    def trigger_clip_hotkey(self):
        for k in [(0x11,0),(0x12,0),(0x47,0),(0x47,2),(0x12,2),(0x11,2)]:
            user32.keybd_event(k[0],0,k[1],0)

    # ------------------ POPUP ------------------
    def show_popup(self, text):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", False)
        win.configure(bg="black")
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"+{sw//2 - 200}+{sh - 120}")
        tk.Label(win, text=text, fg="white", bg="black",
                 font=("Segoe UI", 16, "bold")).pack(padx=20, pady=8)
        win.after(1800, win.destroy)

    # ------------------ ALARM ------------------
    def show_fullscreen_alarm(self):
        alarm = tk.Toplevel(self.root)
        alarm.attributes("-fullscreen", True)
        alarm.configure(bg="black")
        alarm.bind("<Control-r>", lambda e: alarm.destroy())
        tk.Label(alarm, text="⏰ SÜRE DOLDU!",
                 fg="white", bg="black",
                 font=("Segoe UI", 36, "bold")).pack(expand=True)

# ================== RUN ==================
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
