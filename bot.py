import os
import json
import uuid
import re
import asyncio
import glob
from datetime import date
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =====================================
# SYSTEM CONFIGURATION [ENCRYPTED]
# =====================================
TOKEN = "8808956054:AAEfxKA88M2iUoa7F8UInrrTcBj3dYrarnQ"
ADMIN_ID = 8177674216
GROUP_ID = -1003857456899
GROUP_LINK = "https://t.me/+LY4WB3EYA3IyZDAx"

# CORE ASSETS
DB_PATH = r"C:\Users\PCX\Pictures\bot\database"
DEFAULT_LIMIT = 400
PROGRESS_FILE = "progress.json"
CACHE_FILE = "daily_cache.json"
USER_CONFIG_FILE = "user_configs.json"

def normalize_target(target: str) -> str:
    target = target.lower().strip()
    target = re.sub(r'^https?://', '', target)
    target = re.sub(r'^www\.', '', target)
    target = target.split('/')[0]
    return target

def load_json(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# DATA INITIALIZATION
search_progress = load_json(PROGRESS_FILE)
user_cache = load_json(CACHE_FILE)
user_configs = load_json(USER_CONFIG_FILE)

async def is_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user: return False
    if chat.type == "private" and user.id == ADMIN_ID: return True
    if chat.id == GROUP_ID: return True
    if chat.type == "private":
        text = (
            "--- [ACCESS_DENIED] ---\n"
            "ERROR: Unauthorized Access\n"
            "STATUS: Restricted to Official Group\n"
            f"JOIN: {GROUP_LINK}"
        )
        await update.message.reply_text(f"<code>{text}</code>", parse_mode="HTML", disable_web_page_preview=True)
        return False
    return False

async def post_init(application: Application):
    # Set bot commands in the menu
    commands = [
        BotCommand("search", "Pesquisar um site ou link (Ex: /search netflix.com)"),
        BotCommand("vip", "Ver planos VIP e benefícios disponíveis"),
        BotCommand("start", "Mostrar o guia de uso do sistema")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update, context): return
    text = (
        "--- [DATA_SEARCH_ENGINE_V2] ---\n"
        "SYSTEM STATUS: OPERATIONAL\n\n"
        "COMO USAR:\n"
        "1. Copie o link ou domínio alvo\n"
        "2. Digite: /search <alvo>\n"
        "Exemplo: /search netflix.com\n\n"
        "REGRAS DO SISTEMA:\n"
        "- Limite Padrão: 400 registros/busca\n"
        "- Entrega Sequencial: Novos dados a cada busca\n"
        "- Acesso VIP: Digite /vip para limites maiores"
    )
    await update.message.reply_text(f"<code>{text}</code>", parse_mode="HTML", disable_web_page_preview=True)

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_id = str(context.args[0])
        new_limit = int(context.args[1])
        if target_id not in user_configs: user_configs[target_id] = {}
        user_configs[target_id]["limit"] = new_limit
        save_json(USER_CONFIG_FILE, user_configs)
        await update.message.reply_text(f"<code>[ADMIN] User {target_id} limit set to {new_limit}</code>", parse_mode="HTML")
    except:
        await update.message.reply_text("<code>Usage: /setlimit <user_id> <value></code>", parse_mode="HTML")

async def vip_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update, context): return
    text = (
        "--- [VIP_PLANS] ---\n"
        "15 BRL - 1 Mês (1000 buscas)\n"
        "50 BRL - 3 Meses (1500 buscas)\n"
        "PAGAMENTO: PAYPAL\n"
        "CONTATO: @fuckyou00l"
    )
    await update.message.reply_text(f"<code>{text}</code>", parse_mode="HTML", disable_web_page_preview=True)

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update, context): return
    if not context.args:
        await update.message.reply_text("<code>Uso: /search <alvo></code>", parse_mode="HTML")
        return

    raw_input = " ".join(context.args).strip()
    target = normalize_target(raw_input)
    
    user_id_num = update.effective_user.id
    user_id_str = str(user_id_num)
    today = date.today().isoformat()
    
    # CHECK DAILY CACHE (Skip for Admin)
    if user_id_num != ADMIN_ID:
        cache_key = f"cache|{target}"
        cache = user_cache.get(cache_key)
        if cache and cache.get("date") == today:
            key_id = cache["key"]
            out_file = f"DATA_{key_id}.txt"
            with open(out_file, "w", encoding="utf-8") as out:
                out.write(cache["content"])
            
            caption = (
                "--- [CACHE_HIT] ---\n"
                f"KEY: {key_id}\n"
                f"TARGET: {target}\n"
                f"TOTAL_FOUND: {cache['total']}\n"
                "STATUS: FROM_CACHE"
            )
            await update.message.reply_document(document=open(out_file, "rb"), filename=out_file, caption=f"<code>{caption}</code>", parse_mode="HTML")
            os.remove(out_file)
            return

    # START SIMULATED SCAN (TOTAL 12 SECONDS)
    status = await update.message.reply_text(f"<code>[CONNECTING] Estabelecendo conexão segura...</code>", parse_mode="HTML")
    await asyncio.sleep(3)
    await status.edit_text(f"<code>[SEARCHING] Escaneando bancos de dados para: {target}...</code>", parse_mode="HTML")
    await asyncio.sleep(5)

    try:
        current_db_path = DB_PATH if os.path.exists(DB_PATH) else "database"
        db_files = glob.glob(os.path.join(current_db_path, "*.txt"))
        
        if not db_files:
            await status.edit_text("<code>[ERROR] Pasta de database não encontrada.</code>", parse_mode="HTML")
            return

        all_matches = []
        for db in db_files:
            with open(db, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if target in line.lower():
                        all_matches.append(line.strip())

        total_found = len(all_matches)
        if total_found == 0:
            await status.edit_text(f"<code>[NOT_FOUND] Nenhum resultado para: {target}</code>", parse_mode="HTML")
            return

        await status.edit_text(f"<code>[EXTRACTING] {total_found} resultados encontrados. Compilando...</code>", parse_mode="HTML")
        await asyncio.sleep(4)

        # SEQUENTIAL DELIVERY (400 in 400)
        progress_key = f"global|{target}"
        consumed = search_progress.get(progress_key, 0)
        if consumed >= total_found: consumed = 0

        user_limit = user_configs.get(user_id_str, {}).get("limit", DEFAULT_LIMIT)
        raw_chunk = all_matches[consumed : consumed + user_limit]
        delivered_count = len(raw_chunk)
        
        search_progress[progress_key] = consumed + delivered_count
        save_json(PROGRESS_FILE, search_progress)
        
        key_id = uuid.uuid4().hex[:8].upper()
        
        header = (
            f"--- [DATA_KEY: {key_id}] ---\n"
            f"TARGET: {target}\n"
            f"TOTAL_MATCHES: {total_found}\n"
            f"RECORDS_IN_THIS_FILE: {delivered_count}\n" + "="*30 + "\n\n"
        )
        file_content = header + "\n".join(raw_chunk)

        if user_id_num != ADMIN_ID:
            cache_key = f"cache|{target}"
            user_cache[cache_key] = {
                "date": today,
                "key": key_id,
                "total": total_found,
                "content": file_content
            }
            save_json(CACHE_FILE, user_cache)

        out_file = f"DATA_{key_id}.txt"
        with open(out_file, "w", encoding="utf-8") as out:
            out.write(file_content)

        caption = (
            "--- [SCAN_COMPLETE] ---\n"
            f"KEY: {key_id}\n"
            f"TARGET: {target}\n"
            f"TOTAL_HITS: {total_found}\n"
            f"DELIVERED: {delivered_count}\n"
            "STATUS: SUCCESS"
        )

        await status.delete()
        await update.message.reply_document(document=open(out_file, "rb"), filename=out_file, caption=f"<code>{caption}</code>", parse_mode="HTML")
        os.remove(out_file)

    except Exception as e:
        await status.edit_text(f"<code>[SYSTEM_ERROR] {str(e)}</code>", parse_mode="HTML")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("vip", vip_plans))
    app.add_handler(CommandHandler("setlimit", set_limit))
    
    print(f"[SYSTEM_BOOT] Commands and Portuguese Menu active.")
    app.run_polling()

if __name__ == "__main__":
    main()
