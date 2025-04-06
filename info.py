import os

SESSION = "ftmbotzx"
API_ID = int(os.getenv("API_ID", 22141398))
API_HASH = os.getenv("API_HASH", '0c8f8bd171e05e42d6f6e5a6f4305389')
BOT_TOKEN = os.getenv("BOT_TOKEN", "8105194942:AAHisU5gxAc77O5qKoAZluI86w10s9MBV5o")
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1002613994353"))
DUMP_CHANNEL = int(os.getenv("DUMP_CHANNEL", "-1002613994353"))
PORT = int(os.getenv("PORT", "8080"))
FORCE_CHANNEL = int(os.getenv("FORCE_CHANNEL", "-1002087228619"))
HTTP_PROXY = ''
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ftm:ftm@cluster0.xotfi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
MONGO_NAME = os.getenv("MONGO_NAME", "Cluster0")
ADMINS = [7744665378]
DAILY_LIMITS = 10 
