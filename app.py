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
import time
from dotenv import load_dotenv

# Configure logging to see more details
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Function to check PNR ---
def get_pnr_screenshot(pnr):
    """
    Navigates to the PNR status page, takes a screenshot, and returns the filename.
    
    This version configures the Chrome driver to work on a Render.com environment
    by specifying the binary location directly, which is handled by the build script.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")

    # Set the path to the pre-installed Chrome binary
    options.binary_location = "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"
    
    # Specify the driver's path directly, which is also available on Render
    service = Service("/opt/render/project/.render/chrome/opt/google/chrome/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        logging.info(f"Navigating to PNR page for {pnr}...")
        driver.get(f"https://www.confirmtkt.com/pnr-status/{pnr}")
        
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='table-responsive pnr-status']"))
            )
            logging.info("PNR status table found. Waiting for a moment to let content load.")
            time.sleep(5)
        except Exception as e:
            logging.warning(f"PNR status table not found within timeout. Taking screenshot of the current page. Error: {e}")
        
        filename = f"pnr_{pnr}.png"
        driver.save_screenshot(filename)
        driver.quit()
        logging.info(f"Screenshot saved as {filename}")
        return filename

    except Exception as e:
        logging.error(f"Error in PNR fetch for {pnr}: {e}")
        driver.quit()
        return None

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me your PNR number and I will check the status for you.")

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
        os.remove(screenshot)  # cleanup
        logging.info(f"Screenshot sent to user. Cleaned up file {screenshot}")
    else:
        await update.message.reply_text("❌ Failed to fetch PNR status. This PNR may not be valid, or the website is currently unavailable.")
        logging.error(f"Failed to fetch and send screenshot for PNR {pnr}.")


if __name__ == "__main__":
    print("🤖 Bot is running with webhook...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pnr))

    # Get the PORT Render provides
    PORT = int(os.environ.get("PORT", 8080))

    # Start webhook (replace YOUR_DOMAIN with your Render domain)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}"
    )







