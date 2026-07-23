import asyncio
import os
import random
import sqlite3
import discord
from discord.ext import commands

# Inisialisasi Database SQLite
db = sqlite3.connect("database.db")
cursor = db.cursor()

# Buat tabel jika belum ada
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    chips INTEGER DEFAULT 0,
    money INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    banned INTEGER DEFAULT 0,
    ban_reason TEXT DEFAULT ''
)
"""
)
db.commit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Active multiplayer challenges
active_challenges = {}


def get_user(user_id, username=""):
  cursor.execute(
      "SELECT chips, money, level, exp, banned, ban_reason FROM users WHERE"
      " user_id = ?",
      (str(user_id),),
  )
  result = cursor.fetchone()
  if not result:
    cursor.execute(
        "INSERT INTO users (user_id, username, chips, money) VALUES (?, ?, 0,"
        " 0)",
        (str(user_id), username),
    )
    db.commit()
    return [0, 0, 1, 0, 0, ""]
  return result


def update_user(user_id, chips, money, level, exp):
  cursor.execute(
      "UPDATE users SET chips = ?, money = ?, level = ?, exp = ? WHERE"
      " user_id = ?",
      (chips, money, level, exp, str(user_id)),
  )
  db.commit()


@bot.event
async def on_ready():
  print(f"Bot Berhasil Online sebagai {bot.user}")


# 1. REGISTER
@bot.hybrid_command(
    name="register", description="Daftar akun baru blackjack dan dapat 40 chip!"
)
async def register(ctx):
  user_id = str(ctx.author.id)
  cursor.execute("SELECT chips FROM users WHERE user_id = ?", (user_id,))
  res = cursor.fetchone()
  if res:
    await ctx.send("❌ Kamu sudah terdaftar di database Blackjack!")
    return

  cursor.execute(
      "INSERT INTO users (user_id, username, chips, money, level) VALUES (?,"
      " ?, 40, 0, 1)",
      (user_id, ctx.author.name),
  )
  db.commit()
  await ctx.send(
      f"✅ Berhasil registrasi, {ctx.author.mention}! Kamu mendapatkan bonus awal"
      " **40 Chip** 🎉"
  )


# 2. HELP
@bot.hybrid_command(name="help", description="Menampilkan daftar perintah bot")
async def help_cmd(ctx):
  embed = discord.Embed(
      title="🃏 Bantuan Menu - Blackjack Beta Bot",
      color=discord.Color.gold(),
  )
  embed.add_field(
      name="Perintah Utama",
      value=(
          "`/register` - Daftar akun baru (Bonus 40 Chip)\n`!dailybonus` -"
          " Klaim 10 chip harian\n`!cekme` - Lihat profil lengkap & saldo\n`!toko"
          " shopee` - Toko item eksklusif"
      ),
      inline=False,
  )
  embed.add_field(
      name="Perintah Game & Transaksi",
      value=(
          "`!blackjack <bet>` - Main Blackjack vs Dealer (Min bet 5 chip)\n`!multiplayer"
          " @user` - Tantang teman main\n`!terima` - Terima tantangan duel\n`!transferchip"
          " @user <jumlah>` - Transfer chip (Min 5, Max 1000)\n`!tukarchip"
          " <jumlah>` - Tukar chip jadi uang (1 chip = Rp5.000, pajak 500"
          " perak)"
      ),
      inline=False,
  )
  embed.add_field(
      name="Perintah Admin (Khusus Admin)",
      value=(
          "`!setcoin`, `!resetcoin`, `!setuang`, `!resetuang`, `!setlevel`,"
          " `!banakun`, `!unban`"
      ),
      inline=False,
  )
  await ctx.send(embed=embed)


# DAILY BONUS
@bot.command()
async def dailybonus(ctx):
  user_id = str(ctx.author.id)
  data = get_user(user_id, ctx.author.name)
  if data[4] == 1:
    return await ctx.send("❌ Akun kamu di-banned!")

  chips, money, level, exp, banned, reason = data
  update_user(user_id, chips + 10, money, level, exp)
  await ctx.send(
      f"🎁 {ctx.author.mention} Berhasil klaim bonus harian **10 Chip**!"
  )


# CEKME
@bot.command()
async def cekme(ctx, member: discord.Member = None):
  target = member or ctx.author
  data = get_user(target.id, target.name)
  chips, money, level, exp, banned, reason = data

  embed = discord.Embed(
      title=f"📊 Profil Blackjack - {target.name}",
      color=discord.Color.blue(),
  )
  embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
  embed.add_field(name="Username Discord", value=target.name, inline=True)
  embed.add_field(name="ID Discord", value=target.id, inline=True)
  embed.add_field(name="Total Chip", value=f"🪙 {chips}", inline=True)
  embed.add_field(name="Uang (Rupiah)", value=f"Rp {money:,}", inline=True)
  embed.add_field(name="Level", value=f"⭐ {level} (Exp: {exp})", inline=True)
  if banned:
    embed.add_field(name="Status", value=f"🔴 BANNED ({reason})", inline=False)
  await ctx.send(embed=embed)


# TRANSFER CHIP
@bot.command()
async def transferchip(ctx, member: discord.Member, amount: int):
  if amount < 5 or amount > 1000:
    return await ctx.send(
        "❌ Jumlah transfer minimal 5 chip dan maksimal 1000 chip!"
    )
  if member.id == ctx.author.id:
    return await ctx.send("❌ Tidak bisa transfer ke diri sendiri!")

  sender_data = get_user(ctx.author.id, ctx.author.name)
  if sender_data[4] == 1:
    return await ctx.send("❌ Akun kamu dibanned!")
  if sender_data[0] < amount:
    return await ctx.send("❌ Chip kamu tidak mencukupi!")

  receiver_data = get_user(member.id, member.name)

  # Update sender & receiver
  update_user(
      ctx.author.id,
      sender_data[0] - amount,
      sender_data[1],
      sender_data[2],
      sender_data[3],
  )
  update_user(
      member.id,
      receiver_data[0] + amount,
      receiver_data[1],
      receiver_data[2],
      receiver_data[3],
  )
  await ctx.send(
      f"✅ Berhasil mentransfer **{amount} Chip** ke {member.mention}!"
  )


# TUKAR CHIP
@bot.command()
async def tukarchip(ctx, amount: int):
  if amount < 5:
    return await ctx.send("❌ Minimal penukaran adalah 5 chip!")

  data = get_user(ctx.author.id, ctx.author.name)
  chips, money, level, exp, banned, _ = data
  if chips < amount:
    return await ctx.send("❌ Chip kamu kurang!")

  total_rp = (amount * 5000) - (amount * 500)  # Pajak 500 rupiah per chip
  if total_rp < 0:
    total_rp = 0

  update_user(ctx.author.id, chips - amount, money + total_rp, level, exp)
  await ctx.send(
      f"✅ Berhasil menukar {amount} chip menjadi **Rp {total_rp:,}** (Pajak"
      " 500p/chip diterapkan)."
  )


# GAME BLACKJACK REALISTIS
def calculate_hand(hand):
  val = 0
  aces = 0
  for card in hand:
    rank = card[:-1]
    if rank in ["J", "Q", "K"]:
      val += 10
    elif rank == "A":
      aces += 1
      val += 11
    else:
      val += int(rank)
  while val > 21 and aces:
    val -= 10
    aces -= 1
  return val


@bot.command()
async def blackjack(ctx, bet: int):
  if bet < 5:
    return await ctx.send("❌ Minimal bet adalah 5 chip!")

  user_id = str(ctx.author.id)
  data = get_user(user_id, ctx.author.name)
  chips, money, level, exp, banned, _ = data
  if banned:
    return await ctx.send("❌ Akun kamu dibanned!")
  if chips < bet:
    return await ctx.send("❌ Chip kamu kurang untuk melakukan taruhan ini!")

  # Potong chip taruhan sementara
  update_user(user_id, chips - bet, money, level, exp)

  deck = [
      f"{r}{s}"
      for r in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
      for s in ["♠", "♥", "♦", "♣"]
  ]
  random.shuffle(deck)

  player_hand = [deck.pop(), deck.pop()]
  dealer_hand = [deck.pop(), deck.pop()]

  def make_embed(game_over=False):
    p_val = calculate_hand(player_hand)
    d_val = (
        calculate_hand(dealer_hand)
        if game_over
        else calculate_hand([dealer_hand[0], "10?"])
    )

    embed = discord.Embed(
        title="🃏 Blackjack Table (BETA)", color=discord.Color.dark_green()
    )
    embed.add_field(
        name=f"Kartu Dealer ({'?' if not game_over else d_val})",
        value=(
            f"{dealer_hand[0]} `?`"
            if not game_over
            else " ".join(dealer_hand)
        ),
        inline=False,
    )
    embed.add_field(
        name=f"Kartu Kamu ({p_val})",
        value=" ".join(player_hand),
        inline=False,
    )
    embed.set_footer(
        text=f"Taruhan: {bet} Chip | Ketik 'hit' atau 'stand' di chat."
    )
    return embed

  msg = await ctx.send(embed=make_embed(False))

  def check(m):
    return (
        m.author == ctx.author
        and m.channel == ctx.channel
        and m.content.lower() in ["hit", "stand"]
    )

  while calculate_hand(player_hand) < 21:
    try:
      response = await bot.wait_for("message", timeout=30.0, check=check)
    except asyncio.TimeoutError:
      await ctx.send("⏳ Waktu habis! Kamu dianggap *Stand*.")
      break

    if response.content.lower() == "hit":
      player_hand.append(deck.pop())
      await msg.edit(embed=make_embed(False))
      if calculate_hand(player_hand) > 21:
        break
    elif response.content.lower() == "stand":
      break

  p_val = calculate_hand(player_hand)
  d_val = calculate_hand(dealer_hand)

  # Giliran Dealer jika player belum busted (< 22)
  if p_val <= 21:
    while calculate_hand(dealer_hand) < 17:
      dealer_hand.append(deck.pop())
    d_val = calculate_hand(dealer_hand)

  # Penentuan Menang / Kalah
  current_data = get_user(user_id, ctx.author.name)
  c_chips = current_data[0]
  result_text = ""

  if p_val > 21:
    result_text = f"💥 Kamu BUST! Kehilangan {bet} Chip."
  elif d_val > 21:
    c_chips += bet * 2
    result_text = f"🎉 Dealer BUST! Kamu Menang dan dapat {bet * 2} Chip!"
  elif p_val > d_val:
    c_chips += bet * 2
    result_text = f"🎉 Kamu Menang! Mendapatkan {bet * 2} Chip!"
  elif p_val < d_val:
    result_text = f"😢 Dealer Menang! Kamu kehilangan {bet} Chip."
  else:
    c_chips += bet
    result_text = "🤝 DRAW! Chip taruhan dikembalikan."

  update_user(
      user_id,
      c_chips,
      current_data[1],
      current_data[2],
      current_data[3] + 5,
  )  # Tambah 5 exp

  final_embed = make_embed(True)
  final_embed.add_field(name="Hasil Permainan", value=result_text, inline=False)
  await msg.edit(embed=final_embed)


# MULTIPLAYER
@bot.command()
async def multiplayer(ctx, member: discord.Member):
  if member.id == ctx.author.id:
    return await ctx.send("❌ Tidak bisa menantang diri sendiri!")
  active_challenges[member.id] = ctx.author.id
  await ctx.send(
      f"⚔️ {member.mention}, kamu ditantang duel blackjack oleh"
      f" {ctx.author.mention}! Ketik `!terima` untuk memulai."
  )


@bot.command()
async def terima(ctx):
  challenger_id = active_challenges.get(ctx.author.id)
  if not challenger_id:
    return await ctx.send("❌ Tidak ada tantangan duel untukmu saat ini!")
  del active_challenges[ctx.author.id]
  challenger = await bot.fetch_user(challenger_id)
  await ctx.send(
      f"🎮 Duel dimulai antara {ctx.author.mention} dan {challenger.mention}!"
      " (Gunakan `!blackjack <bet>` secara bergantian untuk bertanding di meja"
      " terpisah)."
  )


# 3. ADMIN COMMANDS (Role Administrator Only)
def is_admin(ctx):
  return ctx.author.guild_permissions.administrator


@bot.command()
@commands.check(is_admin)
async def setcoin(ctx, member: discord.Member, amount: int):
  data = get_user(member.id, member.name)
  update_user(member.id, amount, data[1], data[2], data[3])
  await ctx.send(
      f"✅ Berhasil mengubah chip {member.mention} menjadi {amount} Chip."
  )


@bot.command()
@commands.check(is_admin)
async def resetcoin(ctx, member: discord.Member):
  data = get_user(member.id, member.name)
  update_user(member.id, 0, data[1], data[2], data[3])
  await ctx.send(f"✅ Chip {member.mention} telah di-reset ke 0.")


@bot.command()
@commands.check(is_admin)
async def setuang(ctx, member: discord.Member, amount: int):
  data = get_user(member.id, member.name)
  update_user(member.id, data[0], amount, data[2], data[3])
  await ctx.send(
      f"✅ Berhasil mengubah uang {member.mention} menjadi Rp {amount:,}."
  )


@bot.command()
@commands.check(is_admin)
async def resetuang(ctx, member: discord.Member):
  data = get_user(member.id, member.name)
  update_user(member.id, data[0], 0, data[2], data[3])
  await ctx.send(f"✅ Uang {member.mention} telah di-reset ke Rp 0.")


@bot.command()
@commands.check(is_admin)
async def setlevel(ctx, member: discord.Member, level: int):
  if level < 1 or level > 100:
    return await ctx.send("❌ Level harus di antara 1 sampai 100!")
  data = get_user(member.id, member.name)
  update_user(member.id, data[0], data[1], level, data[3])
  await ctx.send(f"✅ Level {member.mention} diubah ke level {level}.")


@bot.command()
@commands.check(is_admin)
async def banakun(ctx, member: discord.Member, *, reason="Tidak ada alasan"):
  cursor.execute(
      "UPDATE users SET banned = 1, ban_reason = ? WHERE user_id = ?",
      (reason, str(member.id)),
  )
  db.commit()
  await ctx.send(
      f"🔨 Akun {member.mention} berhasil di-banned. Alasan: {reason}"
  )


@bot.command()
@commands.check(is_admin)
async def unban(ctx, member: discord.Member):
  cursor.execute(
      "UPDATE users SET banned = 0, ban_reason = '' WHERE user_id = ?",
      (str(member.id),),
  )
  db.commit()
  await ctx.send(f"🔓 Akun {member.mention} telah di-unban.")


# 4. TOKO SHOPEE
@bot.hybrid_command(
    name="toko", description="Melihat daftar item toko blackjack"
)
async def toko(ctx, kategori: str = None):
  if kategori == "shopee":
    embed = discord.Embed(
        title="🛒 TOKO SHOPEE BLACKJACK", color=discord.Color.orange()
    )
    embed.description = (
        "**LIST PRODUCT TOKO**\n"
        "```\n"
        "- Role Sesepuh Blackjack : Rp1.000.000\n"
        "- Role Custom Name : Rp1.500.000\n"
        "- Level +10 : Rp750.000\n"
        "- Role Trial Admins : Rp50.000.000\n"
        "- Role BOS SAWIT : Rp10.000.000\n"
        "- Role Secret : Rp100.000.000\n"
        "```\n"
        "Gunakan `!order {nama barang}` contoh: `!order Role Secret`"
    )
    await ctx.send(embed=embed)
  else:
    await ctx.send("Gunakan `/toko shopee` untuk membuka toko.")


@bot.command()
async def order(ctx, *, item_name: str):
  prices = {
      "role sesepuh blackjack": 1000000,
      "role custom name": 1500000,
      "level +10": 750000,
      "role trial admins": 50000000,
      "role bos sawit": 10000000,
      "role secret": 100000000,
  }

  key = item_name.lower()
  if key not in prices:
    return await ctx.send("❌ Barang tidak ditemukan di Toko Shopee!")

  harga = prices[key]
  data = get_user(ctx.author.id, ctx.author.name)
  chips, money, level, exp, banned, _ = data

  if banned:
    return await ctx.send("❌ Akun dibanned!")
  if money < harga:
    return await ctx.send(
        f"❌ Uang Rupiah kamu kurang! Harga barang Rp {harga:,}, uang kamu Rp"
        f" {money:,}."
    )

  # Kurangi uang
  update_user(ctx.author.id, chips, money - harga, level, exp)
  await ctx.send(
      f"🛍️ Berhasil membeli **{item_name}** seharga **Rp {harga:,}**! Silakan"
      " tag Admin untuk klaim rolenya."
  )


# Jalankan Token Bot dari Environment Variable Render
bot.run(os.getenv("TOKEN"))
