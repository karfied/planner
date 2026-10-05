"""Ежедневник на Kivy. Работает на Android (APK) и на компьютере."""
import json
import os
import uuid
from datetime import date, datetime, timedelta

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import escape_markup

Window.clearcolor = (0.96, 0.96, 0.98, 1)
Window.softinput_mode = "below_target"  # клавиатура не перекрывает поле ввода

WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

KV = """
#:import dp kivy.metrics.dp

<TaskRow>:
    size_hint_y: None
    height: dp(60)
    padding: dp(8)
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
    Button:
        size_hint_x: None
        width: dp(44)
        text: 'OK' if root.done else ''
        background_normal: ''
        background_color: (0.09, 0.64, 0.29, 1) if root.done else (0.85, 0.86, 0.92, 1)
        on_release: app.toggle_task(root.task_id)
    Label:
        size_hint_x: None
        width: dp(56)
        text: root.time or '--'
        bold: True
        color: (0.6, 0.6, 0.65, 1) if root.done else (0.31, 0.27, 0.9, 1)
    Label:
        text: root.text
        markup: True
        color: (0.6, 0.6, 0.65, 1) if root.done else (0.12, 0.14, 0.19, 1)
        text_size: self.width, None
        halign: 'left'
        valign: 'middle'
    Button:
        size_hint_x: None
        width: dp(44)
        text: 'X'
        background_normal: ''
        background_color: 0, 0, 0, 0
        color: 0.55, 0.56, 0.64, 1
        on_release: app.delete_task(root.task_id)

<Root>:
    orientation: 'vertical'
    padding: dp(12)
    spacing: dp(8)
    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(8)
        Button:
            text: '<'
            size_hint_x: None
            width: dp(48)
            on_release: app.shift_day(-1)
        Button:
            text: app.title_text
            bold: True
            font_size: '17sp'
            background_normal: ''
            background_color: 0, 0, 0, 0
            color: 0.12, 0.14, 0.19, 1
            on_release: app.go_today()
        Button:
            text: '>'
            size_hint_x: None
            width: dp(48)
            on_release: app.shift_day(1)
    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(8)
        TextInput:
            id: time_in
            hint_text: '09:00'
            text: '09:00'
            multiline: False
            size_hint_x: None
            width: dp(84)
        TextInput:
            id: text_in
            hint_text: 'Что планируешь?'
            multiline: False
            on_text_validate: app.add_task()
        Button:
            text: '+'
            font_size: '24sp'
            size_hint_x: None
            width: dp(52)
            on_release: app.add_task()
    Label:
        text: app.stat_text
        size_hint_y: None
        height: dp(24)
        color: 0.5, 0.52, 0.6, 1
    ScrollView:
        BoxLayout:
            id: list_box
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(6)
"""


class TaskRow(BoxLayout):
    task_id = StringProperty()
    time = StringProperty()
    text = StringProperty()
    done = BooleanProperty(False)


class Root(BoxLayout):
    pass


class PlannerApp(App):
    title = "Ежедневник"
    title_text = StringProperty()
    stat_text = StringProperty()

    def build(self):
        Builder.load_string(KV)
        self.current = date.today()
        self.data_file = os.path.join(self.user_data_dir, "planner.json")
        self.data = self._load()
        root = Root()
        self.refresh(root)
        return root

    # ---------- данные ----------
    def _load(self):
        try:
            with open(self.data_file, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self):
        self.data = {d: t for d, t in self.data.items() if t}
        tmp = self.data_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.data_file)

    @property
    def key(self):
        return self.current.isoformat()

    def tasks(self):
        return sorted(self.data.get(self.key, []), key=lambda t: t.get("time") or "99:99")

    # ---------- интерфейс ----------
    def refresh(self, root=None):
        root = root or self.root
        box = root.ids.list_box
        box.clear_widgets()
        tasks = self.tasks()
        for t in tasks:
            text = escape_markup(t["text"])
            if t["done"]:
                text = "[s]" + text + "[/s]"
            box.add_widget(TaskRow(task_id=t["id"], time=t.get("time", ""), text=text, done=t["done"]))
        wd = WEEKDAYS[self.current.weekday()]
        today = " (сегодня)" if self.current == date.today() else ""
        self.title_text = f"{self.current:%d.%m.%Y}, {wd}{today}"
        done = sum(1 for t in tasks if t["done"])
        self.stat_text = f"Выполнено {done} из {len(tasks)}" if tasks else "На этот день пока ничего нет"

    def shift_day(self, n):
        self.current += timedelta(days=n)
        self.refresh()

    def go_today(self):
        self.current = date.today()
        self.refresh()

    def add_task(self):
        ids = self.root.ids
        text = ids.text_in.text.strip()
        if not text:
            return
        time = ids.time_in.text.strip()
        try:
            time = datetime.strptime(time, "%H:%M").strftime("%H:%M")
        except ValueError:
            time = ""
        self.data.setdefault(self.key, []).append(
            {"id": uuid.uuid4().hex[:8], "time": time, "text": text, "done": False}
        )
        self._save()
        ids.text_in.text = ""
        self.refresh()

    def toggle_task(self, task_id):
        for t in self.data.get(self.key, []):
            if t["id"] == task_id:
                t["done"] = not t["done"]
        self._save()
        self.refresh()

    def delete_task(self, task_id):
        self.data[self.key] = [t for t in self.data.get(self.key, []) if t["id"] != task_id]
        self._save()
        self.refresh()


if __name__ == "__main__":
    PlannerApp().run()
