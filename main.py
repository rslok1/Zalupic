import os
import math
import random
import json
import wave
import struct

os.environ['KIVY_NO_ARGS'] = '1'

import kivy
from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.graphics import Color, Ellipse, Line, Rectangle, InstructionGroup
from kivy.clock import Clock
from kivy.uix.image import Image

# Установка горизонтального разрешения по умолчанию для Kivy
Window.size = (960, 540)

SAVE_FILE = "game_data.json"
SOUND_FILE = "ston.mp3"

# =============================================================
# 🖼️ ЗАДНИЕ ФОНЫ И ИЗОБРАЖЕНИЕ МОНЕТЫ
# - background_menu.png   (для меню и магазина)
# - background_mode1.png  (для Режима 1: вертикальный)
# - background_mode2.png  (для Режима 2: пирамиды)
# - background_mode3.png  (для Режима 3: Земля/Атмосфера)
# - background_space.png  (для Режима 3: Космос при высоте >= 1000 км)
# - coin.png              (картинка для космических монет)
# =============================================================
BG_MENU_IMAGE = "menu.png"
BG_MODE1_IMAGE = "bed.png"
BG_MODE2_IMAGE = "menu.png"
BG_MODE3_IMAGE = "menu.png"
BG_SPACE_IMAGE = "ks.png"
COIN_IMAGE = "coin.png"
DEFAULT_BG_COLOR = (0.12, 0.12, 0.16, 1.0)

MAX_BOOST_LEVEL = 10  # Максимальный уровень прокачки ускорителя


def apply_screen_background(widget, image_file):
    """Добавляет индивидуальный фоновый рисунок или дефолтный цвет к холсту виджета."""
    with widget.canvas.before:
        if os.path.exists(image_file):
            widget.bg_color_inst = Color(1, 1, 1, 1)
            widget.bg_rect_inst = Rectangle(source=image_file, pos=widget.pos, size=widget.size)
        elif os.path.exists("background.png"):
            widget.bg_color_inst = Color(1, 1, 1, 1)
            widget.bg_rect_inst = Rectangle(source="background.png", pos=widget.pos, size=widget.size)
        else:
            widget.bg_color_inst = Color(*DEFAULT_BG_COLOR)
            widget.bg_rect_inst = Rectangle(pos=widget.pos, size=widget.size)

    def _update_bg(inst, value):
        if hasattr(widget, 'bg_rect_inst'):
            widget.bg_rect_inst.pos = widget.pos
            widget.bg_rect_inst.size = widget.size

    widget.bind(pos=_update_bg, size=_update_bg)


# =============================================================
# 👤 ПОСТОЯННЫЙ СКИН ДЛЯ ИГРОКА-СНАРЯДА (НИЖНИЙ / ЛЕВЫЙ)
# =============================================================
BOTTOM_PLAYER_IMAGE = "i.png"
BOTTOM_PLAYER_FALLBACK_COLOR = (1.0, 0.75, 0.15, 1)


# -------------------------------------------------------------
# 🔊 Звук попадания
# -------------------------------------------------------------
def ensure_sound_file():
    if not os.path.exists(SOUND_FILE):
        try:
            fallback_wav = "fallback_hit.wav"
            if not os.path.exists(fallback_wav):
                sample_rate = 22050
                duration = 0.12
                num_samples = int(sample_rate * duration)
                with wave.open(fallback_wav, 'wb') as wav:
                    wav.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
                    for i in range(num_samples):
                        t = float(i) / sample_rate
                        freq = 800.0 - 400.0 * (i / num_samples)
                        value = int(math.sin(2.0 * math.pi * freq * t) * (1.0 - i / num_samples) * 32767)
                        wav.writeframes(struct.pack('<h', value))
        except Exception:
            pass


ensure_sound_file()

# -------------------------------------------------------------
# 🎨 20 Скинов из магазина (ТОЛЬКО ДЛЯ ВТОРОГО ИГРОКА)
# -------------------------------------------------------------
SKINS = [
    {"name": "Классика", "color": (0.35, 0.75, 0.95, 1), "image": "orig.png"},
    {"name": "Изумруд", "color": (0.15, 0.85, 0.40, 1), "image": "2.png"},
    {"name": "Янтарь", "color": (1.0, 0.70, 0.10, 1), "image": "3.png"},
    {"name": "Рубин", "color": (0.95, 0.20, 0.30, 1), "image": "4.png"},
    {"name": "Аметист", "color": (0.70, 0.30, 0.95, 1), "image": "5.png"},
    {"name": "Коралл", "color": (1.0, 0.45, 0.40, 1), "image": "6.png"},
    {"name": "Золото", "color": (0.10, 0.90, 0.85, 1), "image": "7.png"},

]


def get_skin_price(index):
    if index == 0:
        return 0
    return 12 * (2 + (index - 1))


def get_boost_upgrade_price(level):
    """Каждый уровень прокачки стоит +3 монеты, начиная от 1 (ур 1: 1, ур 2: 4, ур 3: 7...)."""
    return 1 + (level - 1) * 3


# -------------------------------------------------------------
# 💾 Сохранение и загрузка прогресса
# -------------------------------------------------------------
def load_game_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["boost_level"] = min(data.get("boost_level", 1), MAX_BOOST_LEVEL)
                return data
        except Exception:
            pass
    return {
        "coins": 0,
        "unlocked_skins": [0],
        "equipped_skin": 0,
        "unlocked_modes": ["mode1"],
        "selected_mode": "mode1",
        "boost_level": 1,
        "high_score_alt": 0
    }


def save_game_data(coins, unlocked_skins, equipped_skin, unlocked_modes, selected_mode, boost_level, high_score_alt):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "coins": coins,
                "unlocked_skins": unlocked_skins,
                "equipped_skin": equipped_skin,
                "unlocked_modes": unlocked_modes,
                "selected_mode": selected_mode,
                "boost_level": min(boost_level, MAX_BOOST_LEVEL),
                "high_score_alt": high_score_alt
            }, f, ensure_ascii=False)
    except Exception:
        pass


# -------------------------------------------------------------
# 🏠 Экран меню
# -------------------------------------------------------------
class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        apply_screen_background(self, BG_MENU_IMAGE)
        self.layout = BoxLayout(orientation='vertical', padding=25, spacing=20)

        top_bar = BoxLayout(size_hint_y=0.12)
        top_bar.add_widget(Widget())
        self.coin_lbl = Label(
            text=" 0",
            font_size='22sp',
            bold=True,
            size_hint_x=None,
            width=160,
            color=(1, 0.85, 0.2, 1),
            halign='right'
        )
        top_bar.add_widget(self.coin_lbl)
        self.layout.add_widget(top_bar)

        self.title_lbl = Label(
            text="Залупик",
            font_size='28sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=0.25
        )
        self.mode_lbl = Label(
            text="Режим: Дуэль",
            font_size='18sp',
            color=(0.3, 0.85, 1, 1),
            size_hint_y=0.10
        )
        self.layout.add_widget(self.title_lbl)
        self.layout.add_widget(self.mode_lbl)

        btn_box = BoxLayout(orientation='vertical', spacing=16, size_hint_y=0.45)

        start_btn = Button(
            text="НАЧАТЬ ИГРУ",
            font_size='22sp',
            bold=True,
            background_color=(0.15, 0.75, 0.35, 1)
        )
        start_btn.bind(on_release=self.start_game)

        shop_btn = Button(
            text="МАГАЗИН (Скины и Режимы)",
            font_size='19sp',
            bold=True,
            background_color=(0.25, 0.55, 0.90, 1)
        )
        shop_btn.bind(on_release=lambda x: self.manager.set_screen('shop'))

        btn_box.add_widget(start_btn)
        btn_box.add_widget(shop_btn)
        self.layout.add_widget(btn_box)

        self.layout.add_widget(Widget(size_hint_y=0.08))
        self.add_widget(self.layout)

    def on_enter(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"
        mode_names = {
            "mode1": "Режим 1: Попади",
            "mode2": "Режим 2: Пирамиды ",
            "mode3": "Режим 3: Полёт в космос "
        }
        self.mode_lbl.text = f"Текущий режим: {mode_names.get(app.selected_mode, 'Дуэль')}"

    def start_game(self, instance):
        app = App.get_running_app()
        if app.selected_mode == "mode2":
            self.manager.set_screen('pyramid_game')
        elif app.selected_mode == "mode3":
            self.manager.set_screen('space_game')
        else:
            self.manager.set_screen('game')


# -------------------------------------------------------------
# 🛒 Экран магазина
# -------------------------------------------------------------
class ShopScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        apply_screen_background(self, BG_MENU_IMAGE)
        self.layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        top_bar = BoxLayout(size_hint_y=0.10)
        back_btn = Button(
            text="Меню",
            size_hint_x=0.32,
            bold=True,
            background_color=(0.3, 0.3, 0.35, 1)
        )
        back_btn.bind(on_release=lambda x: self.manager.set_screen('menu'))

        self.coin_lbl = Label(
            text=" 0",
            font_size='20sp',
            bold=True,
            color=(1, 0.85, 0.2, 1),
            halign='right'
        )

        top_bar.add_widget(back_btn)
        top_bar.add_widget(Widget())
        top_bar.add_widget(self.coin_lbl)
        self.layout.add_widget(top_bar)

        tab_bar = BoxLayout(size_hint_y=0.08, spacing=10)
        self.tab_skins_btn = Button(
            text="СКИНЫ",
            bold=True,
            background_color=(0.2, 0.65, 0.9, 1)
        )
        self.tab_skins_btn.bind(on_release=lambda x: self.switch_tab("skins"))

        self.tab_modes_btn = Button(
            text="РЕЖИМЫ ИГРЫ",
            bold=True,
            background_color=(0.3, 0.3, 0.35, 1)
        )
        self.tab_modes_btn.bind(on_release=lambda x: self.switch_tab("modes"))

        tab_bar.add_widget(self.tab_skins_btn)
        tab_bar.add_widget(self.tab_modes_btn)
        self.layout.add_widget(tab_bar)

        scroll = ScrollView(size_hint=(1, 0.82))
        self.grid = GridLayout(cols=1, spacing=12, size_hint_y=None, padding=[5, 5, 5, 5])
        self.grid.bind(minimum_height=self.grid.setter('height'))
        scroll.add_widget(self.grid)
        self.layout.add_widget(scroll)

        self.add_widget(self.layout)
        self.current_tab = "skins"

    def switch_tab(self, tab):
        self.current_tab = tab
        if tab == "skins":
            self.tab_skins_btn.background_color = (0.2, 0.65, 0.9, 1)
            self.tab_modes_btn.background_color = (0.3, 0.3, 0.35, 1)
            self.refresh_skins_list()
        else:
            self.tab_skins_btn.background_color = (0.3, 0.3, 0.35, 1)
            self.tab_modes_btn.background_color = (0.2, 0.65, 0.9, 1)
            self.refresh_modes_list()

    def on_enter(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"
        self.switch_tab(self.current_tab)

    def refresh_skins_list(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"
        self.grid.clear_widgets()

        preview_size = 110

        for idx, skin in enumerate(SKINS):
            price = get_skin_price(idx)
            is_unlocked = idx in app.unlocked_skins
            is_equipped = idx == app.equipped_skin

            row = BoxLayout(size_hint_y=None, height=105, spacing=12, padding=8)

            img_path = skin["image"]
            if os.path.exists(img_path):
                preview = Image(
                    source=img_path,
                    size_hint=(None, None),
                    size=(preview_size, preview_size),
                    fit_mode="contain"
                )
            else:
                preview_holder = FloatLayout(size_hint=(None, None), size=(preview_size, preview_size))
                with preview_holder.canvas:
                    Color(*skin["color"])
                    Ellipse(pos=(4, 4), size=(preview_size - 8, preview_size - 8))
                preview = preview_holder
            row.add_widget(preview)

            info_lbl = Label(
                text=f"{idx + 1}. {skin['name']}",
                font_size='18sp',
                bold=True,
                halign='left',
                valign='middle'
            )
            info_lbl.bind(size=info_lbl.setter('text_size'))
            row.add_widget(info_lbl)

            if is_equipped:
                action_btn = Button(
                    text="НАДЕТ",
                    size_hint_x=0.36,
                    bold=True,
                    disabled=True,
                    background_color=(0.2, 0.8, 0.3, 1)
                )
            elif is_unlocked:
                action_btn = Button(
                    text="НАДЕТЬ",
                    size_hint_x=0.36,
                    bold=True,
                    background_color=(0.25, 0.55, 0.9, 1)
                )
                action_btn.bind(on_release=lambda x, i=idx: self.equip_skin(i))
            else:
                action_btn = Button(
                    text=f"{price} ",
                    size_hint_x=0.36,
                    bold=True,
                    background_color=(0.9, 0.65, 0.15, 1) if app.coins >= price else (0.4, 0.4, 0.4, 1)
                )
                action_btn.bind(on_release=lambda x, i=idx, p=price: self.buy_skin(i, p))

            row.add_widget(action_btn)
            self.grid.add_widget(row)

    def buy_skin(self, idx, price):
        app = App.get_running_app()
        if app.coins >= price:
            app.coins -= price
            app.unlocked_skins.append(idx)
            app.equipped_skin = idx
            app.save()
            self.refresh_skins_list()

    def equip_skin(self, idx):
        app = App.get_running_app()
        app.equipped_skin = idx
        app.save()
        self.refresh_skins_list()

    def refresh_modes_list(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"
        self.grid.clear_widgets()

        modes = [
            {
                "id": "mode1",
                "name": "Режим 1: Попади",
                "desc": "Рогатка снизу, верхний игрок двигается. Стандартный режим.",
                "price": 0,
                "ready": True
            },
            {
                "id": "mode2",
                "name": "Режим 2: Пирамиды",
                "desc": "Рогатка слева. Сбей 2 пирамидки из 10 скинов. Падение 6+ дает +2 монеты!",
                "price": 50,
                "ready": True
            },
            {
                "id": "mode3",
                "name": "Режим 3: Космос ",
                "desc": "Запуск в космос! Прокачивай ускоритель до 10 уровня и летай по космосу, собирая монеты!",
                "price": 200,
                "ready": True
            }
        ]

        for m in modes:
            row = BoxLayout(size_hint_y=None, height=115, spacing=12, padding=10)

            info_box = BoxLayout(orientation='vertical', size_hint_x=0.64)
            t_lbl = Label(text=m["name"], font_size='18sp', bold=True, halign='left')
            t_lbl.bind(size=t_lbl.setter('text_size'))
            d_lbl = Label(text=m["desc"], font_size='13sp', color=(0.8, 0.8, 0.85, 1), halign='left')
            d_lbl.bind(size=d_lbl.setter('text_size'))
            info_box.add_widget(t_lbl)
            info_box.add_widget(d_lbl)
            row.add_widget(info_box)

            if not m["ready"]:
                btn = Button(
                    text="СКОРО",
                    size_hint_x=0.36,
                    bold=True,
                    disabled=True,
                    background_color=(0.25, 0.25, 0.28, 1)
                )
            elif m["id"] == app.selected_mode:
                btn = Button(
                    text="ВЫБРАН",
                    size_hint_x=0.36,
                    bold=True,
                    disabled=True,
                    background_color=(0.2, 0.8, 0.3, 1)
                )
            elif m["id"] in app.unlocked_modes:
                btn = Button(
                    text="ВЫБРАТЬ",
                    size_hint_x=0.36,
                    bold=True,
                    background_color=(0.25, 0.55, 0.9, 1)
                )
                btn.bind(on_release=lambda x, mid=m["id"]: self.select_mode(mid))
            else:
                price = m["price"]
                btn = Button(
                    text=f"{price} ",
                    size_hint_x=0.36,
                    bold=True,
                    background_color=(0.9, 0.65, 0.15, 1) if app.coins >= price else (0.4, 0.4, 0.4, 1)
                )
                btn.bind(on_release=lambda x, mid=m["id"], p=price: self.buy_mode(mid, p))

            row.add_widget(btn)
            self.grid.add_widget(row)

    def buy_mode(self, mode_id, price):
        app = App.get_running_app()
        if app.coins >= price:
            app.coins -= price
            app.unlocked_modes.append(mode_id)
            app.selected_mode = mode_id
            app.save()
            self.refresh_modes_list()

    def select_mode(self, mode_id):
        app = App.get_running_app()
        app.selected_mode = mode_id
        app.save()
        self.refresh_modes_list()


# -------------------------------------------------------------
# 🎮 РЕЖИМ 1: Игровое поле и рогатка
# -------------------------------------------------------------
class SlingshotGame(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.player_radius = 48
        self.target_radius = 58

        self.anchor_x = 0
        self.anchor_y = 190
        self.proj_x = 0
        self.proj_y = 0
        self.vx = 0
        self.vy = 0
        self.is_flying = False
        self.is_dragging = False

        self.target_x = 0
        self.target_y = 0
        self.target_speed = 130
        self.target_dir = 1

        with self.canvas:
            self.band_color = Color(0.85, 0.35, 0.15, 1)
            self.band_left = Line(points=[], width=4.5)
            self.band_right = Line(points=[], width=4.5)

            self.base_color = Color(0.4, 0.25, 0.15, 1)
            self.base_line = Line(points=[], width=7)

            self.target_color = Color(1, 1, 1, 1)
            self.target_rect = Rectangle(size=(0, 0))
            self.target_ellipse = Ellipse(size=(0, 0))

            self.player_color = Color(1, 1, 1, 1)
            img_path = BOTTOM_PLAYER_IMAGE
            if os.path.exists(img_path):
                self.player_draw = Rectangle(source=img_path, size=(self.player_radius * 2, self.player_radius * 2))
            else:
                self.player_color.rgba = BOTTOM_PLAYER_FALLBACK_COLOR
                self.player_draw = Ellipse(size=(self.player_radius * 2, self.player_radius * 2))

        Clock.schedule_interval(self.update, 1.0 / 60.0)

    def apply_top_target_skin(self):
        app = App.get_running_app()
        skin = SKINS[app.equipped_skin]
        img_path = skin["image"]
        diameter = self.target_radius * 2

        if os.path.exists(img_path):
            self.target_color.rgba = (1, 1, 1, 1)
            self.target_rect.source = img_path
            self.target_rect.size = (diameter, diameter)
            self.target_ellipse.size = (0, 0)
        else:
            self.target_rect.source = ''
            self.target_rect.size = (0, 0)
            self.target_color.rgba = skin["color"]
            self.target_ellipse.size = (diameter, diameter)

    def reset_positions(self):
        self.anchor_x = self.width / 2
        self.proj_x = self.anchor_x
        self.proj_y = self.anchor_y
        self.vx = 0
        self.vy = 0
        self.is_flying = False
        self.is_dragging = False
        self.target_x = self.width / 2
        self.target_y = self.height - 130

        self.apply_top_target_skin()

    def on_touch_down(self, touch):
        if self.is_flying:
            return False
        dist = math.dist(touch.pos, (self.anchor_x, self.anchor_y))
        if dist < 110:
            self.is_dragging = True
            self.pull_to(touch.x, touch.y)
            return True
        return False

    def on_touch_move(self, touch):
        if self.is_dragging:
            self.pull_to(touch.x, touch.y)
            return True
        return False

    def on_touch_up(self, touch):
        if self.is_dragging:
            self.is_dragging = False
            dx = self.anchor_x - self.proj_x
            dy = self.anchor_y - self.proj_y
            pull_dist = math.sqrt(dx * dx + dy * dy)

            if pull_dist > 18:
                speed_multiplier = 14.0
                self.vx = dx * speed_multiplier
                self.vy = dy * speed_multiplier
                self.is_flying = True
            else:
                self.proj_x = self.anchor_x
                self.proj_y = self.anchor_y
            return True
        return False

    def pull_to(self, tx, ty):
        dx = tx - self.anchor_x
        dy = ty - self.anchor_y
        dist = math.sqrt(dx * dx + dy * dy)
        max_pull = 140

        if dist > max_pull:
            scale = max_pull / dist
            dx *= scale
            dy *= scale

        if dy > 10:
            dy = 10

        self.proj_x = self.anchor_x + dx
        self.proj_y = self.anchor_y + dy

    def update(self, dt):
        if self.width <= 10 or self.height <= 10:
            return

        if self.anchor_x == 0:
            self.reset_positions()

        self.target_x += self.target_dir * self.target_speed * dt
        min_x = self.target_radius + 20
        max_x = self.width - self.target_radius - 20
        if self.target_x <= min_x:
            self.target_x = min_x
            self.target_dir = 1
        elif self.target_x >= max_x:
            self.target_x = max_x
            self.target_dir = -1

        if self.is_flying:
            self.proj_x += self.vx * dt
            self.proj_y += self.vy * dt

            dist_to_target = math.dist((self.proj_x, self.proj_y), (self.target_x, self.target_y))
            if dist_to_target <= (self.player_radius + self.target_radius):
                app = App.get_running_app()
                app.on_target_hit(reward=1)
                self.reset_projectile()

            elif (self.proj_y > self.height + 80 or
                  self.proj_y < -80 or
                  self.proj_x < -80 or
                  self.proj_x > self.width + 80):
                self.reset_projectile()

        left_post = (self.anchor_x - 50, self.anchor_y + 20)
        right_post = (self.anchor_x + 50, self.anchor_y + 20)
        self.base_line.points = [
            self.anchor_x, self.anchor_y - 75,
            self.anchor_x, self.anchor_y,
            left_post[0], left_post[1],
            self.anchor_x, self.anchor_y,
            right_post[0], right_post[1]
        ]

        if not self.is_flying:
            self.band_left.points = [left_post[0], left_post[1], self.proj_x, self.proj_y]
            self.band_right.points = [right_post[0], right_post[1], self.proj_x, self.proj_y]
        else:
            self.band_left.points = [left_post[0], left_post[1], self.anchor_x, self.anchor_y]
            self.band_right.points = [right_post[0], right_post[1], self.anchor_x, self.anchor_y]

        self.player_draw.pos = (self.proj_x - self.player_radius, self.proj_y - self.player_radius)
        target_pos = (self.target_x - self.target_radius, self.target_y - self.target_radius)
        self.target_rect.pos = target_pos
        self.target_ellipse.pos = target_pos

    def reset_projectile(self):
        self.is_flying = False
        self.is_dragging = False
        self.proj_x = self.anchor_x
        self.proj_y = self.anchor_y
        self.vx = 0
        self.vy = 0


# -------------------------------------------------------------
# 🎯 Экран Режима 1
# -------------------------------------------------------------
class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        apply_screen_background(self, BG_MODE1_IMAGE)
        self.game = SlingshotGame()
        self.add_widget(self.game)

        top_bar = BoxLayout(
            size_hint=(1, None),
            height=60,
            pos_hint={'top': 1},
            padding=[15, 8, 15, 8]
        )

        menu_btn = Button(
            text="Меню",
            size_hint=(None, 1),
            width=110,
            bold=True,
            background_color=(0.25, 0.25, 0.3, 0.9)
        )
        menu_btn.bind(on_release=lambda x: self.manager.set_screen('menu'))

        self.coin_lbl = Label(
            text="0",
            font_size='22sp',
            bold=True,
            color=(1, 0.85, 0.2, 1),
            halign='right'
        )

        top_bar.add_widget(menu_btn)
        top_bar.add_widget(Widget())
        top_bar.add_widget(self.coin_lbl)
        self.add_widget(top_bar)

    def on_enter(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"
        self.game.reset_positions()

    def update_coin_label(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"


# -------------------------------------------------------------
# 🕹️ РЕЖИМ 2: 2 Пирамидки по 10 скинов
# -------------------------------------------------------------
class PyramidGameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.player_radius = 42
        self.target_radius = 26

        self.anchor_x = 130
        self.anchor_y = 220
        self.proj_x = 0
        self.proj_y = 0
        self.vx = 0
        self.vy = 0
        self.gravity = -550
        self.is_flying = False
        self.is_dragging = False

        self.targets = []
        self.reward_claimed = False

        with self.canvas:
            self.ground_color = Color(0.2, 0.5, 0.25, 0.7)
            self.ground_line = Line(points=[], width=6)

            self.band_color = Color(0.85, 0.35, 0.15, 1)
            self.band_up = Line(points=[], width=4.5)
            self.band_down = Line(points=[], width=4.5)

            self.base_color = Color(0.4, 0.25, 0.15, 1)
            self.base_line = Line(points=[], width=7)

            self.targets_canvas = Widget()

            self.player_color = Color(1, 1, 1, 1)
            img_path = BOTTOM_PLAYER_IMAGE
            if os.path.exists(img_path):
                self.player_draw = Rectangle(source=img_path, size=(self.player_radius * 2, self.player_radius * 2))
            else:
                self.player_color.rgba = BOTTOM_PLAYER_FALLBACK_COLOR
                self.player_draw = Ellipse(size=(self.player_radius * 2, self.player_radius * 2))

        Clock.schedule_interval(self.update, 1.0 / 60.0)

    def build_pyramids(self):
        app = App.get_running_app()
        skin = SKINS[app.equipped_skin]
        img_path = skin["image"]
        use_image = (img_path and os.path.exists(img_path))

        self.canvas.remove_group('pyramid_targets')
        self.targets = []
        self.reward_claimed = False

        d = self.target_radius * 2
        ground_y = 100

        p1_center_x = max(self.width * 0.52, 420)
        p2_center_x = max(self.width * 0.78, 640)

        centers = [p1_center_x, p2_center_x]

        with self.canvas:
            for cx in centers:
                for row_idx, count in enumerate([4, 3, 2, 1]):
                    y = ground_y + self.target_radius + row_idx * (d + 2)
                    start_x = cx - (count - 1) * (d + 4) / 2.0

                    for col in range(count):
                        x = start_x + col * (d + 4)
                        orig_y = y

                        if use_image:
                            Color(1, 1, 1, 1, group='pyramid_targets')
                            draw_elem = Rectangle(
                                source=img_path,
                                pos=(x - self.target_radius, y - self.target_radius),
                                size=(d, d),
                                group='pyramid_targets'
                            )
                        else:
                            Color(*skin["color"], group='pyramid_targets')
                            draw_elem = Ellipse(
                                pos=(x - self.target_radius, y - self.target_radius),
                                size=(d, d),
                                group='pyramid_targets'
                            )

                        target_obj = {
                            "x": x,
                            "y": y,
                            "vx": 0.0,
                            "vy": 0.0,
                            "orig_y": orig_y,
                            "fallen": False,
                            "elem": draw_elem,
                            "use_image": use_image
                        }
                        self.targets.append(target_obj)

    def reset_positions(self):
        self.anchor_x = max(90, self.width * 0.14)
        self.anchor_y = 210
        self.proj_x = self.anchor_x
        self.proj_y = self.anchor_y
        self.vx = 0
        self.vy = 0
        self.is_flying = False
        self.is_dragging = False

        self.build_pyramids()

    def on_touch_down(self, touch):
        if self.is_flying:
            return False
        dist = math.dist(touch.pos, (self.anchor_x, self.anchor_y))
        if dist < 110:
            self.is_dragging = True
            self.pull_to(touch.x, touch.y)
            return True
        return False

    def on_touch_move(self, touch):
        if self.is_dragging:
            self.pull_to(touch.x, touch.y)
            return True
        return False

    def on_touch_up(self, touch):
        if self.is_dragging:
            self.is_dragging = False
            dx = self.anchor_x - self.proj_x
            dy = self.anchor_y - self.proj_y
            pull_dist = math.sqrt(dx * dx + dy * dy)

            if pull_dist > 18:
                speed_multiplier = 14.5
                self.vx = dx * speed_multiplier
                self.vy = dy * speed_multiplier
                self.is_flying = True
            else:
                self.proj_x = self.anchor_x
                self.proj_y = self.anchor_y
            return True
        return False

    def pull_to(self, tx, ty):
        dx = tx - self.anchor_x
        dy = ty - self.anchor_y
        dist = math.sqrt(dx * dx + dy * dy)
        max_pull = 140

        if dist > max_pull:
            scale = max_pull / dist
            dx *= scale
            dy *= scale

        if dx > 10:
            dx = 10

        self.proj_x = self.anchor_x + dx
        self.proj_y = self.anchor_y + dy

    def update(self, dt):
        if self.width <= 10 or self.height <= 10:
            return

        if self.anchor_x == 0 or len(self.targets) == 0:
            self.reset_positions()

        ground_y = 100
        self.ground_line.points = [0, ground_y, self.width, ground_y]

        if self.is_flying:
            self.proj_x += self.vx * dt
            self.vy += self.gravity * dt
            self.proj_y += self.vy * dt

            hit_any = False
            for t in self.targets:
                dist = math.dist((self.proj_x, self.proj_y), (t["x"], t["y"]))
                if dist <= (self.player_radius + self.target_radius):
                    hit_any = True
                    t["vx"] += self.vx * 0.45 + (t["x"] - self.proj_x) * 4.0
                    t["vy"] += self.vy * 0.35 + (t["y"] - self.proj_y) * 4.0
                    t["fallen"] = True

            if hit_any:
                app = App.get_running_app()
                app.play_hit_sound()
                self.vx *= 0.65
                self.vy *= 0.65

            if self.proj_y <= (ground_y + self.player_radius):
                self.proj_y = ground_y + self.player_radius
                self.vx *= 0.8
                self.vy = -self.vy * 0.3
                if abs(self.vy) < 30 and abs(self.vx) < 30:
                    self.reset_projectile()

            if self.proj_x > self.width + 100 or self.proj_x < -100:
                self.reset_projectile()

        fallen_count = 0
        d = self.target_radius * 2

        for t in self.targets:
            if t["fallen"]:
                t["vy"] += self.gravity * 0.9 * dt
                t["x"] += t["vx"] * dt
                t["y"] += t["vy"] * dt

                if t["y"] <= (ground_y + self.target_radius):
                    t["y"] = ground_y + self.target_radius
                    t["vy"] = -t["vy"] * 0.25
                    t["vx"] *= 0.85

            if t["fallen"] or (t["orig_y"] - t["y"]) > 18 or abs(t["vx"]) > 10:
                fallen_count += 1

            t["elem"].pos = (t["x"] - self.target_radius, t["y"] - self.target_radius)

        if fallen_count >= 6 and not self.reward_claimed:
            self.reward_claimed = True
            app = App.get_running_app()
            app.on_target_hit(reward=2)

        up_post = (self.anchor_x - 15, self.anchor_y + 45)
        down_post = (self.anchor_x - 15, self.anchor_y - 45)
        self.base_line.points = [
            self.anchor_x - 70, self.anchor_y,
            self.anchor_x, self.anchor_y,
            up_post[0], up_post[1],
            self.anchor_x, self.anchor_y,
            down_post[0], down_post[1]
        ]

        if not self.is_flying:
            self.band_up.points = [up_post[0], up_post[1], self.proj_x, self.proj_y]
            self.band_down.points = [down_post[0], down_post[1], self.proj_x, self.proj_y]
        else:
            self.band_up.points = [up_post[0], up_post[1], self.anchor_x, self.anchor_y]
            self.band_down.points = [down_post[0], down_post[1], self.anchor_x, self.anchor_y]

        self.player_draw.pos = (self.proj_x - self.player_radius, self.proj_y - self.player_radius)

    def reset_projectile(self):
        self.is_flying = False
        self.is_dragging = False
        self.proj_x = self.anchor_x
        self.proj_y = self.anchor_y
        self.vx = 0
        self.vy = 0


# -------------------------------------------------------------
# 🎯 Экран Режима 2 (Пирамиды)
# -------------------------------------------------------------
class PyramidGameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        apply_screen_background(self, BG_MODE2_IMAGE)
        self.game = PyramidGameWidget()
        self.add_widget(self.game)

        top_bar = BoxLayout(
            size_hint=(1, None),
            height=60,
            pos_hint={'top': 1},
            padding=[15, 8, 15, 8]
        )

        menu_btn = Button(
            text="Меню",
            size_hint=(None, 1),
            width=110,
            bold=True,
            background_color=(0.25, 0.25, 0.3, 0.9)
        )
        menu_btn.bind(on_release=lambda x: self.manager.set_screen('menu'))

        restart_btn = Button(
            text="Заново",
            size_hint=(None, 1),
            width=115,
            bold=True,
            background_color=(0.35, 0.45, 0.2, 0.9)
        )
        restart_btn.bind(on_release=lambda x: self.game.reset_positions())

        self.coin_lbl = Label(
            text=" 0",
            font_size='22sp',
            bold=True,
            color=(1, 0.85, 0.2, 1),
            halign='right'
        )

        top_bar.add_widget(menu_btn)
        top_bar.add_widget(Widget(size_hint_x=0.05))
        top_bar.add_widget(restart_btn)
        top_bar.add_widget(Widget())
        top_bar.add_widget(self.coin_lbl)
        self.add_widget(top_bar)

    def on_enter(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"
        self.game.reset_positions()

    def update_coin_label(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"


# -------------------------------------------------------------
# 🚀 РЕЖИМ 3: Полёт первого игрока в космос
# -------------------------------------------------------------
WORLD_WIDTH = 4500.0
WORLD_HEIGHT = 4500.0
NUM_SPACE_COINS = 85


class SpaceGameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.player_radius = 46

        self.default_anchor_y = 170.0
        self.anchor_x = 0
        self.anchor_y = self.default_anchor_y
        self.target_anchor_y = self.default_anchor_y

        self.proj_x = 0
        self.proj_y = 0
        self.vy = 0
        self.altitude = 0.0
        self.max_altitude = 0.0
        self.is_flying = False
        self.is_dragging = False
        self.is_finished = False

        # Режим свободного полета в космосе (на 10 уровне)
        self.is_roaming = False
        self.world_x = WORLD_WIDTH / 2.0
        self.world_y = WORLD_HEIGHT / 2.0
        self.move_vx = 0.0
        self.move_vy = 0.0
        self.move_input_x = 0.0
        self.move_input_y = 0.0

        # Монеты в космосе
        self.space_coins = []
        self.coin_radius = 22.0

        self.coins_awarded = 0
        self.is_space_bg = False

        with self.canvas:
            self.band_color = Color(0.85, 0.35, 0.15, 1)
            self.band_left = Line(points=[], width=4.5)
            self.band_right = Line(points=[], width=4.5)

            self.base_color = Color(0.4, 0.25, 0.15, 1)
            self.base_line = Line(points=[], width=7)

            self.flame_color = Color(1, 0.5, 0.0, 0)
            self.flame_draw = Ellipse(size=(28, 48))

            self.player_color = Color(1, 1, 1, 1)
            img_path = BOTTOM_PLAYER_IMAGE
            if os.path.exists(img_path):
                self.player_draw = Rectangle(source=img_path, size=(self.player_radius * 2, self.player_radius * 2))
            else:
                self.player_color.rgba = BOTTOM_PLAYER_FALLBACK_COLOR
                self.player_draw = Ellipse(size=(self.player_radius * 2, self.player_radius * 2))

        Clock.schedule_interval(self.update, 1.0 / 60.0)

    def generate_space_coins(self):
        """Создает монеты по космосу с поддержкой кастомной картинки coin.png."""
        if hasattr(self, 'space_coins'):
            for c in self.space_coins:
                if 'group' in c and c['group'] in self.canvas.before.children:
                    self.canvas.before.remove(c['group'])

        self.space_coins = []
        use_coin_img = os.path.exists(COIN_IMAGE)

        for _ in range(NUM_SPACE_COINS):
            cx = random.uniform(150.0, WORLD_WIDTH - 150.0)
            cy = random.uniform(150.0, WORLD_HEIGHT - 150.0)

            grp = InstructionGroup()
            d = self.coin_radius * 2

            if use_coin_img:
                grp.add(Color(1, 1, 1, 1))
                draw_elem = Rectangle(source=COIN_IMAGE, size=(d, d), pos=(-1000, -1000))
                grp.add(draw_elem)
                inner_elem = None
            else:
                grp.add(Color(1.0, 0.85, 0.1, 1.0))
                draw_elem = Ellipse(size=(d, d), pos=(-1000, -1000))
                grp.add(draw_elem)
                grp.add(Color(1.0, 0.98, 0.5, 1.0))
                inner_elem = Ellipse(size=(self.coin_radius, self.coin_radius), pos=(-1000, -1000))
                grp.add(inner_elem)

            self.canvas.before.add(grp)

            self.space_coins.append({
                "x": cx,
                "y": cy,
                "collected": False,
                "group": grp,
                "draw_elem": draw_elem,
                "inner_elem": inner_elem,
                "use_img": use_coin_img
            })

    def reset_positions(self):
        self.anchor_x = self.width / 2
        self.anchor_y = self.default_anchor_y
        self.target_anchor_y = self.default_anchor_y
        self.proj_x = self.anchor_x
        self.proj_y = self.anchor_y
        self.vy = 0
        self.altitude = 0.0
        self.max_altitude = 0.0
        self.is_flying = False
        self.is_dragging = False
        self.is_finished = False
        self.is_roaming = False
        self.move_input_x = 0.0
        self.move_input_y = 0.0
        self.move_vx = 0.0
        self.move_vy = 0.0
        self.world_x = WORLD_WIDTH / 2.0
        self.world_y = WORLD_HEIGHT / 2.0
        self.coins_awarded = 0
        self.flame_color.a = 0
        self.set_background(is_space=False)
        self.generate_space_coins()

    def set_background(self, is_space):
        self.is_space_bg = is_space
        parent_screen = self.parent
        if parent_screen and hasattr(parent_screen, 'bg_rect_inst'):
            target_img = BG_SPACE_IMAGE if is_space else BG_MODE3_IMAGE
            if os.path.exists(target_img):
                parent_screen.bg_rect_inst.source = target_img
                parent_screen.bg_color_inst.rgba = (1, 1, 1, 1)
            else:
                parent_screen.bg_rect_inst.source = ''
                if is_space:
                    parent_screen.bg_color_inst.rgba = (0.02, 0.02, 0.08, 1.0)
                else:
                    parent_screen.bg_color_inst.rgba = (0.15, 0.25, 0.45, 1.0)

    def on_touch_down(self, touch):
        if self.is_flying or self.is_finished or self.is_roaming:
            return False
        dist = math.dist(touch.pos, (self.anchor_x, self.anchor_y))
        if dist < 110:
            self.is_dragging = True
            self.pull_to(touch.x, touch.y)
            return True
        return False

    def on_touch_move(self, touch):
        if self.is_dragging:
            self.pull_to(touch.x, touch.y)
            return True
        return False

    def on_touch_up(self, touch):
        if self.is_dragging:
            self.is_dragging = False
            dy = self.anchor_y - self.proj_y
            if dy > 20:
                app = App.get_running_app()
                boost_lvl = min(app.boost_level, MAX_BOOST_LEVEL)
                launch_multiplier = 6.5 + (boost_lvl - 1) * 0.7
                self.vy = dy * launch_multiplier
                self.is_flying = True
                app.play_hit_sound()
            else:
                self.proj_x = self.anchor_x
                self.proj_y = self.anchor_y
            return True
        return False

    def pull_to(self, tx, ty):
        dy = ty - self.anchor_y
        max_pull = 135
        if dy > 0:
            dy = 0
        if dy < -max_pull:
            dy = -max_pull
        self.proj_x = self.anchor_x
        self.proj_y = self.anchor_y + dy

    def apply_boost(self):
        app = App.get_running_app()
        if app.boost_level >= MAX_BOOST_LEVEL or self.is_roaming:
            return

        cost = get_boost_upgrade_price(app.boost_level)
        if app.coins >= cost:
            app.coins -= cost
            app.boost_level = min(app.boost_level + 1, MAX_BOOST_LEVEL)
            app.save()

            boost_impulse = 200 + (app.boost_level * 25)
            if self.is_flying:
                self.vy = max(self.vy + boost_impulse, boost_impulse * 0.95)
                self.altitude += 12.0 * app.boost_level
                if self.altitude > self.max_altitude:
                    self.max_altitude = self.altitude

            self.flame_color.a = 0.95
            Clock.schedule_once(self._hide_flame, 0.40)

            app.play_hit_sound()
            if self.parent:
                self.parent.update_ui()
                self.parent.update_altitude_label(self.altitude)

    def _hide_flame(self, dt):
        self.flame_color.a = 0

    def enter_space_roam_mode(self):
        self.is_roaming = True
        self.is_flying = False
        self.vy = 0
        self.set_background(is_space=True)

        self.proj_x = self.width / 2.0
        self.proj_y = self.height / 2.0
        self.world_x = WORLD_WIDTH / 2.0
        self.world_y = WORLD_HEIGHT / 2.0

        self.anchor_y = -300.0

        if self.parent:
            self.parent.activate_space_roam_controls()

    def set_move_dir(self, dx, dy):
        self.move_input_x = dx
        self.move_input_y = dy

    def update(self, dt):
        if self.width <= 10 or self.height <= 10:
            return

        if self.anchor_x == 0 or len(self.space_coins) == 0:
            self.reset_positions()

        if self.is_roaming:
            speed = 420.0
            friction = 0.92

            if abs(self.move_input_x) > 0 or abs(self.move_input_y) > 0:
                self.move_vx += self.move_input_x * speed * 4.0 * dt
                self.move_vy += self.move_input_y * speed * 4.0 * dt
                self.flame_color.a = 0.9
            else:
                self.flame_color.a = 0

            max_s = 480.0
            self.move_vx = max(-max_s, min(max_s, self.move_vx * friction))
            self.move_vy = max(-max_s, min(max_s, self.move_vy * friction))

            self.world_x += self.move_vx * dt
            self.world_y += self.move_vy * dt

            self.world_x = max(self.player_radius, min(WORLD_WIDTH - self.player_radius, self.world_x))
            self.world_y = max(self.player_radius, min(WORLD_HEIGHT - self.player_radius, self.world_y))

            cam_x = self.world_x - (self.width / 2.0)
            cam_y = self.world_y - (self.height / 2.0)

            app = App.get_running_app()
            for c in self.space_coins:
                if not c["collected"]:
                    dist = math.hypot(self.world_x - c["x"], self.world_y - c["y"])
                    if dist <= (self.player_radius + self.coin_radius):
                        c["collected"] = True
                        if c["group"] in self.canvas.before.children:
                            self.canvas.before.remove(c["group"])
                        app.coins += 10
                        app.save()
                        app.play_hit_sound()
                        if self.parent:
                            self.parent.update_ui()
                        continue

                    sx = c["x"] - cam_x
                    sy = c["y"] - cam_y
                    d = self.coin_radius * 2

                    if -60 <= sx <= self.width + 60 and -60 <= sy <= self.height + 60:
                        c["draw_elem"].pos = (sx - self.coin_radius, sy - self.coin_radius)
                        c["draw_elem"].size = (d, d)
                        if c["inner_elem"]:
                            c["inner_elem"].pos = (sx - self.coin_radius / 2, sy - self.coin_radius / 2)
                            c["inner_elem"].size = (self.coin_radius, self.coin_radius)
                    else:
                        c["draw_elem"].size = (0, 0)
                        if c["inner_elem"]:
                            c["inner_elem"].size = (0, 0)

            self.proj_x = self.width / 2.0
            self.proj_y = self.height / 2.0
            self.player_draw.pos = (self.proj_x - self.player_radius, self.proj_y - self.player_radius)
            self.flame_draw.pos = (self.proj_x - 14, self.proj_y - self.player_radius - 36)

            self.base_line.points = []
            self.band_left.points = []
            self.band_right.points = []
            return

        for c in self.space_coins:
            if not c["collected"]:
                c["draw_elem"].size = (0, 0)
                if c["inner_elem"]:
                    c["inner_elem"].size = (0, 0)

        if self.is_flying:
            if self.vy > 0 or self.altitude > 150.0:
                self.target_anchor_y = -130.0
            else:
                self.target_anchor_y = self.default_anchor_y
        else:
            self.target_anchor_y = self.default_anchor_y

        self.anchor_y += (self.target_anchor_y - self.anchor_y) * 4.5 * dt

        if self.is_flying:
            if self.vy > 0:
                up_gravity = 250.0
                self.vy -= up_gravity * dt

                self.altitude += (self.vy * dt) * 0.19
                if self.altitude > self.max_altitude:
                    self.max_altitude = self.altitude

                target_screen_y = min(self.height * 0.58, self.default_anchor_y + min(220.0, self.altitude * 0.45))
                self.proj_y += (target_screen_y - self.proj_y) * 4.0 * dt

            else:
                app = App.get_running_app()
                if app.boost_level >= MAX_BOOST_LEVEL:
                    self.enter_space_roam_mode()
                    return

                down_gravity = 650.0
                self.vy -= down_gravity * dt

                self.altitude += (self.vy * dt) * 0.24

                ratio = max(0.0, self.altitude) / max(1.0, self.max_altitude)
                target_screen_y = self.default_anchor_y + ratio * 180.0
                self.proj_y += (target_screen_y - self.proj_y) * 8.0 * dt

                if self.altitude <= 0 or self.proj_y <= (self.default_anchor_y + 3.0):
                    self.altitude = 0.0
                    self.proj_y = self.default_anchor_y
                    self.anchor_y = self.default_anchor_y
                    self.vy = 0.0
                    self.is_flying = False
                    self.is_finished = True
                    self.on_flight_finished()

            if self.altitude >= 1000.0 and not self.is_space_bg:
                self.set_background(is_space=True)
            elif self.altitude < 1000.0 and self.is_space_bg:
                self.set_background(is_space=False)

            if self.parent:
                self.parent.update_altitude_label(self.altitude)

        left_post = (self.anchor_x - 50, self.anchor_y + 20)
        right_post = (self.anchor_x + 50, self.anchor_y + 20)
        self.base_line.points = [
            self.anchor_x, self.anchor_y - 75,
            self.anchor_x, self.anchor_y,
            left_post[0], left_post[1],
            self.anchor_x, self.anchor_y,
            right_post[0], right_post[1]
        ]

        if not self.is_flying:
            self.band_left.points = [left_post[0], left_post[1], self.proj_x, self.proj_y]
            self.band_right.points = [right_post[0], right_post[1], self.proj_x, self.proj_y]
        else:
            self.band_left.points = [left_post[0], left_post[1], self.anchor_x, self.anchor_y]
            self.band_right.points = [right_post[0], right_post[1], self.anchor_x, self.anchor_y]

        self.player_draw.pos = (self.proj_x - self.player_radius, self.proj_y - self.player_radius)
        self.flame_draw.pos = (self.proj_x - 14, self.proj_y - self.player_radius - 40)

    def on_flight_finished(self):
        app = App.get_running_app()
        int_max_alt = int(self.max_altitude)

        is_new_record = False
        if int_max_alt > app.high_score_alt:
            app.high_score_alt = int_max_alt
            is_new_record = True

        reward = int(self.max_altitude // 80)
        if self.max_altitude >= 1000.0:
            reward += 15

        if reward > 0:
            app.coins += reward
            self.coins_awarded = reward

        app.save()

        if self.parent:
            self.parent.show_results(self.max_altitude, reward, is_new_record)


# -------------------------------------------------------------
# 🎯 Экран Режима 3 (Космос)
# -------------------------------------------------------------
class SpaceGameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        apply_screen_background(self, BG_MODE3_IMAGE)

        self.game = SpaceGameWidget()
        self.add_widget(self.game)

        top_bar = BoxLayout(
            size_hint=(1, None),
            height=70,
            pos_hint={'top': 1},
            padding=[10, 6, 10, 6],
            spacing=8
        )

        menu_btn = Button(
            text="Меню",
            size_hint=(None, 1),
            width=85,
            bold=True,
            background_color=(0.25, 0.25, 0.3, 0.9)
        )
        menu_btn.bind(on_release=lambda x: self.manager.set_screen('menu'))

        self.top_restart_btn = Button(
            text="Заново",
            size_hint=(None, 1),
            width=95,
            bold=True,
            font_size='14sp',
            background_color=(0.2, 0.65, 0.35, 0.95)
        )
        self.top_restart_btn.bind(on_release=self.restart_flight)

        reset_btn = Button(
            text="Сброс",
            size_hint=(None, 1),
            width=90,
            bold=True,
            font_size='14sp',
            background_color=(0.85, 0.25, 0.25, 0.95)
        )
        reset_btn.bind(on_release=self.show_confirm_reset_popup)

        center_box = BoxLayout(orientation='vertical', size_hint=(1, 1))
        self.alt_lbl = Label(
            text="Высота: 0 км",
            font_size='18sp',
            bold=True,
            color=(0.2, 0.95, 1, 1),
            halign='center'
        )
        self.record_lbl = Label(
            text="Рекорд: 0 км",
            font_size='14sp',
            bold=True,
            color=(1, 0.85, 0.25, 1),
            halign='center'
        )
        center_box.add_widget(self.alt_lbl)
        center_box.add_widget(self.record_lbl)

        self.coin_lbl = Label(
            text=" 0",
            font_size='22sp',
            bold=True,
            color=(1, 0.85, 0.2, 1),
            size_hint=(None, 1),
            width=95,
            halign='right'
        )

        top_bar.add_widget(menu_btn)
        top_bar.add_widget(self.top_restart_btn)
        top_bar.add_widget(reset_btn)
        top_bar.add_widget(center_box)
        top_bar.add_widget(self.coin_lbl)
        self.add_widget(top_bar)

        self.restart_btn = Button(
            text="Лететь снова",
            size_hint=(None, None),
            size=(220, 60),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            bold=True,
            font_size='18sp',
            background_color=(0.2, 0.8, 0.3, 0.95),
            opacity=0,
            disabled=True
        )
        self.restart_btn.bind(on_release=self.restart_flight)
        self.add_widget(self.restart_btn)

        self.boost_btn = Button(
            text=" УСКОРИТЕЛЬ\n(Ур. 1: 1 )",
            size_hint=(None, None),
            size=(190, 85),
            pos_hint={'right': 0.96, 'y': 0.16},
            bold=True,
            font_size='15sp',
            halign='center',
            background_color=(0.95, 0.45, 0.1, 0.95)
        )
        self.boost_btn.bind(on_release=lambda x: self.game.apply_boost())
        self.add_widget(self.boost_btn)

        self.ctrl_panel = FloatLayout(size_hint=(1, 1), opacity=0)

        dpad_size = (80, 80)
        btn_bg = (0.2, 0.6, 0.95, 0.85)

        self.btn_up = Button(text="^", font_size='26sp', bold=True, size_hint=(None, None), size=dpad_size,
                             pos_hint={'x': 0.14, 'y': 0.22}, background_color=btn_bg)
        self.btn_up.bind(on_press=lambda x: self.game.set_move_dir(0, 1),
                         on_release=lambda x: self.game.set_move_dir(0, 0))

        self.btn_down = Button(text="v", font_size='26sp', bold=True, size_hint=(None, None), size=dpad_size,
                               pos_hint={'x': 0.14, 'y': 0.05}, background_color=btn_bg)
        self.btn_down.bind(on_press=lambda x: self.game.set_move_dir(0, -1),
                           on_release=lambda x: self.game.set_move_dir(0, 0))

        self.btn_left = Button(text="<", font_size='26sp', bold=True, size_hint=(None, None), size=dpad_size,
                               pos_hint={'x': 0.04, 'y': 0.135}, background_color=btn_bg)
        self.btn_left.bind(on_press=lambda x: self.game.set_move_dir(-1, 0),
                           on_release=lambda x: self.game.set_move_dir(0, 0))

        self.btn_right = Button(text=">", font_size='26sp', bold=True, size_hint=(None, None), size=dpad_size,
                                pos_hint={'x': 0.24, 'y': 0.135}, background_color=btn_bg)
        self.btn_right.bind(on_press=lambda x: self.game.set_move_dir(1, 0),
                            on_release=lambda x: self.game.set_move_dir(0, 0))

        self.ctrl_panel.add_widget(self.btn_up)
        self.ctrl_panel.add_widget(self.btn_down)
        self.ctrl_panel.add_widget(self.btn_left)
        self.ctrl_panel.add_widget(self.btn_right)
        self.add_widget(self.ctrl_panel)

    def show_confirm_reset_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=15, padding=15)
        lbl = Label(
            text="Вы уверены?\n\nРекорд высоты и уровень ускорения\nбудут сброшены до начальных!",
            font_size='16sp',
            halign='center',
            valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        content.add_widget(lbl)

        btn_box = BoxLayout(spacing=15, size_hint_y=0.4)
        yes_btn = Button(
            text="ДА",
            bold=True,
            font_size='18sp',
            background_color=(0.85, 0.2, 0.2, 1)
        )
        no_btn = Button(
            text="НЕТ",
            bold=True,
            font_size='18sp',
            background_color=(0.25, 0.65, 0.35, 1)
        )

        btn_box.add_widget(yes_btn)
        btn_box.add_widget(no_btn)
        content.add_widget(btn_box)

        popup = Popup(
            title="Подтверждение",
            content=content,
            size_hint=(None, None),
            size=(340, 240),
            auto_dismiss=False
        )

        def on_yes(btn):
            popup.dismiss()
            self.execute_reset()

        def on_no(btn):
            popup.dismiss()

        yes_btn.bind(on_release=on_yes)
        no_btn.bind(on_release=on_no)
        popup.open()

    def execute_reset(self):
        app = App.get_running_app()
        app.boost_level = 1
        app.high_score_alt = 0
        app.save()

        self.restart_flight(None)
        self.update_ui()

    def on_enter(self):
        self.restart_flight(None)

    def activate_space_roam_controls(self):
        self.ctrl_panel.opacity = 1
        self.btn_up.disabled = False
        self.btn_down.disabled = False
        self.btn_left.disabled = False
        self.btn_right.disabled = False

        self.boost_btn.opacity = 0
        self.boost_btn.disabled = True
        self.restart_btn.opacity = 0
        self.restart_btn.disabled = True

        self.alt_lbl.text = " КОСМОС: Летай и собирай монеты! (+10 )"
        self.alt_lbl.color = (1, 0.85, 0.2, 1)

    def deactivate_space_roam_controls(self):
        self.ctrl_panel.opacity = 0
        self.btn_up.disabled = True
        self.btn_down.disabled = True
        self.btn_left.disabled = True
        self.btn_right.disabled = True
        self.boost_btn.opacity = 1
        self.boost_btn.disabled = False

    def update_altitude_label(self, alt):
        self.alt_lbl.text = f" Высота: {int(alt)} км"
        if alt >= 1000.0:
            self.alt_lbl.color = (1, 0.8, 0.2, 1)

    def update_ui(self):
        app = App.get_running_app()
        self.coin_lbl.text = f" {app.coins}"
        self.record_lbl.text = f" Рекорд: {app.high_score_alt} км"

        if app.boost_level >= MAX_BOOST_LEVEL:
            self.boost_btn.text = " УСКОРИТЕЛЬ\n(МАКС. УРОВЕНЬ 10)"
            self.boost_btn.disabled = True
            self.boost_btn.background_color = (0.35, 0.35, 0.38, 0.8)
        else:
            cost = get_boost_upgrade_price(app.boost_level)
            self.boost_btn.disabled = False
            self.boost_btn.text = f" УСКОРИТЕЛЬ\n(Ур. {app.boost_level}: {cost} )"
            self.boost_btn.background_color = (0.95, 0.45, 0.1, 0.95) if app.coins >= cost else (0.4, 0.4, 0.4, 0.8)

    def show_results(self, max_alt, reward, is_new_record):
        self.restart_btn.opacity = 1
        self.restart_btn.disabled = False
        if is_new_record:
            self.alt_lbl.text = f" НОВЫЙ РЕКОРД: {int(max_alt)} км! (+{reward} )"
            self.alt_lbl.color = (1, 0.85, 0.1, 1)
        else:
            self.alt_lbl.text = f"Итог: {int(max_alt)} км (+{reward} )"
        self.update_ui()

    def restart_flight(self, instance):
        self.deactivate_space_roam_controls()
        self.restart_btn.opacity = 0
        self.restart_btn.disabled = True
        self.alt_lbl.color = (0.2, 0.95, 1, 1)
        self.alt_lbl.text = " Натяните рогатку!"
        self.game.reset_positions()
        self.update_ui()


# -------------------------------------------------------------
# 📱 Менеджер экранов и приложение
# -------------------------------------------------------------
class CustomScreenManager(ScreenManager):
    def set_screen(self, name):
        self.current = name


class StreamlitAppPlaceholder:
    """Заглушка, если приложение запущено в окружении Streamlit."""
    pass


class SlingshotApp(App):
    def build(self):
        data = load_game_data()
        self.coins = data.get("coins", 0)
        self.unlocked_skins = data.get("unlocked_skins", [0])
        self.equipped_skin = data.get("equipped_skin", 0)
        self.unlocked_modes = data.get("unlocked_modes", ["mode1"])
        self.selected_mode = data.get("selected_mode", "mode1")
        self.boost_level = min(data.get("boost_level", 1), MAX_BOOST_LEVEL)
        self.high_score_alt = data.get("high_score_alt", 0)

        self.hit_sound = None
        if os.path.exists(SOUND_FILE):
            self.hit_sound = SoundLoader.load(SOUND_FILE)
        elif os.path.exists("fallback_hit.wav"):
            self.hit_sound = SoundLoader.load("fallback_hit.wav")

        self.sm = CustomScreenManager()
        self.sm.add_widget(MenuScreen(name='menu'))
        self.sm.add_widget(GameScreen(name='game'))
        self.sm.add_widget(PyramidGameScreen(name='pyramid_game'))
        self.sm.add_widget(SpaceGameScreen(name='space_game'))
        self.sm.add_widget(ShopScreen(name='shop'))
        return self.sm

    def play_hit_sound(self):
        if self.hit_sound:
            self.hit_sound.stop()
            self.hit_sound.play()

    def on_target_hit(self, reward=1):
        self.coins += reward
        self.save()
        self.play_hit_sound()

        if self.sm.has_screen('game'):
            self.sm.get_screen('game').update_coin_label()
        if self.sm.has_screen('pyramid_game'):
            self.sm.get_screen('pyramid_game').update_coin_label()

    def save(self):
        save_game_data(
            self.coins,
            self.unlocked_skins,
            self.equipped_skin,
            self.unlocked_modes,
            self.selected_mode,
            self.boost_level,
            self.high_score_alt
        )


if __name__ == "__main__":
    SlingshotApp().run()
