from discord.ext import commands
import discord


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1️⃣ 监听：只发了一个前缀（例如 "!"）
    @commands.Cog.listener()
    async def on_message(self, message):
        # 排除 Bot 自己的消息，防止死循环
        if message.author.bot:
            return

        # 读取配置
        prefix = self.bot.config["prefix"]
        reaction = self.bot.config["reaction"]

        # 判断：如果消息内容去空格后，正好等于前缀
        if message.content.strip() == prefix:
            try:
                # 1. 贴表情
                await message.add_reaction(reaction)
                # 2. 回复表情
                await message.reply(reaction)
            except discord.HTTPException:
                pass

    # 2️⃣ 监听：有效的指令（例如 "!ping"）
    @commands.Cog.listener()
    async def on_command(self, ctx):
        # 只要是指令，先贴个表情再说
        try:
            reaction = self.bot.config["reaction"]
            await ctx.message.add_reaction(reaction)
        except discord.HTTPException:
            pass

    # 3️⃣ 监听：指令执行过程中的错误
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        reaction = self.bot.config["reaction"]
        await ctx.message.add_reaction(reaction)

        # 情况 1: 指令不存在
        if isinstance(error, commands.CommandNotFound):
            try:

                await ctx.reply("未知命令")
            except:
                pass

        # 👇 情况 2: 找不到指定的用户 (MemberNotFound)
        # 当你输入 !rp milmon，系统找不到 milmon 这个人时触发
        elif isinstance(error, commands.MemberNotFound):
            # error.argument 会包含导致错误的那个输入（即 "milmon"）
            await ctx.reply(
                f"❌ 找不到用户 **{error.argument}**。\n请检查拼写，或尝试使用 `@提及` 对方。"
            )

        # 👇 情况 3: 其他参数错误 (BadArgument)
        # 比如要求输入数字却输入了文字
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ 参数格式错误，请检查你的输入。")

        # 情况 4: 缺少必要的参数
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"❌ 缺少必要参数：`{error.param.name}`")

        # 其他未知的严重错误，打印到控制台方便调试
        else:
            print(f"⚠️ 指令异常: {error}")

    # --- 下面是具体的命令逻辑 ---

    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.reply(f"Pong! Latency: {round(self.bot.latency * 1000)}ms")

    @commands.command(name="help")
    async def help_command(self, ctx):
        cfg = self.bot.config
        msg = cfg["help_message"].format(prefix=cfg["prefix"])
        await ctx.reply(msg)


async def setup(bot):
    await bot.add_cog(General(bot))
