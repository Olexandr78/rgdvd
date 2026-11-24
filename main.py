"""RGDVD desktop launcher. Panda3D is imported only by rgdvd_game.py after Play."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import customtkinter as ctk

from rgdvd.config import DEFAULT_SERVER_URL, load_config, save_config
from rgdvd.cars import CAR_SPECS
from rgdvd.events import EVENTS
from rgdvd.profile import CareerProfile

ROOT = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent)
GAME_FILE = ROOT / "rgdvd_game.py"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class RGDVDLauncher(ctk.CTk):
    BG = "#0b1018"
    PANEL = "#131d29"
    PANEL2 = "#1a2735"
    ACCENT = "#ed4b35"
    MUTED = "#9aabba"
    TEXT = "#f2f5f8"

    def __init__(self):
        super().__init__()
        self.title("RGDVD | Street Racing")
        self.geometry("1180x760")
        self.minsize(1000, 680)
        self.configure(fg_color=self.BG)
        self.config_data = load_config()
        self.profile = CareerProfile()
        self.game_process = None
        self.current_page = "home"
        self.nav_buttons = {}
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self._build_shell()
        self.show_page("home")
        self.after(350, self._poll_game)

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=225, corner_radius=0, fg_color="#0e1722")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        ctk.CTkLabel(self.sidebar, text="RGDVD", font=ctk.CTkFont(size=32, weight="bold"),
                     text_color=self.TEXT).pack(anchor="w", padx=24, pady=(28, 0))
        ctk.CTkLabel(self.sidebar, text="STREET RACING", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=self.ACCENT).pack(anchor="w", padx=26, pady=(0, 28))
        nav = [
            ("home", "⌂   ГЛАВНАЯ"),
            ("garage", "▣   ГАРАЖ"),
            ("events", "⚑   ЗАЕЗДЫ"),
            ("multiplayer", "◎   СЕТЕВАЯ ИГРА"),
            ("controls", "⌘   УПРАВЛЕНИЕ"),
            ("settings", "⚙   НАСТРОЙКИ"),
        ]
        for key, label in nav:
            button = ctk.CTkButton(
                self.sidebar, text=label, anchor="w", height=46, corner_radius=10,
                fg_color="transparent", hover_color=self.PANEL2,
                text_color=self.TEXT, font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda page=key: self.show_page(page))
            button.pack(fill="x", padx=14, pady=4)
            self.nav_buttons[key] = button
        ctk.CTkFrame(self.sidebar, height=2, fg_color="#263646").pack(fill="x", padx=18, pady=22)
        self.sidebar_status = ctk.CTkLabel(
            self.sidebar, text="●  ГОТОВО К ЗАПУСКУ", text_color="#75c995",
            font=ctk.CTkFont(size=11, weight="bold"))
        self.sidebar_status.pack(side="bottom", anchor="w", padx=22, pady=24)
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=self.BG)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

    def show_page(self, page):
        self.current_page = page
        for key, button in self.nav_buttons.items():
            button.configure(fg_color=self.PANEL2 if key == page else "transparent")
        for child in self.content.winfo_children():
            child.destroy()
        titles = {
            "home": ("ГЛАВНОЕ МЕНЮ", "Выбери режим. 3D-движок запускается только после старта игры."),
            "garage": ("ГАРАЖ", "Выбери автомобиль для следующей поездки."),
            "events": ("ГОРОДСКИЕ ЗАЕЗДЫ", "53 маршрута по шести районам города."),
            "multiplayer": ("СЕТЕВАЯ ИГРА", "Играй по локальной сети или подключайся к онлайн-комнате."),
            "controls": ("УПРАВЛЕНИЕ", "Клавиатура и настройки рулевого контроллера."),
            "settings": ("НАСТРОЙКИ", "Графика и параметры запуска."),
        }
        title, subtitle = titles[page]
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=34, pady=(28, 16))
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=27, weight="bold"),
                     text_color=self.TEXT).pack(anchor="w")
        ctk.CTkLabel(header, text=subtitle, font=ctk.CTkFont(size=13),
                     text_color=self.MUTED).pack(anchor="w", pady=(5, 0))
        self.page_body = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.page_body.grid(row=1, column=0, sticky="nsew", padx=26, pady=(0, 24))
        if page == "home":
            self._home()
        elif page == "garage":
            self._garage()
        elif page == "events":
            self._events()
        elif page == "multiplayer":
            self._multiplayer()
        elif page == "controls":
            self._controls()
        else:
            self._settings()

    def _card(self, parent, title, description, button_text, command, accent=False):
        card = ctk.CTkFrame(parent, fg_color=self.PANEL, corner_radius=16)
        card.pack(fill="x", padx=5, pady=8)
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=22, pady=19)
        ctk.CTkLabel(left, text=title, font=ctk.CTkFont(size=19, weight="bold"),
                     text_color=self.TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text=description, font=ctk.CTkFont(size=12),
                     text_color=self.MUTED, wraplength=570, justify="left").pack(anchor="w", pady=(5, 0))
        ctk.CTkButton(card, text=button_text, command=command, width=165, height=42,
                      fg_color=self.ACCENT if accent else self.PANEL2,
                      hover_color="#c83b2a" if accent else "#26394b",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(side="right", padx=22, pady=22)
        return card

    def _home(self):
        hero = ctk.CTkFrame(self.page_body, fg_color="#172638", corner_radius=18)
        hero.pack(fill="x", padx=5, pady=(2, 14))
        ctk.CTkLabel(hero, text="ТВОЙ ГОРОД. ТВОИ ПРАВИЛА.", text_color="#ff795f",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=26, pady=(22, 2))
        ctk.CTkLabel(hero, text="ВЫХОДИ НА УЛИЦЫ", text_color=self.TEXT,
                     font=ctk.CTkFont(size=31, weight="bold")).pack(anchor="w", padx=26)
        ctk.CTkLabel(hero, text="Открытый город • Свободная езда • 53 события • LAN и Online",
                     text_color="#b6c5d3", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=27, pady=(3, 20))
        self._card(self.page_body, "СВОБОДНАЯ ЕЗДА",
                   "Просто садись за руль и исследуй город без таймера и обязательных гонок.",
                   "ИГРАТЬ", lambda: self.launch_game("free"), True)
        self._card(self.page_body, "СОБЫТИЯ И ГОНКИ",
                   "Выбери спринт или кольцевой маршрут на карте города.",
                   "ВЫБРАТЬ ЗАЕЗД", lambda: self.show_page("events"))
        self._card(self.page_body, "МУЛЬТИПЛЕЕР",
                   "Создай LAN-комнату, найди игру в локальной сети или подключись к серверу.",
                   "ОТКРЫТЬ", lambda: self.show_page("multiplayer"))
        stats = ctk.CTkFrame(self.page_body, fg_color=self.PANEL, corner_radius=14)
        stats.pack(fill="x", padx=5, pady=8)
        races = self.profile.data.get("races", 0)
        wins = self.profile.data.get("wins", 0)
        ctk.CTkLabel(stats, text=f"ПРОФИЛЬ     {races} ЗАЕЗДОВ     {wins} ПОБЕД     {self.profile.credits:,} КРЕДИТОВ",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=self.MUTED).pack(padx=20, pady=17)

    def _garage(self):
        selected = self.config_data.get("car_id", "street_gt")
        for car_id, spec in CAR_SPECS.items():
            unlocked = car_id in self.profile.data.get("unlocked_cars", ["street_gt"])
            is_selected = car_id == selected
            card = ctk.CTkFrame(self.page_body, fg_color=self.PANEL2 if is_selected else self.PANEL,
                                corner_radius=14)
            card.pack(fill="x", padx=5, pady=7)
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", padx=20, pady=15, fill="x", expand=True)
            ctk.CTkLabel(info, text=spec["name"], text_color=self.TEXT,
                         font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
            state = "ДОСТУПЕН" if unlocked else f"ОТКРОЕТСЯ ПОСЛЕ {spec['required_wins']} ПОБЕД"
            ctk.CTkLabel(info, text=state, text_color="#78c99a" if unlocked else self.MUTED,
                         font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(4, 0))
            if unlocked:
                ctk.CTkButton(card, text="ВЫБРАТЬ" if not is_selected else "ВЫБРАНО",
                              state="normal" if not is_selected else "disabled",
                              command=lambda cid=car_id: self.select_car(cid),
                              fg_color=self.ACCENT if not is_selected else "#314454",
                              width=125).pack(side="right", padx=20)
        self._note(self.page_body, "Выбранная машина сохраняется и появится в следующем запуске игры.")

    def select_car(self, car_id):
        self.config_data["car_id"] = car_id
        save_config(self.config_data)
        self.show_page("garage")

    def _events(self):
        search = ctk.CTkEntry(self.page_body, placeholder_text="Поиск по району или названию...",
                              height=40)
        search.pack(fill="x", padx=5, pady=(0, 10))
        listing = ctk.CTkFrame(self.page_body, fg_color="transparent")
        listing.pack(fill="both", expand=True)
        def populate(*_):
            for child in listing.winfo_children():
                child.destroy()
            term = search.get().strip().lower()
            filtered = [event for event in EVENTS if term in event.name.lower() or term in event.event_id.lower()]
            for event in filtered:
                self._card(listing, event.name,
                           f"{event.event_type}  •  {event.laps} круг(а)  •  ID {event.event_id}",
                           "СТАРТ", lambda eid=event.event_id: self.launch_game("event", eid))
        search.bind("<KeyRelease>", populate)
        populate()

    def _multiplayer(self):
        self.nickname = ctk.CTkEntry(self.page_body, height=40)
        self.nickname.insert(0, self.config_data.get("nickname", "Driver"))
        self.nickname.pack(fill="x", padx=5, pady=6)
        self.room = ctk.CTkEntry(self.page_body, height=40)
        self.room.insert(0, self.config_data.get("room", "OPEN-LOBBY"))
        self.room.pack(fill="x", padx=5, pady=6)
        self.server = ctk.CTkEntry(self.page_body, height=40)
        self.server.insert(0, self.config_data.get("server_url", DEFAULT_SERVER_URL))
        self.server.pack(fill="x", padx=5, pady=6)
        self._card(self.page_body, "СОЗДАТЬ ЛОКАЛЬНУЮ ИГРУ",
                   "Открыть комнату для игроков в той же Wi-Fi / Ethernet сети.",
                   "СОЗДАТЬ", lambda: self._launch_network("host-lan"), True)
        self._card(self.page_body, "НАЙТИ ИГРУ В СЕТИ",
                   "Найти доступный LAN-сервер в локальной сети.",
                   "ИСКАТЬ", lambda: self._launch_network("join-lan"))
        self._card(self.page_body, "ОНЛАЙН-КОМНАТА",
                   "Подключиться к комнате через сервер RGDVD.",
                   "ПОДКЛЮЧИТЬСЯ", lambda: self._launch_network("online"))

    def _launch_network(self, mode):
        self.config_data["nickname"] = self.nickname.get().strip() or "Driver"
        self.config_data["room"] = self.room.get().strip() or "OPEN-LOBBY"
        self.config_data["server_url"] = self.server.get().strip() or DEFAULT_SERVER_URL
        save_config(self.config_data)
        self.launch_game(mode)

    def _controls(self):
        rows = [
            ("W / ↑", "Газ"),
            ("S / ↓", "Тормоз и задний ход"),
            ("A / ←   D / →", "Поворот"),
            ("ПРОБЕЛ", "Ручной тормоз"),
            ("Q / E", "Передача вниз / вверх (механика)"),
            ("R", "Перезапуск заезда"),
            ("M", "Карта города во время езды"),
            ("ESC", "Пауза"),
        ]
        for key, action in rows:
            row = ctk.CTkFrame(self.page_body, fg_color=self.PANEL, corner_radius=10)
            row.pack(fill="x", padx=5, pady=4)
            ctk.CTkLabel(row, text=key, width=190, anchor="w", text_color="#ff8b72",
                         font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=18, pady=13)
            ctk.CTkLabel(row, text=action, text_color=self.TEXT,
                         font=ctk.CTkFont(size=13)).pack(side="left", padx=10)
        self._note(self.page_body, "Настройка рулевого контроллера находится ниже. F6 меняет профиль руля в игре.")
        self.wheel_var = ctk.StringVar(value=self.config_data.get("controller_preset", "auto"))
        ctk.CTkOptionMenu(self.page_body, values=["auto", "esperanza_nitro_egw102", "generic"],
                          variable=self.wheel_var).pack(anchor="w", padx=8, pady=8)
        ctk.CTkButton(self.page_body, text="СОХРАНИТЬ ПРОФИЛЬ РУЛЯ",
                      command=self.save_wheel).pack(anchor="w", padx=8, pady=6)

    def save_wheel(self):
        self.config_data["controller_preset"] = self.wheel_var.get()
        save_config(self.config_data)
        self._note(self.page_body, "Профиль руля сохранён.")

    def _settings(self):
        self.quality_var = ctk.StringVar(value=self.config_data.get("quality", "medium"))
        self._setting_row("КАЧЕСТВО ГРАФИКИ", self.quality_var, ["low", "medium", "high"])
        self.transmission_var = ctk.StringVar(value=self.config_data.get("transmission", "automatic"))
        self._setting_row("КОРОБКА ПЕРЕДАЧ", self.transmission_var, ["automatic", "manual"])
        self._setting_row("РАЗМЕР ОКНА", None, ["1366 × 768", "1600 × 900", "1920 × 1080"])
        ctk.CTkButton(self.page_body, text="СОХРАНИТЬ НАСТРОЙКИ", height=42,
                      fg_color=self.ACCENT, command=self.save_settings).pack(anchor="w", padx=8, pady=18)

    def _setting_row(self, title, variable, values):
        row = ctk.CTkFrame(self.page_body, fg_color=self.PANEL, corner_radius=12)
        row.pack(fill="x", padx=5, pady=7)
        ctk.CTkLabel(row, text=title, text_color=self.TEXT,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=18, pady=17)
        if variable is not None:
            menu = ctk.CTkOptionMenu(row, values=values, variable=variable, width=190)
        else:
            current = f"{self.config_data.get('width', 1366)} × {self.config_data.get('height', 768)}"
            variable = ctk.StringVar(value=current if current in values else values[0])
            menu = ctk.CTkOptionMenu(row, values=values, variable=variable, width=190)
            self.resolution_var = variable
        menu.pack(side="right", padx=18)

    def save_settings(self):
        self.config_data["quality"] = self.quality_var.get()
        self.config_data["transmission"] = self.transmission_var.get()
        try:
            width, height = self.resolution_var.get().split(" × ")
            self.config_data["width"] = int(width)
            self.config_data["height"] = int(height)
        except (ValueError, AttributeError):
            pass
        save_config(self.config_data)
        self._note(self.page_body, "Настройки сохранены.")

    def _note(self, parent, message):
        ctk.CTkLabel(parent, text=message, text_color=self.MUTED,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=12)

    def launch_game(self, mode, event_id=""):
        if self.game_process and self.game_process.poll() is None:
            return
        frozen = getattr(sys, "frozen", False)
        if not frozen and not GAME_FILE.exists():
            self.sidebar_status.configure(text="ОШИБКА: НЕТ RGDVD_GAME.PY", text_color="#ff746b")
            return
        if frozen:
            game_executable = ROOT / "RGDVDGame.exe"
            if not game_executable.exists():
                self.sidebar_status.configure(text="НЕТ RGDVDGAME.EXE", text_color="#ff746b")
                return
            args = [str(game_executable)]
        else:
            args = [sys.executable, str(GAME_FILE)]
        args += ["--mode", mode,
                 "--nickname", str(self.config_data.get("nickname", "Driver")),
                 "--room", str(self.config_data.get("room", "OPEN-LOBBY")),
                 "--server", str(self.config_data.get("server_url", DEFAULT_SERVER_URL))]
        if event_id:
            args += ["--event-id", event_id]
        try:
            self.game_process = subprocess.Popen(args, cwd=str(ROOT))
            self.withdraw()
            self.sidebar_status.configure(text="●  ИГРА ЗАПУЩЕНА", text_color="#ffb36b")
        except OSError as exc:
            self.sidebar_status.configure(text=f"ОШИБКА ЗАПУСКА: {exc}", text_color="#ff746b")

    def _poll_game(self):
        if self.game_process and self.game_process.poll() is not None:
            self.game_process = None
            self.deiconify()
            self.lift()
            self.sidebar_status.configure(text="●  ГОТОВО К ЗАПУСКУ", text_color="#75c995")
            self.show_page("home")
        self.after(350, self._poll_game)

    def close_app(self):
        if self.game_process and self.game_process.poll() is None:
            self.game_process.terminate()
        self.destroy()


if __name__ == "__main__":
    RGDVDLauncher().mainloop()
