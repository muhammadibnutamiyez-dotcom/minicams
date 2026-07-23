import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# Sistem Antrean & Status
music_queue = []
is_playing = False

def play_next(ctx):
    global is_playing
    if len(music_queue) > 0:
        is_playing = True
        next_url, next_title = music_queue.pop(0)
        
        vc = ctx.guild.voice_client
        if vc and vc.is_connected():
            try:
                source = discord.FFmpegPCMAudio(next_url, **FFMPEG_OPTIONS)
                vc.play(source, after=lambda e: play_next(ctx))
                # Kirim pesan sedang memutar lagu berikutnya
                asyncio.run_coroutine_threadsafe(ctx.send(f"▶️ Memutar lagu berikutnya: **{next_title}**"), bot.loop)
            except Exception as e:
                print(f"Error play_next: {e}")
                play_next(ctx)
    else:
        is_playing = False

@bot.event
async def on_ready():
    print(f'Bot {bot.user} berhasil online!')

@bot.command(name="play")
async def play(ctx, *, query: str):
    global is_playing
    if not ctx.author.voice:
        return await ctx.send("❌ Kamu harus masuk ke Voice Channel terlebih dahulu!")
    
    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client

    if not vc:
        vc = await channel.connect()
    elif vc.channel != channel:
        await vc.move_to(channel)

    msg = await ctx.send("🔍 Mengambil data lagu...")

    try:
        data = ytdl.extract_info(query if "http" in query else f"ytsearch:{query}", download=False)
        
        if 'entries' in data:
            data = data['entries'][0]
            
        audio_url = data['url']
        title = data.get('title', 'Audio')

        if not is_playing:
            is_playing = True
            music_queue.append((audio_url, title))
            
            # Ambil item pertama dan langsung putar
            current_url, current_title = music_queue.pop(0)
            source = discord.FFmpegPCMAudio(current_url, **FFMPEG_OPTIONS)
            vc.play(source, after=lambda e: play_next(ctx))
            
            await msg.edit(content=f"▶️ Sedang memutar: **{current_title}**")
        else:
            music_queue.append((audio_url, title))
            await msg.edit(content=f"📝 Ditambahkan ke antrean: **{title}** (Posisi antrean: {len(music_queue)})")
            
    except Exception as e:
        print(f"ERROR PLAY: {e}")
        await msg.edit(content=f"❌ Gagal memutar lagu. Pastikan link valid atau coba gunakan `!ss`.")

# Fitur Vote Stop
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
            await interaction.response.edit_message(content="🛑 **Voting berhasil!** Musik dihentikan dan antrean dikosongkan.", view=self)
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
    msg = await ctx.send(f"🔍 Mencari `{query}`...")
    try:
        data = ytdl.extract_info(f"ytsearch4:{query}", download=False)
        if 'entries' not in data or len(data['entries']) == 0:
            return await msg.edit(content="❌ Tidak ditemukan.")
            
        embed = discord.Embed(title="🔍 Hasil Pencarian", color=discord.Color.blue())
        for i, entry in enumerate(data['entries']):
            url = f"https://www.youtube.com/watch?v={entry.get('id')}"
            embed.add_field(name=f"{i+1}. {entry['title']}", value=url, inline=False)
            
        embed.set_footer(text="Gunakan link di atas dengan command !play")
        await msg.edit(content=None, embed=embed)
    except Exception as e:
        await msg.edit(content=f"❌ Error pencarian: {e}")

bot.run(os.getenv("BOT_TOKEN"))
