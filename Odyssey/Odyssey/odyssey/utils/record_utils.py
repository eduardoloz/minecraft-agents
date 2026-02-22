import time
import os

from .file_utils import *
from .json_utils import *
from .logger import get_logger

class EventRecorder:
    def __init__(
        self,
        ckpt_dir="ckpt",
        resume=False,
        init_position=None,
    ):
        self.logger = get_logger("EventRecorder")
        self.ckpt_dir = ckpt_dir
        self.item_history = set()
        self.item_vs_time = {}
        self.item_vs_iter = {}
        self.biome_history = set()
        self.init_position = init_position
        self.position_history = [[0, 0]]
        self.elapsed_time = 0
        self.iteration = 0
        f_mkdir(self.ckpt_dir, "events")
        if resume:
            self.resume()

    def record(self, events, task):
        task = re.sub(r'[\\/:"*?<>| ]', "_", task)
        task = task.replace(" ", "_") + time.strftime(
            "_%Y%m%d_%H%M%S", time.localtime()
        )
        self.iteration += 1
        if not self.init_position:
            self.init_position = [
                events[0][1]["status"]["position"]["x"],
                events[0][1]["status"]["position"]["z"],
            ]
        for event_type, event in events:
            self.update_items(event)
            if event_type == "observe":
                self.update_elapsed_time(event)
        
        
        self.logger.info(f"****Recorder message: {self.elapsed_time} ticks have elapsed****")
        self.logger.info(f"****Recorder message: {self.iteration} iteration passed****")
        dump_json(events, f_join(self.ckpt_dir, "events", task))
        return self.elapsed_time, self.iteration

    def resume(self, cutoff=None):
        self.item_history = set()
        self.item_vs_time = {}
        self.item_vs_iter = {}
        self.elapsed_time = 0
        self.position_history = [[0, 0]]

        def get_timestamp(string):
            timestamp = "_".join(string.split("_")[-2:])
            return time.mktime(time.strptime(timestamp, "%Y%m%d_%H%M%S"))

        records = f_listdir(self.ckpt_dir, "events")
        sorted_records = sorted(records, key=get_timestamp)
        for record in sorted_records:
            self.iteration += 1
            if cutoff and self.iteration > cutoff:
                break
            events = load_json(f_join(self.ckpt_dir, "events", record))
            if not self.init_position:
                self.init_position = (
                    events[0][1]["status"]["position"]["x"],
                    events[0][1]["status"]["position"]["z"],
                )
            for event_type, event in events:
                self.update_items(event)
                self.update_position(event)
                if event_type == "observe":
                    self.update_elapsed_time(event)

    def update_items(self, event):
        inventory = event["inventory"]
        elapsed_time = event["status"]["elapsedTime"]
        biome = event["status"]["biome"]
        items = set(inventory.keys())
        new_items = items - self.item_history
        self.item_history.update(items)
        self.biome_history.add(biome)
        if new_items:
            if self.elapsed_time + elapsed_time not in self.item_vs_time:
                self.item_vs_time[self.elapsed_time + elapsed_time] = []
            self.item_vs_time[self.elapsed_time + elapsed_time].extend(new_items)
            if self.iteration not in self.item_vs_iter:
                self.item_vs_iter[self.iteration] = []
            self.item_vs_iter[self.iteration].extend(new_items)

    def update_elapsed_time(self, event):
        self.elapsed_time += event["status"]["elapsedTime"]

    def update_position(self, event):
        position = [
            event["status"]["position"]["x"] - self.init_position[0],
            event["status"]["position"]["z"] - self.init_position[1],
        ]
        if self.position_history[-1] != position:
            self.position_history.append(position)


class BotActivityRecorder:
    """Simple recorder that parses the Minecraft server log for a particular bot's
    join/leave events.

    The class maintains an in-memory list of events and can persist them as JSON
    under a checkpoint directory.  It is intentionally lightweight for the
    current requirement and only looks for the strings ``"<name> joined the
    game"`` and ``"<name> left the game"`` (or ``"lost connection"``).

    Example::

        recorder = BotActivityRecorder()
        recorder.scan_log("bot")                    # scan entire file once
        # or repeatedly call scan_log() in a loop to tail
    """

    def __init__(
        self,
        log_path="server-setup/data/logs/latest.log",
        ckpt_dir="ckpt",
        bot_name=None,
    ):
        self.logger = get_logger("BotActivityRecorder")
        self.log_path = log_path
        self.ckpt_dir = ckpt_dir
        self.bot_name = bot_name
        # events will be a list of dicts with keys: time, type, raw_line
        self.events = []
        # track file offset so we only read new lines during a tail
        self._offset = 0
        f_mkdir(self.ckpt_dir, "activity")
        if self.bot_name:
            # perform initial scan if bot name was provided
            self.scan_log(self.bot_name)

    def _parse_line(self, line: str, bot_name: str):
        # normalize whitespace
        text = line.strip()
        if f"{bot_name} joined the game" in text:
            return {"type": "join", "time": time.time(), "line": text}
        if f"{bot_name} left the game" in text or f"{bot_name} lost connection" in text:
            return {"type": "leave", "time": time.time(), "line": text}
        return None

    def scan_log(self, bot_name: str = None):
        """Scan the log file from the last read position for matching events.

        If ``bot_name`` is provided it overrides the one stored on the instance.
        """
        if bot_name:
            self.bot_name = bot_name
        if not self.bot_name:
            raise ValueError("bot_name must be set before scanning log")

        try:
            with open(self.log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._offset)
                for line in f:
                    evt = self._parse_line(line, self.bot_name)
                    if evt is not None:
                        self.events.append(evt)
                self._offset = f.tell()
        except FileNotFoundError:
            self.logger.error(f"Log file not found: {self.log_path}")
            return []

        # write out the activity so far
        dump_json(self.events, f_join(self.ckpt_dir, "activity", "bot_activity.json"))
        return self.events

    def reset(self):
        """Clear recorded events and reset offset."""
        self.events = []
        self._offset = 0
        activity_file = f_join(self.ckpt_dir, "activity", "bot_activity.json")
        try:
            os.remove(activity_file)
        except Exception:
            pass
