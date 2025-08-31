import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Function to check PNR ---
def get_pnr_screenshot(pnr):
    options = Options()
    options.add_argument("--headless=new")   # ✅ modern headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")

    # ✅ Let webdriver-manager download correct ChromeDriver version
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        logging.info(f"Navigating to PNR page for {pnr}...")
        driver.get(f"https://www.confirmtkt.com/pnr-status/{pnr}")

        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='table-responsive.pnr-status']"))
            )
            logging.info("PNR status table found. Waiting to load...")
            time.sleep(5)
        except Exception as e:
            logging.warning(f"PNR table not found in time. Error: {e}")

        filename = f"pnr_{pnr}.png"
        driver.save_screenshot(filename)
        driver.quit()
        return filename

    except Exception as e:
        logging.error(f"Error fetching PNR {pnr}: {e}")
        driver.quit()
        return None

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me your PNR number and I’ll check the status.")

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
    else:
        await update.message.reply_text("❌ Failed to fetch PNR status. Please try again later.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pnr))

    PORT = int(os.environ.get("PORT", 8080))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}"
    )
