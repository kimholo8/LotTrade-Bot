import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime

# =================================================================
# 1. 영구 유지형(Persistent) 뷰 및 티켓 시스템
# =================================================================

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🔒 티켓 닫기", style=discord.ButtonStyle.danger, custom_id="p_tkt_cls")
    async def close(self, it: discord.Interaction, btn):
        await it.response.send_message("⚙️ 5초 후 채널이 삭제됩니다.", ephemeral=True)
        await asyncio.sleep(5)
        await it.channel.delete()

class LTBFixedTicketView(discord.ui.View):
    """[고정 디자인] 사진과 100% 동일한 사양 구현"""
    def __init__(self):
        super().__init__(timeout=None)
    
    async def create_tkt(self, it, cat):
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            it.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ch = await it.guild.create_text_channel(name=f"{cat}-{it.user.name}", overwrites=overwrites)
        await it.response.send_message(f"📩 티켓이 생성되었습니다: {ch.mention}", ephemeral=True)
        await ch.send(embed=discord.Embed(title=f"🎫 {cat} 문의", color=0x2b2d31), view=TicketCloseView())

    @discord.ui.button(label="일반 문의", style=discord.ButtonStyle.primary, emoji="📩", custom_id="f_ltb_1")
    async def b1(self, it, btn): await self.create_tkt(it, "일반")
    
    @discord.ui.button(label="오류 신고", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="f_ltb_2")
    async def b2(self, it, btn): await self.create_tkt(it, "오류")
    
    @discord.ui.button(label="사용자 신고", style=discord.ButtonStyle.secondary, emoji="👤", custom_id="f_ltb_3")
    async def b3(self, it, btn): await self.create_tkt(it, "신고")

# =================================================================
# 2. 메인 봇 엔진 (데이터베이스 및 자동 복구)
# =================================================================

class LTB_Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.db_path = "ltb_config.json"
        self.db = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r", encoding="utf-8") as f: return json.load(f)
        return {"welcome": 0, "leave": 0, "server_log": 0, "warn_log": 0, "warns": {}}

    def save_db(self):
        with open(self.db_path, "w", encoding="utf-8") as f: json.dump(self.db, f, indent=4)

    async def setup_hook(self):
        """봇 재시작 시 버튼 영구 활성화"""
        self.add_view(LTBFixedTicketView())
        self.add_view(TicketCloseView())
        await self.tree.sync()

bot = LTB_Bot()

# =================================================================
# 3. 통합 명령어 리스트 (Administrator 전용)
# =================================================================

# --- [ 설정 및 인사 관리 ] ---
@bot.tree.command(name="설정", description="모든 채널(인사, 퇴장, 로그)을 통합 설정합니다.")
@app_commands.choices(인사모드=[
    app_commands.Choice(name="한 채널에서 인사/퇴장 모두 표시", value="uni"),
    app_commands.Choice(name="각각 다른 채널 사용", value="sep")
])
@app_commands.checks.has_permissions(administrator=True)
async def config_all(it: discord.Interaction, 인사모드: str, 
                     인사채널: discord.TextChannel, 
                     퇴장채널: discord.TextChannel = None,
                     서버로그: discord.TextChannel = None,
                     경고로그: discord.TextChannel = None):
    
    bot.db["welcome"] = 인사채널.id
    bot.db["leave"] = 인사채널.id if 인사모드 == "uni" else (퇴장채널.id if 퇴장채널 else 인사채널.id)
    if 서버로그: bot.db["server_log"] = 서버로그.id
    if 경고로그: bot.db["warn_log"] = 경고로그.id
    
    bot.save_db()
    await it.response.send_message("✅ 모든 시스템 설정이 저장되었습니다.", ephemeral=True)

# --- [ 티켓 시스템 ] ---
@bot.tree.command(name="ltb티켓", description="이미지와 똑같은 사양의 고정 티켓 패널 생성")
@app_commands.checks.has_permissions(administrator=True)
async def ltb_fixed(it: discord.Interaction):
    # image_f4b916.png 문구 완벽 구현
    embed = discord.Embed(
        title="LTB Ticket Support",
        description=(
            "LTB 티켓 채널에 오신것을 환영합니다!\n"
            "티켓 서비스는 플레이어분의 문의를 다른 문의와 섞이지 않게 하여 더 정확하고\n"
            "빠른 확인 및 답변을 제공하고 있습니다.\n\n"
            "서비스를 이용하시기 전에, 아래의 유의 사항을 확인 하시시기 바랍니다!\n\n"
            "**[ 유의사항 ]**\n"
            "· 서버와 관련되지 않는 문의를 하거나 서비스를 오남용 하는 경우, 타임아웃 혹\n"
            "은 경고 처리합니다.\n"
            "· 문의하시려는 내용에 맞는 티켓을 열어주시기 바랍니다."
        ),
        color=0x2b2d31
    )
    await it.channel.send(embed=embed, view=LTBFixedTicketView())
    await it.response.send_message("✅ 공식 티켓 패널 생성 완료", ephemeral=True)

@bot.tree.command(name="티켓설정", description="나만 보이는 실시간 티켓 패널 제작 마법사")
@app_commands.checks.has_permissions(administrator=True)
async def custom_wizard(it: discord.Interaction):
    from __main__ import AdminTicketWizard
    wz = AdminTicketWizard()
    await it.response.send_message("🎫 **티켓 설정 마법사**", embed=wz.embed(), view=wz, ephemeral=True)

# --- [ 관리 도구: 경고, 인증, 역할 ] ---
@bot.tree.command(name="경고", description="유저에게 경고를 부여하고 로그를 전송합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def give_warn(it: discord.Interaction, 유저: discord.Member, 사유: str):
    uid = str(유저.id)
    bot.db["warns"][uid] = bot.db["warns"].get(uid, 0) + 1
    bot.save_db()
    
    await it.response.send_message(f"⚠️ {유저.mention} 경고 부여 (누적: {bot.db['warns'][uid]}회)\n사유: {사유}")
    
    log_ch = bot.get_channel(bot.db["warn_log"])
    if log_ch:
        e = discord.Embed(title="🚨 경고 로그", color=0xff0000, timestamp=datetime.now())
        e.add_field(name="대상", value=유저.mention); e.add_field(name="담당자", value=it.user.mention)
        e.add_field(name="사유", value=사유); e.add_field(name="누적", value=f"{bot.db['warns'][uid]}회")
        await log_ch.send(embed=e)

@bot.tree.command(name="인증기", description="인증 버튼 패널 생성")
@app_commands.checks.has_permissions(administrator=True)
async def verify_tool(it: discord.Interaction, 제목: str, 설명: str, 역할: discord.Role):
    v = discord.ui.View(timeout=None)
    v.add_item(discord.ui.Button(label="인증", style=discord.ButtonStyle.success, custom_id=f"p_v_{역할.id}"))
    await it.channel.send(embed=discord.Embed(title=제목, description=설명, color=0x00ff00), view=v)
    await it.response.send_message("✅ 인증기 생성 완료", ephemeral=True)

@bot.tree.command(name="추가역할지급기", description="최대 5개 역할 지급 패널")
@app_commands.checks.has_permissions(administrator=True)
async def multi_roles(it: discord.Interaction, 제목: str, 설명: str, 
                     역할1: discord.Role, 이름1: str, 
                     역할2: discord.Role=None, 이름2: str=None,
                     역할3: discord.Role=None, 이름3: str=None,
                     역할4: discord.Role=None, 이름4: str=None,
                     역할5: discord.Role=None, 이름5: str=None):
    v = discord.ui.View(timeout=None)
    for r, n in [(역할1, 이름1), (역할2, 이름2), (역할3, 이름3), (역할4, 이름4), (역할5, 이름5)]:
        if r and n: v.add_item(discord.ui.Button(label=n, style=discord.ButtonStyle.secondary, custom_id=f"p_r_{r.id}"))
    await it.channel.send(embed=discord.Embed(title=제목, description=설명, color=0x3498db), view=v)
    await it.response.send_message("✅ 역할 지급기 생성 완료", ephemeral=True)

# =================================================================
# 4. 이벤트 핸들러 (로그 및 인사말)
# =================================================================

@bot.event
async def on_member_join(m):
    ch = bot.get_channel(bot.db["welcome"])
    if ch: await ch.send(f"👋 {m.mention}님, LTB 서버에 오신 것을 환영합니다!")

@bot.event
async def on_member_remove(m):
    ch = bot.get_channel(bot.db["leave"])
    if ch: await ch.send(f"🚪 {m.name}님이 서버를 떠나셨습니다.")

@bot.event
async def on_message_delete(msg):
    if msg.author.bot: return
    log_ch = bot.get_channel(bot.db["server_log"])
    if log_ch:
        e = discord.Embed(title="🗑️ 메시지 삭제 로그", color=0xffa500, timestamp=datetime.now())
        e.add_field(name="작성자", value=msg.author.mention)
        e.add_field(name="내용", value=msg.content or "내용 없음", inline=False)
        await log_ch.send(embed=e)

@bot.event
async def on_interaction(it: discord.Interaction):
    """영구 버튼(인증, 역할) 작동 핵심 로직"""
    if it.type == discord.InteractionType.component:
        cid = it.data.get("custom_id", "")
        if cid.startswith("p_v_") or cid.startswith("p_r_"):
            rid = int(cid.split("_")[-1])
            role = it.guild.get_role(rid)
            if role:
                if role in it.user.roles:
                    await it.user.remove_roles(role)
                    await it.response.send_message(f"❌ {role.name} 역할 제거", ephemeral=True)
                else:
                    await it.user.add_roles(role)
                    await it.response.send_message(f"✅ {role.name} 역할 지급", ephemeral=True)

# =================================================================
# 5. 티켓 커스텀 마법사 클래스
# =================================================================

class AdminTicketWizard(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.t, self.d, self.btns = "제목", "내용", []
    def embed(self): return discord.Embed(title=f"미리보기: {self.t}", description=self.d, color=0x2b2d31)
    
    @discord.ui.button(label="텍스트 설정", style=discord.ButtonStyle.primary)
    async def set_t(self, it, btn): await it.response.send_modal(TxtModal(self))
    
    @discord.ui.button(label="버튼 추가", style=discord.ButtonStyle.success)
    async def add_b(self, it, btn):
        if len(self.btns) >= 5: return await it.response.send_message("최대 5개!", ephemeral=True)
        await it.response.send_modal(BtnModal(self))
        
    @discord.ui.button(label="패널 생성", style=discord.ButtonStyle.danger)
    async def spawn(self, it, btn):
        view = CustomTicketView(self.btns)
        it.client.add_view(view)
        await it.channel.send(embed=self.embed(), view=view)
        await it.response.send_message("✅ 생성 완료", ephemeral=True)

class TxtModal(discord.ui.Modal, title="제목/내용"):
    a = discord.ui.TextInput(label="제목"); b = discord.ui.TextInput(label="내용", style=discord.TextStyle.paragraph)
    def __init__(self, wz): super().__init__(); self.wz = wz
    async def on_submit(self, it):
        self.wz.t, self.wz.d = self.a.value, self.b.value
        await it.response.edit_message(embed=self.wz.embed(), view=self.wz)

class BtnModal(discord.ui.Modal, title="버튼"):
    a = discord.ui.TextInput(label="이름"); b = discord.ui.TextInput(label="색상(primary, danger, success, secondary)")
    def __init__(self, wz): super().__init__(); self.wz = wz
    async def on_submit(self, it):
        self.wz.btns.append({"l": self.a.value, "s": self.b.value.lower()})
        await it.response.edit_message(embed=self.wz.embed(), view=self.wz)

class CustomTicketView(discord.ui.View):
    def __init__(self, btns):
        super().__init__(timeout=None)
        for b in btns:
            btn = discord.ui.Button(label=b['l'], style=getattr(discord.ButtonStyle, b['s']), custom_id=f"p_c_{b['l']}")
            btn.callback = self.cb
            self.add_item(btn)
    async def cb(self, it):
        ch = await it.guild.create_text_channel(name=f"tkt-{it.user.name}", overwrites={
            it.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            it.user: discord.PermissionOverwrite(read_messages=True), it.guild.me: discord.PermissionOverwrite(read_messages=True)
        })
        await it.response.send_message(f"📩 티켓: {ch.mention}", ephemeral=True)
        await ch.send(view=TicketCloseView())

bot.run("봇 토큰")
