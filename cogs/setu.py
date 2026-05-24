import discord
from discord.ext import commands
import aiohttp


class Setu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_channel_config(self, channel_id):
        for ch in self.bot.config.get("channels", []):
            if ch["id"] == channel_id:
                return ch
        return None

    @commands.command(name="setu")
    async def setu(self, ctx):
        # 1. 检查配置
        ch_conf = self.get_channel_config(ctx.channel.id)
        if not ch_conf or not ch_conf.get("setu", False):
            await ctx.reply("❌ 本频道未开启涩图功能。")
            return

        # 2. 准备参数
        r18_mode = ch_conf.get("r18", 0)  # 0:非R18, 1:R18, 2:混合
        params = {"r18": r18_mode, "aiType": 1}  # aiType = 1 无 AI
        url = "https://api.lolicon.app/setu/v2"

        # 3. 请求 API
        await ctx.typing()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        await ctx.reply(f"API 请求失败: {resp.status}")
                        return
                    data = await resp.json()
        except Exception as e:
            await ctx.reply(f"网络错误: {e}")
            return

        # 4. 检查数据
        if data.get("error"):
            await ctx.reply(f"API 返回错误: {data['error']}")
            return
        if not data.get("data"):
            await ctx.reply("没找到图，换个姿势试试？")
            return

        # 5. 解析第一张图
        img_data = data["data"][0]
        pid = img_data["pid"]
        title = img_data["title"]
        author = img_data["author"]
        tags = img_data["tags"]
        # API 默认返回的是 i.pixiv.re 的代理链接，Discord 可以直接显示
        img_url = img_data["urls"]["original"]
        # 更新：API 代理链接挂了
        img_url = img_url.replace("i.pixiv.re", "i.muxmus.com")
        is_r18 = img_data.get("r18", False)

        # 6. 构建 Embed
        color = 0xFF69B4 if is_r18 else 0x3498DB
        embed = discord.Embed(
            title=title, url=f"https://www.pixiv.net/artworks/{pid}", color=color
        )
        embed.set_author(
            name=f"Artist: {author}",
            url=f"https://www.pixiv.net/users/{img_data['uid']}",
        )
        tag_str = ", ".join(tags)[:100]
        embed.add_field(name="Tags", value=tag_str, inline=False)

        # 🟢 最终逻辑判断
        # 只有 R18 才下载并遮罩，普通图依然秒发 URL
        need_spoiler = is_r18 or ("R-18" in tags)

        if need_spoiler:
            # R18：下载 -> 遮罩上传
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(img_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            from io import BytesIO

                            # 只要文件名带 SPOILER_，Discord 就会加遮罩
                            f = discord.File(BytesIO(data), filename="SPOILER_setu.png")
                            # 图片不放 Embed 里，而是作为附件
                            await ctx.reply(embed=embed, file=f)
                        else:
                            await ctx.reply("图片加载失败")
            except:
                await ctx.reply("下载出错，请重试")
        else:
            # 非R18：秒发 URL
            # embed.set_image(url=img_url)
            # await ctx.reply(embed=embed)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(img_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            from io import BytesIO

                            f = discord.File(BytesIO(data), filename="SPOILER_setu.png")
                            # 图片不放 Embed 里，而是作为附件
                            await ctx.reply(embed=embed, file=f)
                        else:
                            await ctx.reply("图片加载失败")
            except:
                await ctx.reply("下载出错，请重试")


async def setup(bot):
    await bot.add_cog(Setu(bot))
