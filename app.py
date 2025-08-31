import os
import logging
import time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_binary  # ✅ this ensures chromedriver is in PATH

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Function to check PNR ---
def get_pnr_screenshot(pnr: str):
    """Navigate to Confirmtkt PNR page, take screenshot, and return filename."""
    options = Options()
    options.add_argument("--headless=new")  # modern headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")

    driver = webdriver.Chrome(options=options)  # ✅ No need to set Service()

    try:
        logging.info(f"Navigating to PNR page for {pnr}...")
        driver.get(f"https://www.confirmtkt.com/pnr-status/{pnr}")

        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='table-responsive pnr-status']")
                )
            )
            logging.info("PNR status table found, waiting a bit for rendering.")
            time.sleep(3)
        except Exception as e:
            logging.warning(f"PNR table not found in time. Screenshot anyway. Error: {e}")

        filename = f"pnr_{pnr}.png"
        driver.save_screenshot(filename)
        logging.info(f"Screenshot saved: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Error in get_pnr_screenshot({pnr}): {e}")
        return None
    finally:
        driver.quit()

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! Send me your 10-digit PNR number and I’ll check the status."
    )

async def handle_pnr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pnr = update.message.text.strip()

    if not pnr.isdigit() or len(pnr) != 10:
        await update.message.reply_text("⚠️ Please send a valid 10-digit PNR number.")
        return

    await update.message.reply_text(f"🔎 Checking status for PNR: {pnr} ...")
    logging.info(f"Received PNR {pnr} from user {update.message.from_user.id}")

    screenshot = get_pnr_screenshot(pnr)

    if screenshot:
        await update.message.reply_photo(photo=open(screenshot, "rb"))
        os.remove(screenshot)
        logging.info(f"Screenshot sent and deleted: {screenshot}")
    else:
        await update.message.reply_text(
            "❌ Could not fetch PNR status. Try again later."
        )
        logging.error(f"Failed to fetch/send screenshot for PNR {pnr}")

# --- Main ---
if __name__ == "__main__":
    print("🤖 Bot is running with webhook...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pnr))

    PORT = int(os.environ.get("PORT", 8080))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}",
    )
