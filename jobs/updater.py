from apscheduler.schedulers.background import BackgroundScheduler
from .jobs import updateKuota,delHistoryDownload

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(updateKuota,'cron',month="1-12",day="1",hour="0",minute="1")
    scheduler.add_job(delHistoryDownload,'interval',seconds=60*60*24) #hapus file download_history setiap 24 jam sekali
    scheduler.start()
    