import discord
from discord.ext import commands
from discord.ui import View, UserSelect, Button
import os
from flask import Flask
from threading import Thread

# ==========================================
# 設定エリア
# ==========================================
# クラウド上ではトークンを直接コードに書くのは危険なため、環境変数から読み込みます。
# ローカルでテストする場合は、下の TOKEN = "..." のコメントアウトを外して使ってください。
# TOKEN = "ここにあなたのBOTトークンを貼り付けてください" 
CHANNEL_NAME_BOT = "bot"
CHANNEL_NAME_ANNOUNCE = "迷子のお知らせ" 
# ==========================================

# ------------------------------------------
# Botを24時間稼働させるためのWebサーバー機能 (Keep Alive)
# ------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    # Renderなどのクラウドではポート指定が必要な場合があるため 0.0.0.0 で待機
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------------------------

# 権限設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(PersistentCallView())

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.deploy_persistent_button()

    async def deploy_persistent_button(self):
        for guild in self.guilds:
            target_channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME_BOT)
            
            if target_channel:
                try:
                    has_button = False
                    async for message in target_channel.history(limit=10):
                        if message.author == self.user and message.components:
                            has_button = True
                            break

                    if not has_button:
                        await target_channel.send("以下のボタンを押して呼び出しを開始してください。", view=PersistentCallView())
                        print(f"[{guild.name}] ボタンを設置しました。")
                    else:
                        print(f"[{guild.name}] 既にボタンがあります。")

                except discord.Forbidden:
                    print(f"[{guild.name}] 🔴エラー: 権限不足")
                except Exception as e:
                    print(f"[{guild.name}] 🔴予期せぬエラー: {e}")

# ------------------------------------------
# UI部品 (変更なし)
# ------------------------------------------
class MemberSelectView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.user_select = UserSelect(
            placeholder="呼び出すメンバーを選択してください（複数可）",
            min_values=1,
            max_values=25,
            row=0
        )
        self.user_select.callback = self.select_callback
        self.add_item(self.user_select)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

    @discord.ui.button(label="送信", style=discord.ButtonStyle.green, row=1)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        selected_users = self.user_select.values
        if not selected_users:
            await interaction.response.send_message("メンバーが選択されていません。", ephemeral=True)
            return

        mentions = " ".join([user.mention for user in selected_users])
        sender = interaction.user.mention
        message_content = f"{mentions}\n{sender} さんがお呼びです。ボイスチャンネルにお越しください。"
        
        announce_channel = discord.utils.get(interaction.guild.text_channels, name=CHANNEL_NAME_ANNOUNCE)

        if announce_channel:
            try:
                await announce_channel.send(message_content)
                await interaction.response.send_message(f"{len(selected_users)}名の呼び出しを送信しました。", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("エラー: 書き込み権限がありません。", ephemeral=True)
        else:
            await interaction.response.send_message(f"エラー: '{CHANNEL_NAME_ANNOUNCE}' が見つかりません。", ephemeral=True)

class PersistentCallView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="呼出", style=discord.ButtonStyle.primary, custom_id="persistent_view:call_button")
    async def call_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "呼び出したいメンバーを選択し、「送信」を押してください。", 
            view=MemberSelectView(), 
            ephemeral=True
        )

# Botの起動処理
bot = Bot()

if __name__ == "__main__":
    # Webサーバー機能を起動
    keep_alive()
    
    # 環境変数からトークンを取得して起動
    token = os.getenv("DISCORD_TOKEN")
    
    # 環境変数がない場合（ローカルテスト用）はコード内の設定を使ってみる
    if not token and 'TOKEN' in globals():
        token = TOKEN
        
    if token:
        try:
            bot.run(token)
        except Exception as e:
            print(f"エラー: {e}")
    else:
        print("エラー: Botトークンが見つかりません。環境変数 DISCORD_TOKEN を設定してください。")