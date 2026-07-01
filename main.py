import os
import json
import uuid
import re
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

# =====================================
# CONFIGURAÇÕES
# =====================================

# Cole aqui o seu token NOVO (depois de revogar o antigo no @BotFather)
TOKEN = "8808956054:AAGVHHfZc52vhlXg1k7HnKIEERgScbbJTS8"

MEU_ID = 8177674216
MEU_GRUPO = -1003857456899

# Link de convite do grupo (mostrado quando alguém usa o bot no PV)
LINK_GRUPO = "https://t.me/+LY4WB3EYA3IyZDAx"

# Site/divulgação do bot (mostrado quando alguém usa o bot no PV)
SITE_BOT = "https://cxanalytica.com/"

ARQUIVO = "Snow249.txt"
LIMITE = 400
ARQUIVO_PROGRESSO = "progresso.json"
ARQUIVO_CACHE_DIARIO = "cache_usuarios_diario.json"


def normalizar_url(url: str) -> str:
    url = url.lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    url = url.split('/')[0]
    url = re.sub(r'\.(com|com\.br|net|org|io|gov|edu|me|info|tv|site)$', '', url)
    return url


def extrair_email_pass(linha: str) -> str:
    """
    Melhoria na extração:
    Geralmente logs vêm como url:user:pass ou user:pass:url.
    Esta função tenta identificar o par email:pass (contendo @) ou apenas o par user:pass.
    """
    # Tenta separar por ':' ou '|' que são os separadores mais comuns
    partes = re.split(r'[:|]', linha)
    
    # Se tiver pelo menos 2 partes
    if len(partes) >= 2:
        # Procura por uma parte que contenha '@' (email)
        for i in range(len(partes) - 1):
            if "@" in partes[i]:
                # Retorna o email e a próxima parte (senha)
                return f"{partes[i].strip()}:{partes[i+1].strip()}"
        
        # Se não achou @, mas tem 3 partes (ex: url:user:pass), tenta pegar as duas últimas
        if len(partes) >= 3 and (partes[0].startswith("http") or "." in partes[0]):
            return f"{partes[1].strip()}:{partes[2].strip()}"
            
        # Padrão fallback: retorna as duas primeiras partes
        return f"{partes[0].strip()}:{partes[1].strip()}"
        
    return linha


def carregar_json(caminho):
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def salvar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


progresso_pesquisas = carregar_json(ARQUIVO_PROGRESSO)
cache_usuarios = carregar_json(ARQUIVO_CACHE_DIARIO)


async def permitido(update: Update):
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user: return False
    return (chat.id == user.id and user.id == MEU_ID) or (chat.id == MEU_GRUPO)


async def bloquear_pv(update: Update):
    chat = update.effective_chat
    user = update.effective_user
    if chat.id == user.id and user.id != MEU_ID:
        texto = (
            "🚫 Não é permitido usar este bot no privado.\n\n"
            "👉 Use os comandos dentro do nosso grupo:\n"
            f"{LINK_GRUPO}\n\n"
            "🌐 Conheça também o site oficial:\n"
            f"{SITE_BOT}"
        )
        await update.message.reply_text(texto, disable_web_page_preview=True)
        return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_pv(update) or not await permitido(update): return
    await update.message.reply_text("🤖 **Bot Online!**\n\nUse: `/search <url>`", parse_mode="Markdown")


async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_pv(update) or not await permitido(update): return
    if not context.args:
        await update.message.reply_text("Uso: /search <url>")
        return

    pesquisa_limpa = normalizar_url(" ".join(context.args))
    
    keyboard = [
        [
            InlineKeyboardButton("📧 Email:Pass", callback_data=f"login|{pesquisa_limpa}"),
            InlineKeyboardButton("🌐 ULP (Completo)", callback_data=f"ulp|{pesquisa_limpa}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🔎 **Domínio:** `{pesquisa_limpa}`\n\nEscolha o formato do resultado:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|")
    modo = data[0]
    pesquisa_limpa = data[1]
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    hoje = date.today().isoformat()
    
    chave_cache_user = f"{user_id}|{pesquisa_limpa}|{modo}"
    chave_progresso_global = f"{chat_id}|{pesquisa_limpa}"
    
    cache = cache_usuarios.get(chave_cache_user)
    if cache and cache.get("data") == hoje:
        token = cache["token"]
        arquivo_saida = f"resultado_{token}.txt"
        with open(arquivo_saida, "w", encoding="utf-8") as out:
            out.write(cache["conteudo"])
            
        legenda = (
            f"♻️ **Resultado Reutilizado**\n\n"
            f"🆔 Token: {token}\n"
            f"🔍 Domínio: {pesquisa_limpa}\n"
            f"⚙️ Modo: {'Email:Pass' if modo == 'login' else 'ULP'}\n"
            f"📊 Total na base: {cache['total_exibir']}\n"
            f"📄 {cache['qtd_mostrada']} resultados"
        )
        
        await query.message.reply_document(document=open(arquivo_saida, "rb"), filename=arquivo_saida, caption=legenda, parse_mode="Markdown")
        os.remove(arquivo_saida)
        return

    status_msg = await query.message.reply_text(f"⏳ Processando {modo.upper()} para `{pesquisa_limpa}`...", parse_mode="Markdown")

    try:
        encontrados = []
        with open(ARQUIVO, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                if pesquisa_limpa in linha.lower():
                    encontrados.append(linha.strip())

        total = len(encontrados)
        if total == 0:
            await status_msg.edit_text(f"❌ Nenhum resultado para '{pesquisa_limpa}'.")
            return

        ja_consumidos = progresso_pesquisas.get(chave_progresso_global, 0)
        if ja_consumidos >= total: ja_consumidos = 0

        mostrar_bruto = encontrados[ja_consumidos : ja_consumidos + LIMITE]
        
        # APLICA A EXTRAÇÃO DE EMAIL:PASS SE O MODO FOR LOGIN
        if modo == "login":
            mostrar = []
            for l in mostrar_bruto:
                mostrar.append(extrair_email_pass(l))
        else:
            mostrar = mostrar_bruto
            
        token = uuid.uuid4().hex.lower()
        total_exibir = "5000+" if total > 5000 else str(total)
        
        cabecalho = (
            f"Token: {token}\nDomínio: {pesquisa_limpa}\nModo: {modo.upper()}\n"
            f"Total: {total_exibir}\nResultados: {len(mostrar)}\n" + "="*30 + "\n\n"
        )
        conteudo_completo = cabecalho + "\n".join(mostrar)

        cache_usuarios[chave_cache_user] = {
            "data": hoje, "token": token, "total_exibir": total_exibir,
            "qtd_mostrada": len(mostrar), "conteudo": conteudo_completo
        }
        salvar_json(ARQUIVO_CACHE_DIARIO, cache_usuarios)
        
        progresso_pesquisas[chave_progresso_global] = ja_consumidos + len(mostrar_bruto)
        salvar_json(ARQUIVO_PROGRESSO, progresso_pesquisas)

        arquivo_saida = f"resultado_{token}.txt"
        with open(arquivo_saida, "w", encoding="utf-8") as out:
            out.write(conteudo_completo)

        legenda = (
            f"✅ Pesquisa concluída!\n\n🆔 Token: {token}\n🔍 Domínio: {pesquisa_limpa}\n"
            f"⚙️ Modo: {modo.upper()}\n📊 Total na base: {total_exibir}\n📄 {len(mostrar)} resultados"
        )

        await status_msg.delete()
        await query.message.reply_document(document=open(arquivo_saida, "rb"), filename=arquivo_saida, caption=legenda, parse_mode="Markdown")
        os.remove(arquivo_saida)

    except Exception as e:
        await status_msg.edit_text(f"Erro: {e}")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("search", logs))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Bot iniciado com botões e extração corrigida!")
    app.run_polling()

if __name__ == "__main__":
    main()
