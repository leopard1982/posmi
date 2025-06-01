from apscheduler.schedulers.background import BackgroundScheduler
from .jobs import updateKuota

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(updateKuota,'cron',month="1-12",day="1",hour="0",minute="1")
    scheduler.start()