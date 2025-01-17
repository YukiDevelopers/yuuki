import importlib
import re
import sys
import time
from datetime import timedelta
import aiohttp
import aiofiles
import requests
from pyrogram import Client, filters
import os
import json
import logging
import asyncio
import psutil
import platform
import base64
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

start_time = time.time()
config_file = "config.json"
modules_file = "modules.json"


async def read_json(file_name):
    async with aiofiles.open(file_name, mode='r') as file:
        content = await file.read()
    return json.loads(content)


async def write_json(file_name, data):
    async with aiofiles.open(file_name, mode='w') as file:
        await file.write(json.dumps(data, indent=4))

async def init_bot():
    if not os.path.exists(modules_file):
        async with aiofiles.open(modules_file, 'w') as file:
            await file.write(json.dumps([], indent=4))

    if not os.path.exists(config_file):
        api_id = input("Enter API ID: ")
        api_hash = input("Enter API Hash: ")
        prefix = input("Enter the prefix for commands (e.g., !help or .help): ")

        config_data = {"api_id": api_id, "api_hash": api_hash, "prefix": prefix}
        await write_json(config_file, config_data)
    else:
        config_data = await read_json(config_file)

    app = Client("yuki_userbot", api_id=config_data['api_id'], api_hash=config_data['api_hash'])
    return app, config_data['prefix']


async def load_modules():
    modules = []
    damaged_modules = []
    modules_list = await read_json(modules_file)
    for module_name in modules_list:
        try:
            module = importlib.import_module(module_name)
            modules.append(module)
        except Exception as e:
            damaged_modules.append((module_name, str(e)))
    return modules, damaged_modules


RISK_METHODS = {
    "critical": [
        {"command": "delete_account", "perms": "delete account"},
        {"command": "reset_authorizations", "perms": "kill account sessions"},
        {"command": "get_authorizations", "perms": "get telegram api_id and api_hash"}
    ],
    "warn": [
        {"command": "log_out", "perms": "disconnect account"}
    ],
    "not_bad": [
        {"command": "torpy", "perms": "can download viruses"},
        {"command": "pyarmor", "perms": "all(obfuscated script)"},
        {"command": "os", "perms": "presumably get os info"}
    ]
}


def check_code_for_risk_methods(code):
    found_methods = {"critical": [], "warn": [], "not_bad": []}
    for risk, methods in RISK_METHODS.items():
        for method in methods:
            if re.search(r'\b' + re.escape(method) + r'\b', code):
                found_methods[risk].append(method)
    return found_methods


async def help_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("help", prefixes=yuki_prefix))
    async def _help_command(_, message):
        try:
            modules, damaged_modules = await load_modules()
            
            modules.sort(key=lambda mod: mod.__name__.split('.')[-1])
            
            help_text = "**<emoji id=5431895003821513760>❄️</emoji> Yuki Userbot Commands <emoji id=5431895003821513760>❄️</emoji>**\n\n"
            help_text += f"**Modules loaded: {len(modules)}**\n"
            for module in modules:
                module_name = module.__name__.split('.')[-1]
                help_text += f"<emoji id=5431736674147114227>🗂</emoji> `{module_name}` [{module.cinfo}]\n"

            if damaged_modules:
                help_text += "\n**Damaged modules:**\n"
                for module_name, error in damaged_modules:
                    help_text += f"<emoji id=5467928559664242360>❗️</emoji> **{module_name}**\n"
                    help_text += f"Error: {error}\n\n"

            help_text += "\n**Standard commands:**\n"
            help_text += f"<emoji id=5334544901428229844>ℹ️</emoji> {yuki_prefix}info - Bot information\n"
            help_text += f"<emoji id=5451646226975955576>⌛️</emoji> {yuki_prefix}ping - Show bot ping\n"
            help_text += f"<emoji id=5451959871257713464>💤</emoji> {yuki_prefix}off - Turn off the bot\n"
            help_text += f"<emoji id=5364105043907716258>🆙</emoji> {yuki_prefix}restart - Restart the bot\n"
            help_text += f"<emoji id=5361979468887893611>🆕</emoji> {yuki_prefix}update - Update bot, wtf it's now version?\n"
            help_text += f"<emoji id=5433811242135331842>📥</emoji> {yuki_prefix}dm - `{yuki_prefix}dm` link - Download module from link\n"
            help_text += f"<emoji id=5469654973308476699>💣</emoji> {yuki_prefix}delm - `{yuki_prefix}delm` module name - Delete module\n"
            help_text += f"<emoji id=5469913852462242978>🧨</emoji> {yuki_prefix}addprefix - `{yuki_prefix}addprefix` prefix E.g: ?,! - Set a prefix\n"
            help_text += f"<emoji id=5433614747381538714>📤</emoji> {yuki_prefix}unm - `{yuki_prefix}unm` module name - Send module file in chat\n"
            help_text += f"<emoji id=5431721976769027887>📂</emoji> {yuki_prefix}lm - Reply `{yuki_prefix}lm` to the file. Installing a module from a file.\n"
            help_text += f"<emoji id=5427009714745517609>✅</emoji> {yuki_prefix}check - Reply `{yuki_prefix}check` to the file check the file for bad practices\n"
            help_text += f"<emoji id=5443132326189996902>🧑‍💻</emoji> {yuki_prefix}sh - `{yuki_prefix}sh true` - Run a command in terminal.\n"
            help_text += f"<emoji id=5373330964372004748>📺</emoji> {yuki_prefix}backup - Backup your Yuki."

            await message.edit(help_text)
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the help command: {str(e)}")



def get_system_info():
    ram = psutil.virtual_memory()
    ram_total = ram.total / (1024 ** 3)
    ram_used = ram.used / (1024 ** 3)
    ram_percent = ram.percent

    system = platform.system()
    release = platform.release()
    version = platform.version()

    return ram_total, ram_used, ram_percent, system, release, version


def get_ip_and_country():
    try:
        ip_response = requests.get('https://api.ipify.org?format=json')
        ip = ip_response.json().get('ip')
        
        if ip:
            country_response = requests.get(f'https://ipinfo.io/{ip}/json')
            country = country_response.json().get('country')
            return ip, country
        else:
            return None, None
    except requests.RequestException as e:
        print(f"Ошибка получения информации: {e}")
        return None, None


async def info_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("info", prefixes=yuki_prefix))
    async def _info_command(_, message):
        try:
            current_time = time.time()
            uptime_seconds = int(round(current_time - start_time))
            uptime = str(timedelta(seconds=uptime_seconds))
            
            ping_start_time = time.time()
            await message.delete()
            ping_end_time = time.time()
            ping_time = round((ping_end_time - ping_start_time) * 1000, 1)
            
            ram_total, ram_used, ram_percent, system, release, version = get_system_info()
            ip, country = get_ip_and_country()
            country_text = f"**Country:** {country}" if ip and country else ""
            
            caption_text = (f"**<emoji id=5431895003821513760>❄️</emoji> 雪 Yuki**\n"
                            f"__🔧Version: 1.2__\n\n"
                            f"{message.from_user.first_name}@yuki-userbot\n"
                            f"      **Uptime:** {uptime}\n"
                            f"      **RAM:** {ram_used:.2f} GB / {ram_total:.2f} GB ({ram_percent}%)\n"
                            f"      **OS:** {system} {release}\n"
                            f"      **Ping:** {ping_time}ms\n"
                            f"      {country_text}")
            
            gif_url = "https://tinypic.host/images/2024/07/29/ezgif-6-baeda9490a.gif"
            await app.send_document(
                chat_id=message.chat.id,
                document=gif_url,
                caption=caption_text)
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the info command: {str(e)}")



async def ping_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("ping", prefixes=yuki_prefix))
    async def _ping_command(_, message):
        try:
            ping_start_time = time.time()
            msg = await message.edit("❄️")
            ping_end_time = time.time()
            ping_time = round((ping_end_time - ping_start_time) * 1000)
            uptime_seconds = int(round(time.time() - start_time))
            uptime = str(timedelta(seconds=uptime_seconds))
            await msg.edit(f"**<emoji id=5188666899860298925>🌒</emoji> Your ping: {ping_time} ms**\n**<emoji id=5451646226975955576>⌛️</emoji> Uptime: {uptime}**")
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the ping command: {str(e)}")


def check_code_for_risk_methods(code):
    found_methods = {"critical": [], "warn": [], "not_bad": []}
    for risk_level, methods in RISK_METHODS.items():
        for method in methods:
            if method["command"] in code:
                found_methods[risk_level].append(method)
    return found_methods

async def check_file(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("check", prefixes=yuki_prefix))
    async def check_dangerous_methods(client: Client, message):
        try:
            file_path = ""
            if message.reply_to_message and message.reply_to_message.document:
                if message.reply_to_message.document.mime_type == "text/x-python":
                    filename = message.reply_to_message.document.file_name
                    file_path = os.path.join(os.getcwd(), filename)
                    await client.download_media(message.reply_to_message.document.file_id, file_path)
                else:
                    await message.edit("<emoji id=5465665476971471368>❌</emoji> Please ensure this is a Python file.")
                    return
            elif message.text:
                url = message.text.split(maxsplit=1)[1].strip()
                response = requests.get(url)
                if response.status_code == 200:
                    filename = url.split('/')[-1]
                    file_path = os.path.join(os.getcwd(), filename)
                    with open(file_path, 'wb') as file:
                        file.write(response.content)
                else:
                    await message.edit("<emoji id=5465665476971471368>❌</emoji> Failed to retrieve the file from the URL.")
                    return
            elif message.document:
                if message.document.mime_type == "text/x-python":
                    filename = message.document.file_name
                    file_path = os.path.join(os.getcwd(), filename)
                    await client.download_media(message.document.file_id, file_path)
                else:
                    await message.edit("<emoji id=5465665476971471368>❌</emoji> Please send a Python file.")
                    return

            if file_path:
                await message.edit("<emoji id=5188666899860298925>🌒</emoji> Checking the file...")
                await asyncio.sleep(1.5)

                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                found_methods = check_code_for_risk_methods(content)
                response_text = ""
                for risk_level, methods in found_methods.items():
                    if methods:
                        response_text += f"<emoji id=5470049770997292425>🌡</emoji> {risk_level.capitalize()}:\n"
                        for method in methods:
                            response_text += f"- {method['command']} ({method['perms']})\n"
                if response_text:
                    await message.edit(response_text)
                else:
                    await message.edit("<emoji id=5427009714745517609>✅</emoji> No dangerous methods found in the file.")
            else:
                await message.edit("<emoji id=5465665476971471368>❌</emoji> Error occurred during file processing.")

        except Exception as e:
            await message.edit(f"<emoji id=5465665476971471368>❌</emoji> Error occurred: {str(e)}")

async def update_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("update", prefixes=yuki_prefix))
    async def _update_command(_, message):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.github.com/repos/YukiDevelopers/yuuki/commits?path=yuki.py") as response:
                    response.raise_for_status()
                    commits = await response.json()
                    if not commits:
                        await message.edit("<emoji id=5465665476971471368>❌</emoji> Bot not found in the repository.")
                        return
                    last_commit_hash = commits[0]["sha"]

            local_commit_hash_file = "bot.commit"
            if os.path.exists(local_commit_hash_file):
                with open(local_commit_hash_file, "r") as file:
                    local_commit_hash = file.read().strip()  
                if local_commit_hash == last_commit_hash:
                    await message.edit(f"<emoji id=5467928559664242360>❗️</emoji> Bot is already up to date. Version: {local_commit_hash[:7]}")
                    return

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://raw.githubusercontent.com/YukiDevelopers/yuuki/main/yuki.py") as response:
                        response.raise_for_status()
                        file_name = "yuki.py"

                        async with aiofiles.open(file_name, 'wb') as file:
                            await file.write(await response.read())

                        with open(local_commit_hash_file, "w") as file:
                            file.write(last_commit_hash)

                        await message.delete()
                        await message.reply_text(
                            f"<emoji id=5427009714745517609>✅</emoji> File `{file_name}` successfully downloaded and saved.\n\nVersion: {last_commit_hash[:7]}")
                        os.execv(sys.executable, [sys.executable] + sys.argv)
            except aiohttp.ClientError as e:
                await message.reply_text(f"Error downloading file: {str(e)}")
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the dm command: {str(e)}")

async def dm_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("dm", prefixes=yuki_prefix))
    async def _dm_command(_, message):
        try:
            if len(message.command) < 2:
                await message.edit("<emoji id=5467928559664242360>❗️</emoji> Please provide a link to the file or module name.")
                return

            url = message.command[1]
            if not url.startswith("http"):
                url = f"https://raw.githubusercontent.com/YukiDevelopers/Yuki_Modules/main/{url}.py"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 404:
                            await message.edit(f"<emoji id=5465665476971471368>❌</emoji> Module `{url}` not found in the repository.")
                            return
                        response.raise_for_status()
                        file_name = os.path.basename(url)
                        module_name = file_name[:-3]

                        modules_list = await read_json(modules_file)
                        if module_name in modules_list:
                            await message.edit(f"<emoji id=5467928559664242360>❗️</emoji> Module `{module_name}` already exists in `{modules_file}`.")
                            return

                        async with aiofiles.open(file_name, 'wb') as file:
                            await file.write(await response.read())

                        modules_list.append(module_name)
                        await write_json(modules_file, modules_list)

                        await message.delete()
                        await message.reply_text(
                            f"<emoji id=5427009714745517609>✅</emoji> File `{file_name}` successfully downloaded and saved.\n\nLink: `{url}`")
                        os.execv(sys.executable, [sys.executable] + sys.argv)
            except aiohttp.ClientError as e:
                await message.reply_text(f"Error downloading file: {str(e)}")
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the dm command: {str(e)}")


async def load_module(app: Client, yuki_prefix):
    @app.on_message(filters.me & filters.command("lm", prefixes=yuki_prefix))
    async def load_cmd(_, message):
        reply = message.reply_to_message
        file = message if message.document else reply if reply and reply.document else None

        if not file:
            await message.edit("<emoji id=5465665476971471368>❌</emoji> A reply or a document is needed!")
            return

        if not file.document.file_name.endswith(".py"):
            await message.edit("<emoji id=5465665476971471368>❌</emoji> Only .py files are supported!")
            return

        filename = file.document.file_name
        module_name = filename.split(".py")[0]

        await message.edit(f"<emoji id=5431895003821513760>❄️</emoji> Loading module **{module_name}**...")

        file_path = os.path.join(os.getcwd(), filename)
        await file.download(file_path)

        modules_list = await read_json(modules_file)
        if module_name not in modules_list:
            modules_list.append(module_name)
        await write_json(modules_file, modules_list)

        await message.edit(f"<emoji id=5431895003821513760>❄️</emoji> Module **{module_name}** successfully loaded!")
        os.execv(sys.executable, [sys.executable] + sys.argv)


async def delm_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("delm", prefixes=yuki_prefix))
    async def _delm_command(_, message):
        try:
            if len(message.command) < 2:
                await message.edit("<emoji id=5467928559664242360>❗️</emoji> Please provide the module name to delete.")
                return

            module_name = message.command[1]
            module_file = f"{module_name}.py"

            modules_list = await read_json(modules_file)
            if module_name not in modules_list:
                await message.edit(f"<emoji id=5467928559664242360>❗️</emoji> Module `{module_name}` not found in `{modules_file}`.")
                return

            modules_list.remove(module_name)
            await write_json(modules_file, modules_list)

            if os.path.exists(module_file):
                os.remove(module_file)
                await message.edit(
                    f"<emoji id=5427009714745517609>✅</emoji> Module `{module_name}` successfully deleted from `{modules_file}` and file `{module_file}` deleted.")
            else:
                await message.edit(
                    f"<emoji id=5427009714745517609>✅</emoji> Module `{module_name}` successfully deleted from `{modules_file}`, but file `{module_file}` not found.")

            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the delm command: {str(e)}")


async def off_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("off", prefixes=yuki_prefix))
    async def _off_command(_, message):
        try:
            await message.edit("**<emoji id=5451959871257713464>💤</emoji> Turning off the userbot...**")
            await app.stop()
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the off command: {str(e)}")


async def restart_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("restart", prefixes=yuki_prefix))
    async def _restart_command(_, message):
        try:
            await message.edit("**<emoji id=5361979468887893611>🆕</emoji> You Yuki will be rebooted...**")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the restart command: {str(e)}")


async def unm_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("unm", prefixes=yuki_prefix))
    async def _unm_command(_, message):
        try:
            if len(message.command) < 2:
                await message.edit("<emoji id=5467928559664242360>❗️</emoji> Please provide the module name to send.")
                return

            module_name = message.command[1]
            module_file = f"{module_name}.py"

            if not os.path.exists(module_file):
                await message.edit(f"<emoji id=5467928559664242360>❗️</emoji> File `{module_file}` not found.")
                return

            caption = f"<emoji id=5431721976769027887>📂</emoji> Here is the module `{module_name}`\n\n<emoji id=5431895003821513760>❄️</emoji> .lm to this message to install."
            await app.send_document(message.chat.id, module_file, caption=caption)
            await message.delete()
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the unm command: {str(e)}")


async def addprefix_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("addprefix", prefixes=yuki_prefix))
    async def _addprefix_command(_, message):
        try:
            if len(message.command) < 2:
                await message.edit("<emoji id=5467928559664242360>❗️</emoji> Please provide the new prefix.")
                return

            new_prefix = message.command[1]

            config_data = await read_json(config_file)
            config_data['prefix'] = new_prefix
            await write_json(config_file, config_data)

            global yuki_prefix
            yuki_prefix = new_prefix

            await message.reply_text(f"<emoji id=5427009714745517609>✅</emoji> Prefix successfully changed to `{new_prefix}`.")
            await message.delete()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            await message.reply_text(f"An error occurred while executing the addprefix command: {str(e)}")


async def backup_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("backup", prefixes=yuki_prefix))
    async def _backup_command(_, message):
        try:
            reply = message.reply_to_message
            if reply and reply.document and reply.document.mime_type == "application/json":
                file_path = await reply.download()
                with open(file_path, 'r') as file:
                    data = json.load(file)
                
                modules_list = await read_json(modules_file)
                for module_name, encoded_content in data.items():
                    module_file_path = f"{module_name}.py"
                    with open(module_file_path, 'wb') as module_file:
                        module_file.write(base64.b64decode(encoded_content))
                    
                    if module_name not in modules_list:
                        modules_list.append(module_name)
                
                await write_json(modules_file, modules_list)
                await message.delete()
                await message.reply_text("<emoji id=5427009714745517609>✅</emoji> Modules successfully restored from backup.")
            else:
                modules_list = await read_json(modules_file)
                backup_data = {}
                for module_name in modules_list:
                    module_file_path = f"{module_name}.py"
                    if os.path.exists(module_file_path):
                        with open(module_file_path, 'rb') as module_file:
                            encoded_content = base64.b64encode(module_file.read()).decode('utf-8')
                            backup_data[module_name] = encoded_content
                
                backup_file_path = "modules_backup.json"
                with open(backup_file_path, 'w') as backup_file:
                    json.dump(backup_data, backup_file, indent=4)
                    
                await message.delete()
                await app.send_document(
                    message.chat.id, 
                    backup_file_path, 
                    caption="<emoji id=5427009714745517609>✅</emoji> Backup of modules successfully created.\n\nUse `.backup` on this message to restore the modules."
                )
                os.remove(backup_file_path)
        except Exception as e:
            await message.delete()
            await message.reply_text(f"<emoji id=5465665476971471368>❌</emoji> An error occurred: {str(e)}")


async def terminal_command(app, yuki_prefix):
    @app.on_message(filters.me & filters.command("sh", prefixes=yuki_prefix))
    async def _terminal_command(_, message):
        if len(message.command) > 1:
            command = " ".join(message.command[1:])
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                output = result.stdout if result.stdout else result.stderr

                chunk_size = 4096
                if len(output) > chunk_size:
                    for i in range(0, len(output), chunk_size):
                        await message.reply_text(f"<emoji id=5188217332748527444>🔍</emoji> Result (part {i//chunk_size + 1}):\n```\n{output[i:i+chunk_size]}\n```")
                else:
                    await message.edit_text(f"<emoji id=5188217332748527444>🔍</emoji> Result:\n```\n{output}\n```")
            except Exception as e:
                error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
                await message.edit_text(f"<emoji id=5465665476971471368>❌</emoji> Error:\n```\n{error_message}\n```")
        else:
            await message.edit_text("<emoji id=5422858869372104873>🙅‍♂️</emoji> Please provide a command to execute")


async def load_and_exec_modules(app):
    try:
        modules, _ = await load_modules()
        for module in modules:
            if hasattr(module, 'register_module'):
                module.register_module(app)
    except Exception as e:
        logger.error(f"An error occurred while loading modules: {str(e)}")


def main():
    loop = asyncio.get_event_loop()
    app, yuki_prefix = loop.run_until_complete(init_bot())

    loop.run_until_complete(load_and_exec_modules(app))
    loop.run_until_complete(help_command(app, yuki_prefix))
    loop.run_until_complete(info_command(app, yuki_prefix))
    loop.run_until_complete(ping_command(app, yuki_prefix))
    loop.run_until_complete(dm_command(app, yuki_prefix))
    loop.run_until_complete(delm_command(app, yuki_prefix))
    loop.run_until_complete(off_command(app, yuki_prefix))
    loop.run_until_complete(restart_command(app, yuki_prefix))
    loop.run_until_complete(unm_command(app, yuki_prefix))
    loop.run_until_complete(addprefix_command(app, yuki_prefix))
    loop.run_until_complete(load_module(app, yuki_prefix))
    loop.run_until_complete(check_file(app, yuki_prefix))
    loop.run_until_complete(update_command(app, yuki_prefix))
    loop.run_until_complete(backup_command(app, yuki_prefix))
    loop.run_until_complete(terminal_command(app, yuki_prefix))

    app.run()


if __name__ == "__main__":
    main()
