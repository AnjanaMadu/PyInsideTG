import io
import os
import sys
import json
import asyncio
import traceback
from telethon import TelegramClient, events

class Database:
    def __init__(self):
        self.db = {}
        if not os.path.exists("db.json"):
            with open("db.json", "w") as f:
                f.write("{}")
        else:
            with open("db.json", "r") as f:
                self.db = json.load(f)

    def get(self, key):
        return self.db.get(key, None)

    def set(self, key, value):
        self.db[key] = value
        with open("db.json", "w") as f:
            json.dump(self.db, f)

    def isOwner(self, user):
        return user == self.get("OWNER")

    def isAuth(self, user):
        return user in self.get("AUTH") or self.isOwner(user)

def getEnv(key):
    value = os.environ.get(key, None)
    if value is None:
        raise KeyError(f"{key} is not set")
        sys.exit(1)
    return value

async def aexec(code, event):
    exec(
        'async def __aexec(event, client): '
        + '\n reply = await event.get_reply_message()'
        + '\n chat = event.chat_id'
        + ''.join(f'\n {l}' for l in code.split('\n'))
    )
    return await locals()['__aexec'](event, event.client)

db = Database()
db.set("OWNER", int(getEnv("OWNER_ID")))
auth_ = getEnv("AUTH_USERS").split(" ")
db.set("AUTH", [int(i) for i in auth_])
client = TelegramClient("evalbot", api_id=int(getEnv("API_ID")), api_hash=getEnv("API_HASH"))

@client.on(events.NewMessage(pattern="^/auth$"))
async def auth_actions(event):
    if not db.isOwner(event.sender_id):
        return
    auth = list(db.get("AUTH"))
    reply = await event.get_reply_message()
    if reply is None:
        ulist = "\n".join(f"`{i}`" for i in auth)
        await event.reply("Auth list:\n" + ulist)
        return
    if reply.sender_id in auth:
        auth.remove(reply.sender_id)
        db.set("AUTH", auth)
        await event.reply(f"Removed `{reply.sender_id}` from auth list")
    else:
        auth.append(reply.sender_id)
        db.set("AUTH", auth)
        await event.reply(f"Added `{reply.sender_id}` to auth list")

@client.on(events.NewMessage(pattern="^/restart$"))
async def restart_action(event):
    if not db.isOwner(event.sender_id):
        return
    await event.reply("Restarting...")
    os.execl(sys.executable, sys.executable, *sys.argv)
    sys.exit(0)

@client.on(events.NewMessage(pattern="^/(bash|sh)"))
async def bash_action(event):
    if not db.isAuth(event.sender_id):
        return
    cmd = event.raw_text.split(" ", 1)
    if len(cmd) == 1:
        await event.reply("Usage: `/sh <command>`")
        return
    msg = await event.reply("Executing `{}`...".format(cmd[1]))
    ps = await asyncio.create_subprocess_shell(cmd[1], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await ps.communicate()
    output = "**Command:**\n`{}`\n\n".format(cmd[1])
    if stdout:
        output += "**stdout:**\n`{}`\n\n".format(stdout.decode().strip())
    if stderr:
        output += "**stderr**:\n`{}`".format(stderr.decode().strip())
    if len(output) > 4096:
        await msg.edit("Output too long, sending as file...")
        output_ = output.replace("`", "").replace("*", "")
        with io.BytesIO(output_.encode()) as f:
            f.name = "output.txt"
            await client.send_file(event.chat_id, file=f, reply_to=event.id)
        await msg.delete()
    else:
        await msg.edit(output)

@client.on(events.NewMessage(pattern="^/eval"))
async def eval_action(event):
    if not db.isAuth(event.sender_id):
        return
    code = event.raw_text.split(" ", 1)
    if len(code) == 1:
        await event.reply("Usage: `/eval <code>`")
        return
    msg = await event.reply("Running...")
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    stdout, stderr, exc = None, None, None
    try:
        value = await aexec(code[1], event)
    except Exception:
        exc = traceback.format_exc()
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    evaluation = exc or stderr or stdout or value or "No output"
    output = "**Code:**\n`{}`\n\n**Output:**\n`{}`".format(code[1], evaluation)
    if len(output) > 4096:
        await msg.edit("Output too long, sending as file...")
        output_ = output.replace("`", "").replace("*", "")
        with io.BytesIO(output_.encode()) as f:
            f.name = "output.txt"
            await client.send_file(event.chat_id, file=f, reply_to=event.id)
        await msg.delete()
    else:
        await msg.edit(output)

client.start(bot_token=getEnv("BOT_TOKEN"))
print("=== STARTED ===")
client.run_until_disconnected()
