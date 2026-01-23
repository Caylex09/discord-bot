import discord
from discord.ext import commands
import aiohttp

FABING_API = "https://60s.viki.moe/v2/fabing"


class Fabing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="fa", aliases=["fabing", "crazy"])
    async def fabing(self, ctx, *, target_input: str = None):
        """
        发病文学生成器
        用法:
          !fa               -> 对自己发病
          !fa @某人         -> 对群友发病
          !fa 纸片人老婆    -> 对自定义名字发病
        """

        target_name = ""
        mention_str = ""

        # === 1. 解析目标名字 ===

        # 情况 A: 没输参数 -> 默认是发送者自己
        if target_input is None:
            target_name = ctx.author.display_name
            # 不用专门 mention，reply 默认就会 @

        else:
            # 情况 B: 尝试检查是不是 @某人
            # discord.py 的转换器可以帮我们做这件事，但既然我们要混合输入，手动处理更灵活
            try:
                # 尝试把输入转换成 Member 对象
                converter = commands.MemberConverter()
                member = await converter.convert(ctx, target_input)

                # 如果转换成功，说明用户真的 @ 了一个群友
                target_name = member.display_name
                mention_str = member.mention  # 记录一下，待会儿发消息时 @ 他

            except commands.MemberNotFound:
                # 情况 C: 转换失败，说明用户输入的是普通文字 (例如 "纸片人")
                # 那就直接用这个文字
                target_name = target_input
                mention_str = ""  # 自定义名字就不 @ 谁了

        # === 2. 请求 API ===
        params = {"name": target_name}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(FABING_API, params=params) as resp:
                    if resp.status != 200:
                        await ctx.reply("发病失败，医生正在赶来的路上...")
                        return
                    data = await resp.json()
        except Exception as e:
            await ctx.reply(f"网络错误: {e}")
            return

        if not data or data.get("code") != 200:
            await ctx.reply("API 返回异常。")
            return

        # === 3. 发送消息 ===
        content = data["data"]["saying"]

        # 如果有需要 @ 的人 (mention_str)，加在前面
        if mention_str:
            final_msg = f"{mention_str} {content}"
            # 使用 ctx.send 而不是 reply，避免看起来像是 bot 在回复那个被 @ 的人
            # 或者依然用 reply 回复指令发送者，带上 mention
            await ctx.reply(final_msg)
        else:
            # 普通文字或对自己，直接回复
            await ctx.reply(content)


async def setup(bot):
    await bot.add_cog(Fabing(bot))
