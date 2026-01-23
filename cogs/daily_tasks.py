import discord
from discord.ext import commands, tasks
import aiohttp
import datetime

# API 地址
BING_API = "https://60s.viki.moe/v2/bing"
HISTORY_API = "https://60s.viki.moe/v2/today-in-history"
NEWS_API = "https://60s.viki.moe/v2/60s"


class DailyTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 启动定时任务
        self.daily_push_task.start()

    def cog_unload(self):
        self.daily_push_task.cancel()

    async def get_json(self, url):
        """通用异步请求函数"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    # --- 必应壁纸逻辑 ---
    async def send_bing_wallpaper(self):
        data = await self.get_json(BING_API)
        if not data or data.get("code") != 200:
            print("Failed to get Bing wallpaper")
            return

        item = data["data"]

        # 构建 Embed
        embed = discord.Embed(
            title=f"🖼️ {item['title']} - {item['headline']}",
            description=item["description"],
            color=0x0078D7,  # Bing 蓝
            url=item["cover_4k"],  # 点击标题跳转 4K 原图
        )
        embed.set_image(url=item["cover"])  # 使用预览图 (cover)
        embed.set_footer(text=f"{item['copyright']} | {item['update_date']}")

        # 遍历所有频道发送
        for ch_conf in self.bot.config.get("channels", []):
            if ch_conf.get("daily_bing", False):
                channel = self.bot.get_channel(ch_conf["id"])
                if channel:
                    try:
                        await channel.send(embed=embed)
                    except Exception as e:
                        print(f"Failed to send Bing to {channel.id}: {e}")

    # --- 历史上的今天逻辑 ---
    async def send_history_today(self):
        data = await self.get_json(HISTORY_API)
        if not data or data.get("code") != 200:
            print("Failed to get history data")
            return

        today_data = data["data"]
        date_str = f"{today_data['month']}月{today_data['day']}日"

        items = today_data["items"]

        display_items = items

        embed = discord.Embed(
            title=f"📜 历史上的今天 ({date_str})",
            description="回顾历史长河中的今天...",
            color=0x8E44AD,  # 紫色
        )

        for item in display_items:
            # 格式：[年份] 标题
            # 描述太长的话截断一下
            desc = item["description"]
            # if len(desc) > 50:
            #     desc = desc[:50] + "..."

            field_name = f"【{item['year']}】{item['title']}"
            field_value = f"{desc} [详情]({item['link']})"
            embed.add_field(name=field_name, value=field_value, inline=False)

        # if len(items) > 5:
        #     embed.set_footer(text=f"还有 {len(items)-5} 个事件未显示...")

        # 遍历所有频道发送
        for ch_conf in self.bot.config.get("channels", []):
            if ch_conf.get("daily_history", False):
                channel = self.bot.get_channel(ch_conf["id"])
                if channel:
                    try:
                        await channel.send(embed=embed)
                    except Exception as e:
                        print(f"Failed to send History to {channel.id}: {e}")

    async def send_daily_60s(self):
        data = await self.get_json(NEWS_API)
        if not data or data.get("code") != 200:
            print("Failed to get 60s news")
            return

        item = data["data"]
        news_list = item["news"]

        # 1. 整理新闻文本 (加上序号)
        # 即使有图片，把文本放进 Embed description 也是好的，方便复制和搜索
        news_text = ""
        for i, news in enumerate(news_list):
            # 防止文本过长超过 Discord 限制 (4096字符)，虽然一般不会
            if len(news_text) > 3500:
                news_text += f"\n...还有 {len(news_list) - i} 条新闻见下方图片"
                break
            news_text += f"{i+1}. {news}\n"

        # 2. 构建 Embed
        embed = discord.Embed(
            title=f"📰 每天 60 秒读懂世界 ({item['date']} {item['day_of_week']})",
            description=news_text,
            color=0xF1C40F,  # 橙黄色
            url=item["link"],  # 标题跳转微信文章
        )

        # 3. 设置大图 (API 提供的总结图)
        # 如果你觉得图太长占屏幕，可以改成 embed.set_thumbnail(url=item['cover'])
        embed.set_image(url=item["image"])

        # 4. 设置 Footer (每日一句)
        embed.set_footer(text=f"💡 {item['tip']} | 农历 {item['lunar_date']}")

        # 5. 发送
        for ch_conf in self.bot.config.get("channels", []):
            if ch_conf.get("daily_60s", False):  # 👈 检查配置开关
                channel = self.bot.get_channel(ch_conf["id"])
                if channel:
                    try:
                        await channel.send(embed=embed)
                    except Exception as e:
                        print(f"Failed to send 60s News to {channel.id}: {e}")

    # --- 定时任务 ---
    # UTC 16:05 = 北京时间 00:05
    @tasks.loop(time=datetime.time(hour=0, minute=5, tzinfo=datetime.timezone.utc))
    async def daily_push_task(self):
        await self.bot.wait_until_ready()
        print("⏰ Starting Daily Bing & History push...")

        # 执行两个任务
        await self.send_bing_wallpaper()
        await self.send_history_today()
        await self.send_daily_60s()

        print("✅ Daily push finished.")


async def setup(bot):
    await bot.add_cog(DailyTasks(bot))
