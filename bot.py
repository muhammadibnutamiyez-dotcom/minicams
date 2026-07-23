import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import json
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Konfigurasi FFmpeg & yt-dlp yang sudah di-optimize agar tidak error
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
    'options': '-vn -b:a 192k'
}
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

CONFIG_FILE = "voice_config.json"
music_queue = []
is_playing = False

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

def play_next(ctx):
    global is_playing
    if len(music_queue) > 0:
        is_playing = True
        url = music_queue.pop(0)
        
        vc = ctx.guild.voice_client
        if vc and vc.is_connected():
            vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
    else:
        is_playing = False

@bot.event
async def on_ready():
    print(f'Bot {bot.user} berhasil online!')
    try:
        synced = await bot.tree.sync()
        print(f"Berhasil sync {len(synced)} slash commands.")
    except Exception as e:
        print(f"Gagal sync: {e}")
        
    config = load_config()
    if "voice_channel" in config:
        channel = bot.get_channel(config["voice_channel"])
        if channel:
            try:
                await channel.connect()
            except Exception:
                pass

@bot.tree.command(name="setchannel", description="Set default voice channel untuk bot (Owner Only)")
@app_commands.default_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.VoiceChannel):
    config = load_config()
    config["voice_channel"] = channel.id
    save_config(config)
    
    vc = interaction.guild.voice_client
    if vc:
        await vc.move_to(channel)
    else:
        await channel.connect()
        
    await interaction.response.send_message(f"✅ Bot akan *stay* di channel {channel.mention}!", ephemeral=True)

@bot.tree.command(name="help", description="Menampilkan bantuan bot musik")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🎵 ZEMI - MUSIC BOT HELP COMMAND", color=discord.Color.purple())
    embed.add_field(name="!play <link>", value="Memutar musik dari YouTube secara berurutan (Queue).", inline=False)
    embed.add_field(name="!stop", value="Menghentikan musik (menggunakan sistem voting jika ramai di VC).", inline=False)
    embed.add_field(name="!ss <judul>", value="Mencari musik dari teks dan menampilkan 4 hasil dari YouTube.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="play")
async def play(ctx, url: str):
    vc = ctx.guild.voice_client
    if not vc:
        return await ctx.send("❌ Bot belum di-setup ke voice channel. Gunakan `/setchannel` terlebih dahulu.")

    msg = await ctx.send("🔍 Mengambil data lagu...")
    
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        audio_url = data['url']
        title = data.get('title', 'Audio')
        
        music_queue.append(audio_url)
        
        if not is_playing:
            play_next(ctx)
            await msg.edit(content=f"▶️ Sedang memutar: **{title}**")
        else:
            await msg.edit(content=f"📝 Ditambahkan ke antrean: **{title}** (Posisi: {len(music_queue)})")
            
    except Exception as e:
        await msg.edit(content=f"❌ Gagal memutar lagu. Pastikan link valid atau coba gunakan `!ss`.")

class VoteStop(discord.ui.View):
    def __init__(self, required_votes, vc):
        super().__init__(timeout=60)
        self.required_votes = required_votes
        self.voters = set()
        self.vc = vc

    @discord.ui.button(label="Vote Stop", style=discord.ButtonStyle.danger, emoji="🛑")
    async def vote_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.voters:
            return await interaction.response.send_message("Kamu sudah melakukan vote!", ephemeral=True)
            
        self.voters.add(interaction.user.id)
        
        if len(self.voters) >= self.required_votes:
            self.vc.stop()
            global is_playing
            is_playing = False
            music_queue.clear()
            
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(content="🛑 **Voting berhasil!** Musik dihentikan.", view=self)
            self.stop()
        else:
            await interaction.response.send_message(f"Vote diterima! ({len(self.voters)}/{self.required_votes})")

@bot.command(name="stop")
async def stop(ctx):
    vc = ctx.guild.voice_client
    if not vc or not vc.is_playing():
        return await ctx.send("❌ Tidak ada musik yang sedang diputar.")

    members_in_vc = len([m for m in vc.channel.members if not m.bot])
    
    if members_in_vc > 1:
        required_votes = (members_in_vc // 2) + 1
        view = VoteStop(required_votes, vc)
        await ctx.send(f"👥 Ada {members_in_vc} orang di Voice Channel. Butuh **{required_votes} vote** untuk mematikan musik!", view=view)
    else:
        vc.stop()
        global is_playing
        is_playing = False
        music_queue.clear()
        await ctx.send("🛑 Musik dihentikan dan antrean dibersihkan.")

@bot.command(name="ss")
async def ss(ctx, *, query: str):
    msg = await ctx.send(f"🔍 Mencari `{query}` di YouTube...")
    try:
        search_options = {'format': 'bestaudio/best', 'noplaylist': 'True', 'quiet': True, 'extract_flat': True}
        search_ytdl = yt_dlp.YoutubeDL(search_options)
        
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: search_ytdl.extract_info(f"ytsearch4:{query}", download=False))
        
        if 'entries' not in data or len(data['entries']) == 0:
            return await msg.edit(content="❌ Tidak menemukan hasil apa pun.")
            
        embed = discord.Embed(title="🔍 Hasil Pencarian Musik", color=discord.Color.blue())
        for i, entry in enumerate(data['entries']):
            url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
            embed.add_field(name=f"{i+1}. {entry['title']}", value=url, inline=False)
            
        embed.set_footer(text="Gunakan link di atas dengan command !play")
        await msg.edit(content=None, embed=embed)
        
    except Exception as e:
        await msg.edit(content="❌ Terjadi kesalahan saat mencari lagu.")

bot.run(os.getenv("MTUyOTU4NjI4MTE2NjgwMzA0NQ.G3cdei.mDF_SQPF8ZSlotyQkxbOICWOG2zN-uNrJDJ4rA"))