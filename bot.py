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
    MessageHandler,
    filters,
    ContextTypes,
)

# =====================================
# SYSTEM CONFIGURATION
# =====================================
TOKEN = os.environ.get("BOT_TOKEN", "8808956054:AAEk4pl9FVzcT-mRO7VbEhEXqC3WqRhgIGI")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8177674216"))
GROUP_ID = int(os.environ.get("GROUP_ID", "-1003857456899"))
GROUP_LINK = os.environ.get("GROUP_LINK", "https://t.me/+LY4WB3EYA3IyZDAx")

# CORE ASSETS — caminhos relativos ao diretório do bot (Linux-compatible)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database")
DEFAULT_LIMIT = 400
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")
CACHE_FILE = os.path.join(BASE_DIR, "daily_cache.json")
USER_CONFIG_FILE = os.path.join(BASE_DIR, "user_configs.json")

# Garante que a pasta de database existe
os.makedirs(DB_PATH, exist_ok=True)

# =====================================
# HELPERS
# =====================================

def normalize_target(target: str) -> str:
    target = target.lower().strip()
    target = re.sub(r'^https?://', '', target)
    target = re.sub(r'^www\.', '', target)
    target = target.split('/')[0]
    return target

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# DATA INITIALIZATION
search_progress = load_json(PROGRESS_FILE)
user_cache = load_json(CACHE_FILE)
user_configs = load_json(USER_CONFIG_FILE)

# =====================================
# PERMISSION CHECK
# =====================================

async def is_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return False
    if chat.type == "private" and user.id == ADMIN_ID:
        return True
    if chat.id == GROUP_ID:
        return True
    if chat.type == "private":
        text = (
            "--- [ACCESS_DENIED] ---\n"
            "ERROR: Unauthorized Access\n"
            "STATUS: Restricted to Official Group\n"
            f"JOIN: {GROUP_LINK}"
        )
        await update.message.reply_text(
            f"<code>{text}</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return False
    return False

# =====================================
# BOT SETUP
# =====================================

async def post_init(application: Application):
    commands = [
        BotCommand("search", "Pesquisar um site ou link (Ex: /search netflix.com)"),
        BotCommand("vip", "Ver planos VIP e benefícios disponíveis"),
        BotCommand("start", "Mostrar o guia de uso do sistema"),
        BotCommand("upload", "Enviar arquivo de database (somente Admin)"),
        BotCommand("listdb", "Listar databases carregadas (somente Admin)"),
        BotCommand("deletedb", "Deletar uma database (somente Admin)"),
    ]
    await application.bot.set_my_commands(commands)

# =====================================
# COMMANDS
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update, context):
        return
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
    await update.message.reply_text(
        f"<code>{text}</code>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_id = str(context.args[0])
        new_limit = int(context.args[1])
        if target_id not in user_configs:
            user_configs[target_id] = {}
        user_configs[target_id]["limit"] = new_limit
        save_json(USER_CONFIG_FILE, user_configs)
        await update.message.reply_text(
            f"<code>[ADMIN] User {target_id} limit set to {new_limit}</code>",
            parse_mode="HTML"
        )
    except:
        await update.message.reply_text(
            "<code>Usage: /setlimit <user_id> <value></code>",
            parse_mode="HTML"
        )

async def vip_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update, context):
        return
    text = (
        "--- [VIP_PLANS] ---\n"
        "15 BRL - 1 Mês (1000 buscas)\n"
        "50 BRL - 3 Meses (1500 buscas)\n"
        "PAGAMENTO: PAYPAL\n"
        "CONTATO: @fuckyou00l"
    )
    await update.message.reply_text(
        f"<code>{text}</code>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# =====================================
# UPLOAD DE DATABASE (ADMIN ONLY)
# =====================================

async def upload_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instrui o admin a enviar o arquivo de database."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("<code>[ERROR] Acesso negado.</code>", parse_mode="HTML")
        return
    text = (
        "--- [UPLOAD_DATABASE] ---\n"
        "Envie o arquivo .txt da database\n"
        "diretamente neste chat como documento.\n"
        "O arquivo será carregado automaticamente."
    )
    await update.message.reply_text(f"<code>{text}</code>", parse_mode="HTML")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe arquivos .txt enviados pelo admin e salva na pasta database."""
    user = update.effective_user
    if not user or user.id != ADMIN_ID:
        return

    doc = update.message.document
    if not doc:
        return

    file_name = doc.file_name or "database_upload.txt"

    # Aceita apenas .txt
    if not file_name.lower().endswith(".txt"):
        await update.message.reply_text(
            "<code>[ERROR] Apenas arquivos .txt são aceitos.</code>",
            parse_mode="HTML"
        )
        return

    status_msg = await update.message.reply_text(
        f"<code>[UPLOADING] Recebendo {file_name}...</code>",
        parse_mode="HTML"
    )

    try:
        file = await context.bot.get_file(doc.file_id)
        save_path = os.path.join(DB_PATH, file_name)
        await file.download_to_drive(save_path)

        # Conta linhas do arquivo
        with open(save_path, "r", encoding="utf-8", errors="ignore") as f:
            line_count = sum(1 for _ in f)

        text = (
            "--- [UPLOAD_SUCCESS] ---\n"
            f"ARQUIVO: {file_name}\n"
            f"REGISTROS: {line_count:,}\n"
            f"STATUS: SALVO EM DATABASE"
        )
        await status_msg.edit_text(f"<code>{text}</code>", parse_mode="HTML")

    except Exception as e:
        await status_msg.edit_text(
            f"<code>[UPLOAD_ERROR] {str(e)}</code>",
            parse_mode="HTML"
        )

async def list_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todos os arquivos de database carregados."""
    if update.effective_user.id != ADMIN_ID:
        return

    db_files = glob.glob(os.path.join(DB_PATH, "*.txt"))
    if not db_files:
        await update.message.reply_text(
            "<code>[DATABASE] Nenhuma database carregada.</code>",
            parse_mode="HTML"
        )
        return

    lines = ["--- [DATABASE_LIST] ---"]
    total_lines = 0
    for db in sorted(db_files):
        name = os.path.basename(db)
        try:
            with open(db, "r", encoding="utf-8", errors="ignore") as f:
                count = sum(1 for _ in f)
            total_lines += count
            lines.append(f"{name}: {count:,} registros")
        except:
            lines.append(f"{name}: erro ao ler")

    lines.append(f"TOTAL: {total_lines:,} registros")
    await update.message.reply_text(
        f"<code>{chr(10).join(lines)}</code>",
        parse_mode="HTML"
    )

async def delete_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deleta um arquivo de database pelo nome."""
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "<code>Uso: /deletedb <nome_do_arquivo.txt></code>",
            parse_mode="HTML"
        )
        return

    file_name = context.args[0]
    # Segurança: não permite path traversal
    file_name = os.path.basename(file_name)
    file_path = os.path.join(DB_PATH, file_name)

    if not os.path.exists(file_path):
        await update.message.reply_text(
            f"<code>[ERROR] Arquivo '{file_name}' não encontrado.</code>",
            parse_mode="HTML"
        )
        return

    os.remove(file_path)
    await update.message.reply_text(
        f"<code>[DELETED] '{file_name}' removido da database.</code>",
        parse_mode="HTML"
    )

# =====================================
# SEARCH COMMAND
# =====================================

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allowed(update, context):
        return
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
            out_file = os.path.join(BASE_DIR, f"DATA_{key_id}.txt")
            with open(out_file, "w", encoding="utf-8") as out:
                out.write(cache["content"])

            caption = (
                "--- [CACHE_HIT] ---\n"
                f"KEY: {key_id}\n"
                f"TARGET: {target}\n"
                f"TOTAL_FOUND: {cache['total']}\n"
                "STATUS: FROM_CACHE"
            )
            await update.message.reply_document(
                document=open(out_file, "rb"),
                filename=f"DATA_{key_id}.txt",
                caption=f"<code>{caption}</code>",
                parse_mode="HTML"
            )
            os.remove(out_file)
            return

    # START SIMULATED SCAN
    status = await update.message.reply_text(
        "<code>[CONNECTING] Estabelecendo conexão segura...</code>",
        parse_mode="HTML"
    )
    await asyncio.sleep(3)
    await status.edit_text(
        f"<code>[SEARCHING] Escaneando bancos de dados para: {target}...</code>",
        parse_mode="HTML"
    )
    await asyncio.sleep(5)

    try:
        db_files = glob.glob(os.path.join(DB_PATH, "*.txt"))

        if not db_files:
            await status.edit_text(
                "<code>[ERROR] Nenhuma database carregada. Admin: use /upload para adicionar arquivos.</code>",
                parse_mode="HTML"
            )
            return

        all_matches = []
        for db in db_files:
            with open(db, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if target in line.lower():
                        all_matches.append(line.strip())

        total_found = len(all_matches)
        if total_found == 0:
            await status.edit_text(
                f"<code>[NOT_FOUND] Nenhum resultado para: {target}</code>",
                parse_mode="HTML"
            )
            return

        await status.edit_text(
            f"<code>[EXTRACTING] {total_found} resultados encontrados. Compilando...</code>",
            parse_mode="HTML"
        )
        await asyncio.sleep(4)

        # SEQUENTIAL DELIVERY
        progress_key = f"global|{target}"
        consumed = search_progress.get(progress_key, 0)
        if consumed >= total_found:
            consumed = 0

        user_limit = user_configs.get(user_id_str, {}).get("limit", DEFAULT_LIMIT)
        raw_chunk = all_matches[consumed: consumed + user_limit]
        delivered_count = len(raw_chunk)

        search_progress[progress_key] = consumed + delivered_count
        save_json(PROGRESS_FILE, search_progress)

        key_id = uuid.uuid4().hex[:8].upper()

        header = (
            f"--- [DATA_KEY: {key_id}] ---\n"
            f"TARGET: {target}\n"
            f"TOTAL_MATCHES: {total_found}\n"
            f"RECORDS_IN_THIS_FILE: {delivered_count}\n" + "=" * 30 + "\n\n"
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

        out_file = os.path.join(BASE_DIR, f"DATA_{key_id}.txt")
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
        await update.message.reply_document(
            document=open(out_file, "rb"),
            filename=f"DATA_{key_id}.txt",
            caption=f"<code>{caption}</code>",
            parse_mode="HTML"
        )
        os.remove(out_file)

    except Exception as e:
        await status.edit_text(
            f"<code>[SYSTEM_ERROR] {str(e)}</code>",
            parse_mode="HTML"
        )

# =====================================
# MAIN
# =====================================

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("vip", vip_plans))
    app.add_handler(CommandHandler("setlimit", set_limit))
    app.add_handler(CommandHandler("upload", upload_cmd))
    app.add_handler(CommandHandler("listdb", list_db))
    app.add_handler(CommandHandler("deletedb", delete_db))
    # Handler para receber documentos (upload de database)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("[SYSTEM_BOOT] Bot iniciado. Aguardando mensagens...")
    app.run_polling()

if __name__ == "__main__":
    main()
