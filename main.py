import os, logging, asyncio, io, sys, traceback
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from git import Repo
from os import environ, execle
import sys
from git.exc import GitCommandError, InvalidGitRepositoryError
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - [%(levelname)s] - %(message)s'
)
LOGGER = logging.getLogger(__name__)

# --- STARTING BOT --- #
api_id = int(os.environ.get("APP_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("TG_BOT_TOKEN")
auth_chts = set(int(x) for x in os.environ.get("AUTH_USERS", "").split())
banned_usrs = set(int(x) for x in os.environ.get("BANNED_USRS", "").split())
client = TelegramClient('client', api_id, api_hash).start(bot_token=bot_token)

# --- PINGING BOT --- #
@client.on(events.NewMessage(pattern="/ping"))
async def pingE(event):
    start = datetime.now()
    catevent = await event.respond("`!....`")
    await asyncio.sleep(0.3)
    await catevent.edit("`..!..`")
    await asyncio.sleep(0.3)
    await catevent.edit("`....!`")
    end = datetime.now()
    tms = (end - start).microseconds / 1000
    ms = round((tms - 0.6) / 3, 3)
    await catevent.edit(f"Pong!\n`{ms} ms`")
    LOGGER.info("Bot Pinging")

# --- UPDATE BOT --- #
@client.on(events.NewMessage(pattern="/update"))
async def updateE(event):
    if not event.sender_id in auth_chts:
        return
    try:
     repo = Repo()
    except InvalidGitRepositoryError:
     repo = Repo.init()
     origin = repo.create_remote("upstream", "https://github.com/AnjanaMadu/TerminalBot")
     origin.fetch()
     repo.create_head("master", origin.refs.master)
     repo.heads.master.set_tracking_branch(origin.refs.master)
     repo.heads.master.checkout(True)
    repo.create_remote("upstream", 'https://github.com/AnjanaMadu/TerminalBot')
    ac_br = repo.active_branch.name
    ups_rem = repo.remote("upstream")
    ups_rem.fetch(ac_br)
    try:
            ups_rem.pull(ac_br)
    except GitCommandError:
            repo.git.reset("--hard", "FETCH_HEAD")
    args = [sys.executable, "main.py"]
    execle(sys.executable, *args, environ)


    
# --- RESTART BOT --- #
@client.on(events.NewMessage(pattern="/restart"))
async def restartE(event):
    if not event.sender_id in auth_chts:
        return
    await event.respond("Restarting")
    executable = sys.executable.replace(" ", "\\ ")
    args = [executable, "main.py"]
    os.execle(executable, *args, os.environ)
    sys.exit(0)
    LOGGER.info("Bot Restarting")

# --- EVAL DEF HERE --- #
async def aexec(code, smessatatus):
    message = event = smessatatus
    p = lambda _x: print(_format.yaml_format(_x))
    reply = await event.get_reply_message()
    exec(
        f"async def __aexec(message, event , reply, client, p, chat): "
        + "".join(f"\n {l}" for l in code.split("\n"))
    )
    return await locals()["__aexec"](
        message, event, reply, message.client, p, message.chat_id
    )
 
# --- EVAL EVENT HERE --- # 
@client.on(events.NewMessage(chats=auth_chts, pattern="/eval ?(.*)"))
async def evalE(event):
    if event.sender_id in banned_usrs:
        return await event.respond("You are Banned!")
    cmd = "".join(event.message.message.split(maxsplit=1)[1:])
    if not cmd:
        return
    cmd = (
        cmd.replace("send_message", "send_message")
        .replace("send_file", "send_file")
        .replace("edit_message", "edit_message")
    )
    catevent = await event.respond("`Running ...`")
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    stdout, stderr, exc = None, None, None
    try:
        t = asyncio.create_task(aexec(cmd, event))
        await t
    except Exception:
        exc = traceback.format_exc()
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    evaluation = ""
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "Success"
    final_output = (
        f"**•  Eval : **\n```{cmd}``` \n\n**•  Result : **\n```{evaluation}``` \n"
    )
    try:
        await catevent.edit(final_output)
    except:
        with io.open("output.txt", "w", encoding="utf-8") as k:
            k.write(str(final_output).replace("`", "").replace("*", ""))
            k.close()
        await event.client.send_file(event.chat_id, "output.txt")
        os.remove('output.txt')
        await catevent.delete()
    LOGGER.info(f"Eval: {cmd}\nExcute by: {event.sender_id}")

# --- BASH DEF HERE --- #
async def bash(cmd):

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    err = stderr.decode().strip()
    out = stdout.decode().strip()
    return out, err

# --- BASH EVENT HERE --- #
@client.on(events.NewMessage(chats=auth_chts, pattern="/bash ?(.*)"))
async def bashE(event):
    if event.sender_id in banned_usrs:
        return await event.respond("You are Banned!")
    cmd = "".join(event.message.message.split(maxsplit=1)[1:])
    oldmsg = await event.respond("`Running...`")
    out, err = await bash(cmd)
    LOGGER.info(f"Bash: {cmd}\nExcute by: {event.sender_id}")
    if not out:
        out = None
    elif not err:
        err = None
    try:
        await oldmsg.edit(f'**CMD:** `{cmd}`\n**ERROR:**\n `{err}`\n**OUTPUT:**\n `{out}`')
    except:
        with io.open("output.txt", "w", encoding="utf-8") as k:
            k.write(f'CMD: {cmd}\nERROR:\n {err}\nOUTPUT:\n {out}')
            k.close()
        await event.client.send_file(event.chat_id, "output.txt", reply_to=event)
        os.remove('output.txt')
        await oldmsg.delete()

print('>> BOT STARTED <<')
os.system("python -V")
client.run_until_disconnected()


