import schedule
import threading
import logging
import traceback

class Scheduler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.is_running = False
        self.event = threading.Event()

    def start(self):
        self.is_running = True
        super().start()

    def terminate(self):
        self.is_running = False
        self.event.set()

    def run(self):
        logging.info("Scheduler started")
        try:
            while self.is_running:
                schedule.run_pending()
                self.event.wait(1)
            logging.info("Scheduler stopped")
        except Exception:
            logging.error(traceback.format_exc())
            self.is_running = False

    def getStateMetrics(self):
        return [
            "system_service_process{{type=\"scheduler\",}} {}".format("1" if self.is_running else "0")
        ]
