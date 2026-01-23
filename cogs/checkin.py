import discord
from discord.ext import commands, tasks
import random
import datetime
import asyncio
import io
import matplotlib

# 强制使用非交互式后端，防止报错
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 👇 1. 修改主题为默认 (白底)
plt.style.use("default")
# 如果你想让网格线好看点，可以用这个：
# plt.style.use("seaborn-v0_8-whitegrid")


class CheckIn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = bot.data_manager
        self.daily_summary_task.start()

    def cog_unload(self):
        self.daily_summary_task.cancel()

    def get_today_str(self):
        tz = datetime.timezone(datetime.timedelta(hours=8))
        return datetime.datetime.now(tz).strftime("%Y-%m-%d")

    def get_yesterday_str(self):
        tz = datetime.timezone(datetime.timedelta(hours=8))
        yesterday = datetime.datetime.now(tz) - datetime.timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")

    # --- 画图辅助函数 ---

    def _plot_history(self, dates, rps, username):
        """画个人历史趋势图"""
        fig, ax = plt.subplots(figsize=(10, 5))
        date_objs = [datetime.datetime.strptime(d, "%Y-%m-%d") for d in dates]

        # 线条颜色保持好看的青色
        ax.plot(
            date_objs,
            rps,
            marker="o",
            color="#1ABC9C",
            linestyle="-",
            linewidth=2,
            label="RP Value",
        )
        ax.fill_between(date_objs, rps, color="#1ABC9C", alpha=0.3)

        # 👇 2. 文字颜色改为黑色 (black)
        ax.set_title(
            f"RP History: {username}", fontsize=16, color="black", fontweight="bold"
        )
        ax.set_ylabel("RP Value (0-100)", color="black")

        # 网格线稍微深一点
        ax.grid(True, linestyle="--", alpha=0.5, color="gray")
        ax.set_ylim(0, 105)

        # 设置坐标轴刻度颜色
        ax.tick_params(axis="x", colors="black")
        ax.tick_params(axis="y", colors="black")

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        fig.autofmt_xdate()

        buf = io.BytesIO()
        # 👇 3. 关键：transparent=False, facecolor='white' (强制白底)
        plt.savefig(
            buf, format="png", bbox_inches="tight", transparent=False, facecolor="white"
        )
        buf.seek(0)
        plt.close(fig)
        return buf

    def _plot_rank(self, user_rps, title_text="Today's RP Leaderboard (Top 10)"):
        """画排行榜柱状图"""
        fig, ax = plt.subplots(figsize=(10, 6))

        names = [x[0] for x in user_rps][:10]
        values = [x[1] for x in user_rps][:10]

        colors = [
            "#FFD700" if v == 100 else "#E74C3C" if v < 60 else "#1ABC9C"
            for v in values
        ]

        bars = ax.barh(names, values, color=colors)
        ax.invert_yaxis()

        # 👇 文字颜色改为黑色
        ax.bar_label(bars, padding=3, color="black", fontweight="bold")

        ax.set_title(title_text, fontsize=16, color="black", fontweight="bold")
        ax.set_xlabel("RP Value", color="black")

        ax.tick_params(axis="x", colors="black")
        ax.tick_params(axis="y", colors="black")

        ax.set_xlim(0, 110)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # 只要左边和下边的边框
        ax.spines["left"].set_color("black")
        ax.spines["bottom"].set_color("black")

        buf = io.BytesIO()
        # 👇 强制白底
        plt.savefig(
            buf, format="png", bbox_inches="tight", transparent=False, facecolor="white"
        )
        buf.seek(0)
        plt.close(fig)
        return buf

    # ... (后面的 daily_summary_task 和命令逻辑保持不变) ...
    # 为了完整性，下面是定时任务和命令代码（和之前一样）

    @tasks.loop(time=datetime.time(hour=16, minute=5, tzinfo=datetime.timezone.utc))
    async def daily_summary_task(self):
        await self.bot.wait_until_ready()
        print("⏰ Starting daily RP summary task...")
        yesterday_str = self.get_yesterday_str()
        rank_data = self.data.get_day_rank(yesterday_str)
        if not rank_data:
            return
        plot_data = []
        for uid, rp in rank_data:
            user = self.bot.get_user(int(uid))
            name = user.display_name if user else f"User({uid})"
            plot_data.append((name, rp))
        loop = asyncio.get_running_loop()
        buf = await loop.run_in_executor(
            None, self._plot_rank, plot_data, f"Daily RP Summary: {yesterday_str}"
        )
        image_bytes = buf.getvalue()
        buf.close()
        channels_conf = self.bot.config.get("channels", [])
        for ch in channels_conf:
            if ch.get("rp_total_board") is True:
                channel_id = ch["id"]
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        temp_buf = io.BytesIO(image_bytes)
                        file = discord.File(temp_buf, filename="daily_summary.png")
                        await channel.send(
                            content=f"📅 **昨日人品总结 ({yesterday_str})** 已生成！",
                            file=file,
                        )
                    except Exception as e:
                        print(f"Failed to send summary to {channel_id}: {e}")

    @commands.command(name="sign", aliases=["daka", "clockin"])
    async def sign(self, ctx):
        today = self.get_today_str()
        user_id = ctx.author.id
        existing_rp = self.data.get_user_checkin(user_id, today)
        if existing_rp is not None:
            await ctx.reply(f"你今天已经打过卡了！今日人品值：**{existing_rp}**")
            return
        rp = random.randint(0, 100)
        self.data.add_checkin(user_id, today, rp)
        comment = ""
        if rp == 100:
            comment = "💯 天选之子！"
        elif rp >= 90:
            comment = "✨ 欧皇附体！"
        elif rp >= 60:
            comment = "✅ 运势不错。"
        else:
            comment = "🌚 还是去刷题攒攒人品吧..."
        embed = discord.Embed(title="📅 打卡成功", color=0x1ABC9C)
        embed.add_field(name="日期", value=today, inline=True)
        embed.add_field(name="今日人品 (RP)", value=f"**{rp}**", inline=True)
        embed.set_footer(text=comment)
        await ctx.reply(embed=embed)

    @commands.command(name="rp")
    async def rp_history(self, ctx, member: discord.Member = None):
        target_user = member or ctx.author
        history = self.data.get_user_history(target_user.id)
        if not history:
            await ctx.reply("该用户还没有打卡记录哦。")
            return
        sorted_dates = sorted(history.keys())
        recent_dates = sorted_dates[-7:]
        recent_rps = [history[d] for d in recent_dates]
        await ctx.typing()
        loop = asyncio.get_running_loop()
        buf = await loop.run_in_executor(
            None, self._plot_history, recent_dates, recent_rps, target_user.name
        )
        file = discord.File(buf, filename="history.png")
        await ctx.reply(
            content=f"📊 **{target_user.display_name}** 的人品趋势：", file=file
        )

    @commands.command(name="rank", aliases=["leaderboard"])
    async def rank(self, ctx):
        today = self.get_today_str()
        rank_data = self.data.get_day_rank(today)
        if not rank_data:
            await ctx.reply("今天还没有人打卡呢，快来抢沙发！")
            return
        await ctx.typing()
        plot_data = []
        for uid, rp in rank_data:
            user = self.bot.get_user(int(uid))
            name = user.display_name if user else f"User({uid})"
            plot_data.append((name, rp))
        loop = asyncio.get_running_loop()
        buf = await loop.run_in_executor(None, self._plot_rank, plot_data)
        file = discord.File(buf, filename="rank.png")
        await ctx.reply(content=f"🏆 **{today}** 人品排行榜：", file=file)


async def setup(bot):
    await bot.add_cog(CheckIn(bot))
