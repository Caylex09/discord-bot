# main.py
import discord
import asyncio
import datetime  # 引入时间库
from discord.ext import commands
from utils.config_loader import load_config
from utils.data_manager import DataManager

cfg = load_config()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class MyBot(commands.Bot):
    def __init__(self):
        proxy = cfg.get("proxy")

        kwargs = dict(
            command_prefix=cfg["prefix"],
            intents=intents,
            help_command=None,
        )

        if proxy:  # 只有本地调试时才会进来
            kwargs["proxy"] = proxy

        super().__init__(**kwargs)

        self.config = cfg
        self.data_manager = DataManager()
        self.has_sent_startup_report = False

    async def setup_hook(self):
        await self.load_extension("cogs.general")
        await self.load_extension("cogs.rss_feeder")
        await self.load_extension("cogs.checkin")
        await self.load_extension("cogs.setu")
        await self.load_extension("cogs.daily_tasks")
        await self.load_extension("cogs.fabing")

    async def on_ready(self):
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})")

        # 👇 发送上线报告的逻辑
        if not self.has_sent_startup_report:
            await self.send_startup_report()
            self.has_sent_startup_report = True

        print("------")

    async def send_startup_report(self):
        """发送上线报告的具体逻辑"""
        # 1. 统计一下监控了多少个源 (可选，为了报告看起来更高级)
        total_channels = len(self.config["channels"])
        # total_feeds = sum(
        #     len(ch.get("follow_articles", "")) for ch in self.config["channels"]
        # )

        total_commands = len(self.commands)

        # 2. 制作一个漂亮的 Embed
        embed = discord.Embed(
            title="Bot 上线通知",
            description="Bot 已成功连接。",
            color=0x2ECC71,  # 绿色
            timestamp=datetime.datetime.now(),
        )
        embed.add_field(name="监控频道数", value=str(total_channels), inline=True)
        # embed.add_field(name="订阅源总数", value=str(total_feeds), inline=True)
        embed.add_field(name="支持指令数", value=str(total_commands), inline=True)
        embed.add_field(
            name="当前延迟", value=f"{round(self.latency * 1000)}ms", inline=True
        )
        embed.set_footer(text="https://github.com/Caylex09/discord-bot")

        # 3. 遍历配置文件里的频道并发送
        for ch_conf in self.config["channels"]:
            channel_id = ch_conf["id"]
            channel = self.get_channel(channel_id)
            if channel:
                if ch_conf.get("send_message", False) == True:
                    try:
                        await channel.send(embed=embed)
                        print(f"Sent startup report to channel {channel_id}")
                    except discord.Forbidden:
                        print(f"Error: No permission to send in channel {channel_id}")
            else:
                print(
                    f"Warning: Could not find channel {channel_id} (Bot might not be in that server)"
                )


async def main():
    bot = MyBot()
    async with bot:
        await bot.start(cfg["token"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
