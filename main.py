import discord
from discord.ext import tasks, commands
import os
import dotenv
import sqlite3
import pytz, datetime
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

dotenv.load_dotenv()

bot = discord.Bot(
        intents=discord.Intents.all(),
        activity=discord.Game("5階会計委員会"),
        owner_id=int(os.getenv("OWNER_ID")),
        description="5階会計委員会のBot"
)

TOKEN = str(os.getenv("DISCORD_BOT_TOKEN"))
bot.owner_id = int(os.getenv("OWNER_ID"))
ROLE_ID_5F = int(os.getenv("ROLE_ID"))
CHANNEL_ID_5F = int(os.getenv("CHANNEL_ID"))

class MyModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.add_item(discord.ui.InputText(label="詳細"))
        self.add_item(discord.ui.InputText(label="金額"))
        self.add_item(discord.ui.InputText(label="日付(YYYY-MM-DD)"))

    async def callback(self, interaction: discord.Interaction):
        conn = sqlite3.connect("5F_Block.db")
        embed = discord.Embed(title="入力結果")
        embed.add_field(name="詳細", value=self.children[0].value)
        embed.add_field(name="金額", value=self.children[1].value)
        embed.add_field(name="日付", value=self.children[2].value)
        await interaction.response.send_message(embeds=[embed], ephemeral=True)
        conn.execute(f"INSERT INTO entry (type, details, amount, date) VALUES ('{self.title}', '{self.children[0].value}', {self.children[1].value}, '{self.children[2].value}')")
        conn.commit()
        print("データベースにデータを挿入しました。")
        conn.close()
            

class MyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout of the view must be set to None

    @discord.ui.button(label="収入", custom_id="income_button", style=discord.ButtonStyle.success)
    async def income_button_callback(self, button, interaction):
        self.disable_all_items()
        modal = MyModal(title="収入")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="支出", custom_id="expense_button", style=discord.ButtonStyle.danger)
    async def expense_button_callback(self, button, interaction):
        self.disable_all_items()
        modal = MyModal(title="支出")
        await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    bot.add_view(MyView())
    print(f"Botがログインしました：{bot.user}")

@bot.command(name="entry", description="本人にのみ表示できる入力ボタンを表示します。")
@discord.ext.commands.has_role(ROLE_ID_5F)
async def button(ctx:discord.ApplicationContext):
    user = ctx.user
    await ctx.respond(view= MyView(), ephemeral=True)
    print(f"{user.display_name} が/entryを実行しました。")
    

@bot.command(name="total", description="本人にのみ表示できるブロック費の合計金額を出力します。")
@discord.ext.commands.has_role(ROLE_ID_5F)
async def total(ctx:discord.ApplicationContext):
    user = ctx.user
    conn = sqlite3.connect("5F_Block.db")
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(CASE WHEN type="収入" THEN amount ELSE 0 END) - SUM(CASE WHEN type="支出" THEN amount ELSE 0 END) AS TOTAL FROM "entry";')
    result = cursor.fetchone()
    await ctx.respond(f"Total: {result[0]}", ephemeral=True)
    conn.close()
    print(f"{user.display_name} が/totalを実行しました。")

@bot.command(name="alldata", description="本人にのみ表示できるこれまでのデータ（今年分）をすべて出力します。")
@discord.ext.commands.has_role(ROLE_ID_5F)
async def all_data(ctx:discord.ApplicationContext):
    user = ctx.user
    conn = sqlite3.connect("5F_Block.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entry;')
    rows = cursor.fetchall()
    
    if rows:
        response = "\n".join([f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]}" for row in rows])
    else:
        response = "No data found."
        
    await ctx.respond(response, ephemeral=True)
    conn.close()
    print(f"{user.display_name} が/alldataを実行しました。")

# @bot.command(name="exit", description="ボットを終了します。")
# @commands.is_owner()
# async def exit(ctx):
#     await ctx.respond("Botを終了します。", ephemeral=True)
#     await bot.close()
#     loop.stop()
#     print("Botを終了しました。")
# このコマンドは意味がなくなった
    
# ループ
@tasks.loop(seconds=60)
async def loop():
    now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))    
    if now.hour == 21 and now.minute == 30 and now.date % 5 == 0:
        lchannel = bot.get_channel(CHANNEL_ID_5F)
        await lchannel.send('掃除の時間')
    if now.hour == 22 and now.minute == 00 and (now.date.day == 20 or now.date.day == 5):
        lchannel = bot.get_channel(CHANNEL_ID_5F)
        await lchannel.send('ブロック会議')

loop.start()

bot.run(TOKEN)
# todo
