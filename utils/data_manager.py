import json
import os
from datetime import datetime


class DataManager:
    def __init__(
        self,
        url_file="data/seen_url.json",
        luogu_file="data/seen_luogu.json",
        checkin_file="data/checkins.json",
    ):
        self.url_file = url_file
        self.luogu_file = luogu_file
        self.checkin_file = checkin_file  # 新增：打卡数据文件

        self.seen_urls = self._load_json(url_file, default=[])
        self.seen_urls_set = set(self.seen_urls)
        self.seen_luogu = self._load_json(luogu_file, default={})
        self.checkins = self._load_json(checkin_file, default={})  # 新增：加载打卡数据

    def _load_json(self, filepath, default):
        if not os.path.exists(filepath):
            return default
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def save(self):
        # 原有的保存逻辑...
        os.makedirs(os.path.dirname(self.url_file), exist_ok=True)
        with open(self.url_file, "w", encoding="utf-8") as f:
            json.dump(list(self.seen_urls_set), f, ensure_ascii=False, indent=2)
        with open(self.luogu_file, "w", encoding="utf-8") as f:
            json.dump(self.seen_luogu, f, ensure_ascii=False, indent=2)

        # 新增：保存打卡数据
        with open(self.checkin_file, "w", encoding="utf-8") as f:
            json.dump(self.checkins, f, ensure_ascii=False, indent=2)

    # --- 原有的 RSS 相关方法 ---
    def is_url_seen(self, url):
        return url in self.seen_urls_set

    def add_url(self, url):
        self.seen_urls_set.add(url)

    def get_luogu_count(self, uid):
        return self.seen_luogu.get(str(uid), 0)

    def set_luogu_count(self, uid, count):
        self.seen_luogu[str(uid)] = count

    # --- 新增：打卡相关方法 ---
    def add_checkin(self, user_id, date_str, rp_value):
        uid = str(user_id)
        if uid not in self.checkins:
            self.checkins[uid] = {}
        self.checkins[uid][date_str] = rp_value
        self.save()

    def get_user_checkin(self, user_id, date_str):
        """获取某用户某天的RP，没打卡返回 None"""
        return self.checkins.get(str(user_id), {}).get(date_str)

    def get_user_history(self, user_id):
        """获取用户所有历史数据"""
        return self.checkins.get(str(user_id), {})

    def get_day_rank(self, date_str):
        """获取某天所有人的数据，返回 [(uid, rp), ...]"""
        rank = []
        for uid, dates in self.checkins.items():
            if date_str in dates:
                rank.append((uid, dates[date_str]))
        # 按 RP 从大到小排序
        rank.sort(key=lambda x: x[1], reverse=True)
        return rank
