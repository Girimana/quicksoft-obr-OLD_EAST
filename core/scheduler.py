from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from invoice.views import send_invoice_offline
from stock.views import send_stock_offline
from pytz import timezone

def start_send_invoice_offline_job():
    scheduler = BackgroundScheduler({'apscheduler.timezone': timezone('Africa/Bujumbura')}  )

    scheduler.add_job(send_invoice_offline, 'interval', minutes=1)
    scheduler.add_job(send_stock_offline, 'interval', minutes=1)
     
    scheduler.start()
    

