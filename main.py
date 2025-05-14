import logging
import os
from dotenv import load_dotenv

# Attempt to import DuneClient, error clearly if missing
try:
    from dune_client.client import DuneClient
    from dune_client.query import QueryBase
    from dune_client.types import QueryParameter
except ImportError:
    raise ImportError(
        "dune-client library not found. "
        "Please install it with `pip install dune-client` in your virtual environment."
    )

import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Silence verbose logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Load environment variables from .env
load_dotenv()

DUNE_API_KEY = os.getenv("DUNE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
try:
    DUNE_QUERY_ID = int(os.getenv("DUNE_QUERY_ID"))
except (TypeError, ValueError):
    DUNE_QUERY_ID = None

if not all([DUNE_API_KEY, TELEGRAM_TOKEN, DUNE_QUERY_ID]):
    raise RuntimeError(
        "Set DUNE_API_KEY, TELEGRAM_BOT_TOKEN, and DUNE_QUERY_ID in your .env"
    )

# Initialize Dune client
dune = DuneClient(DUNE_API_KEY)

# Whitelisted user and group IDs
ALLOWED_IDS = {1273464377, 6484752597, -1002294232925}

# /analyze command handler
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the user or group is allowed
    chat_id = update.effective_chat.id
    if chat_id not in ALLOWED_IDS:
        return
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            """👋 Welcome!

Use /analyze <token_mint> to check if any of the first 100 buyers of a token are still in the top 100 holders.

Example:
/analyze 7cEgQdp8JTXvBrpjSzji7bLEeCHWENRwX62B2Ep97k5H"""
        )
        return

    token = context.args[0]
    await update.message.reply_text(
        f"🔍 Running analysis for `{token}`…", parse_mode="Markdown"
    )

    try:
        # Build parameterized query
        query = QueryBase(
            query_id=DUNE_QUERY_ID,
            params=[QueryParameter.text_type(name="token_mint", value=token)]
        )
        df = dune.run_query_dataframe(query)

        if df.empty:
            await update.message.reply_text("No matching holders found.")
            return

        # Build new styled horizontal message
        lines = ["*FIRST 100 BUYERS IN TOP 100 HOLDER POSITION*\n"]
        for _, r in df.iterrows():
            wallet = r['wallet']
            rank = int(r['current_rank'])
            initial = f"{int(float(r['initial_balance'])):,}"
            current = f"{int(float(r['current_balance'])):,}"
            link = f"[{wallet}](https://gmgn.ai/sol/address/{wallet})"
            lines.append(
                f"*Rank {rank} - Top 100 Holders*\n"
                f"*Wallet* - {link}\n"
                f"*Initial* - {initial}\n"
                f"*Current* - {current}\n"
            )

        message = "\n".join(lines)
        await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as error:
        await update.message.reply_text(f"❗ Error querying Dune: {error}")

# /start and /help command handler
async def start_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in ALLOWED_IDS:
        return
    await update.message.reply_text(
        """👋 Welcome!
    
    Use /analyze <token_mint> to check if any of the first 100 buyers of a token are still in the top 100 holders.
    
    Example:
    /analyze 7cEgQdp8JTXvBrpjSzji7bLEeCHWENRwX62B2Ep97k5H"""
    )

# Bot startup
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("analyze", analyze_command))
    print("🤖 Bot started. Use /analyze <token_mint> to run your Dune query.")
    app.run_polling()
