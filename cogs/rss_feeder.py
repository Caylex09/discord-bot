from discord.ext import commands, tasks
import discord
import asyncio
from utils.scrapers import parse_rss, parse_luogu


class RSSFeeder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = bot.data_manager  # 引用 bot 实例中的 data_manager
        self.config = bot.config

        # 启动定时任务
        self.rss_loop.start()

    def cog_unload(self):
        self.rss_loop.cancel()

    async def process_feed(self, channel_id, follow_info):
        """处理单个订阅源"""
        feed_type = follow_info["type"]
        results = []  # [(author, articles), ...]

        # 将阻塞的爬虫放入线程池运行
        loop = asyncio.get_running_loop()

        if feed_type in ["cnblogs", "cyx_blogs"]:
            for url in follow_info["url"]:
                # run_in_executor 的第一个参数 None 代表使用默认线程池
                author, articles = await loop.run_in_executor(
                    None,
                    parse_rss,
                    url,
                    self.data.is_url_seen,
                    int(self.config["skip_time"]),
                )
                if articles:
                    results.append((author, articles))
                    # 更新 seen_url
                    for a in articles:
                        self.data.add_url(a["link"])

        elif feed_type == "luogu":
            for uid in follow_info["uid"]:
                # 传入 data_manager 因为 luogu 逻辑稍微复杂需要状态
                author, articles = await loop.run_in_executor(
                    None, parse_luogu, uid, self.data, int(self.config["skip_time"])
                )
                if articles:
                    results.append((author, articles))

        # 发送消息
        if results:
            self.data.save()  # 保存一次状态
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return

            for author, articles in results:
                for a in articles:
                    embed = discord.Embed(
                        title=a["title"],
                        url=a["link"],
                        description=a["summary"],
                        color=0x1ABC9C,
                    )
                    embed.set_author(name=author)
                    embed.set_footer(text=a["time"])
                    await channel.send(embed=embed)

    @tasks.loop(minutes=30)
    async def rss_loop(self):
        print("Starting RSS check...")

        try:
            # 使用 .get("channels", []) 避免 KeyError 导致循环抛出异常而停止
            for ch_config in self.config.get("channels", []):
                ch_id = ch_config["id"]
                for follow in ch_config.get("follow_articles", []):
                    try:
                        await self.process_feed(ch_id, follow)
                    except Exception as e:
                        print(f"Error processing feed in channel {ch_id}: {e}")
        except Exception as e:
            print(f"Critical error in rss_loop: {e}")

        print("RSS check finished.")

    @rss_loop.before_loop
    async def before_rss_loop(self):
        # 推荐将 wait_until_ready 放在 before_loop 中
        await self.bot.wait_until_ready()

    @rss_loop.error
    async def rss_loop_error(self, error):
        # 捕获任务彻底崩溃的异常，方便在控制台中调试
        print(f"Task rss_loop encountered an unhandled error: {error}")

    @commands.command(name="brute")
    async def force_check(self, ctx):
        """手动触发更新 (仅限配置的管理员)"""

        # 1. 寻找当前频道的配置
        current_ch_conf = None
        for ch in self.config.get("channels", []):
            if ch["id"] == ctx.channel.id:
                current_ch_conf = ch
                break

        # 如果当前频道不在配置文件里，直接忽略
        if not current_ch_conf:
            await ctx.reply("❌ 当前频道未配置 RSS 订阅功能。")
            return

        # 2. 权限检查
        # 获取允许的用户列表，默认为空列表 []
        allowed_users = current_ch_conf.get("brute_admin", [])

        # 如果列表为空，或者当前用户不在列表里
        if ctx.author.id not in allowed_users:
            await ctx.reply("🚫 **权限不足**：你没有权限在此频道强制刷新。")
            return

        # --- 权限验证通过，开始执行逻辑 ---

        await ctx.message.add_reaction(self.config["reaction"])
        status_msg = await ctx.reply("🔄 正在强制刷新订阅源...")

        try:
            # 3. 处理 RSS 文章订阅
            article_feeds = current_ch_conf.get("follow_articles", [])
            if article_feeds:
                for follow in article_feeds:
                    await self.process_feed(ctx.channel.id, follow)

            await status_msg.edit(content="✅ 刷新完成。")

        except Exception as e:
            await status_msg.edit(content=f"❌ 刷新过程中出错: {e}")
            print(f"Brute force error: {e}")


async def setup(bot):
    await bot.add_cog(RSSFeeder(bot))
