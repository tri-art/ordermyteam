import discord
from discord.ext import commands
from discord.ui import View, UserSelect, Button
import os
import sys
from flask import Flask
from threading import Thread

# ==========================================
# 設定エリア
# ==========================================
CHANNEL_NAME_BOT = "bot"
CHANNEL_NAME_ANNOUNCE = "迷子のお知らせ" 
# ==========================================

# ログを強制的に表示させるための設定
def log(message):
    print(f"[LOG] {message}", flush=True)

# ------------------------------------------
# Webサーバー機能 (Keep Alive)
# ------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ------------------------------------------
# Bot本体
# ------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(PersistentCallView())

    async def on_ready(self):
        log(f'ログイン成功: {self.user} (ID: {self.user.id})')
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
                        log(f"[{guild.name}] ボタンを設置しました。")
                    else:
                        log(f"[{guild.name}] 既にボタンがあります。")
                except Exception as e:
                    log(f"[{guild.name}] エラー: {e}")
            else:
                log(f"[{guild.name}] チャンネル '{CHANNEL_NAME_BOT}' が見つかりません。")

# ------------------------------------------
# UI部品
# ------------------------------------------
class MemberSelectView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.user_select = UserSelect(
            placeholder="呼び出すメンバーを選択してください",
            min_values=1, max_values=25, row=0
        )
        self.user_select.callback = self.select_callback
        self.add_item(self.user_select)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

    @discord.ui.button(label="送信", style=discord.ButtonStyle.green, row=1)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        selected_users = self.user_select.values
        if not selected_users:
            await interaction.response.send_message("メンバー未選択です。", ephemeral=True)
            return

        mentions = " ".join([user.mention for user in selected_users])
        sender = interaction.user.mention
        message_content = f"{mentions}\n{sender} さんがお呼びです。ボイスチャンネルにお越しください。"
        
        announce_channel = discord.utils.get(interaction.guild.text_channels, name=CHANNEL_NAME_ANNOUNCE)
        if announce_channel:
            try:
                await announce_channel.send(message_content)
                await interaction.response.send_message(f"送信完了しました。", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("エラー: 書き込み権限なし", ephemeral=True)
        else:
            await interaction.response.send_message(f"エラー: 通知先チャンネル不明", ephemeral=True)

class PersistentCallView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="呼出", style=discord.ButtonStyle.primary, custom_id="persistent_view:call_button")
    async def call_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("メンバーを選択してください。", view=MemberSelectView(), ephemeral=True)

# ------------------------------------------
# メイン処理
# ------------------------------------------
bot = Bot()

if __name__ == "__main__":
    log("システム起動開始...")
    
    # 1. Webサーバー起動
    try:
        keep_alive()
        log("Webサーバー起動成功")
    except Exception as e:
        log(f"Webサーバー起動エラー: {e}")

    # 2. トークン確認
    token = os.getenv("DISCORD_TOKEN")
    
    if token:
        log("トークンが見つかりました。Botへログインを試みます...")
        try:
            bot.run(token)
        except Exception as e:
            log(f"Botログインエラー: {e}")
            log("トークンが正しいか、Bot設定のIntentが許可されているか確認してください。")
    else:
        log("【重要】エラー: 環境変数 DISCORD_TOKEN が設定されていません！RenderのEnvironment設定を確認してください。")
