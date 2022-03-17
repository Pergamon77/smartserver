import threading
import glob
import os
from pathlib import Path
from datetime import datetime

from smartserver.github import GitHub

from lib import service
from lib import job
from lib import git

from config import config
from lib import status

repository_owner = GitHub.getRepositoryOwner(config.repository_url)

class JobWatcher(): 
    def __init__(self, logger, handler ):
        self.logger = logger
        self.handler = handler
        
        self.terminated = False
        self.state = None
        self.initState()
        
        self.all_jobs = []
        self.running_jobs = {}
        self.last_mtime = 0
        self.initJobs()
        
        self.condition = threading.Condition()
        self.lock = threading.Lock()

        thread = threading.Thread(target=self._jobWatcher, args=())
        thread.start()
        
    def terminate(self):
        self.terminated = True
        with self.condition:
            self.condition.notifyAll()
        
    def changedJobs(self, event):
        self.lock.acquire()
        try:
            self.logger.info("Job changed")
            self.initJobs()
        finally:
            self.lock.release()
        with self.condition:
            self.condition.notifyAll()

    def changedState(self, event):
        self.lock.acquire()
        try:
            self.logger.info("State changed")
            self.initState()
        finally:
            self.lock.release()
        with self.condition:
            self.condition.notifyAll()

    def initState(self):
        self.state = status.getState(config.status_file)
        
    def initJobs(self):
        jobs = glob.glob(u"{}*.log".format(config.log_dir))
        all_jobs = []
        running_jobs = {}
        for name in jobs:
            details = job.getLogFileDetails(name)
            subject = details["subject"]
            if subject[-1:] == "_":
                subject = u"{}...".format(subject[:-1])
            subject = subject.replace("_", " ")
            all_jobs.append({
                "author": details["author"].replace("_", " "),
                "branch": details["branch"],
                "config": details["config"],
                "deployment": details["deployment"],
                "duration": details["duration"],
                "git_hash": details["git_hash"],
                "state": details["state"],
                "subject": subject,
                "date": details["date"],
                "timestamp": datetime.timestamp(datetime.strptime(details["date"],"%Y.%m.%d_%H.%M.%S"))
            })
            if details["state"] == "running":
                running_jobs[name] = details
        self.all_jobs = all_jobs
        self.running_jobs = running_jobs
        self.last_mtime = round(datetime.timestamp(datetime.now()),3)
        
        self.logger.info(self.last_mtime)
                        
    def isJobRunning(self):
        return self.state is not None and self.state["status"] == "running";

    def _jobWatcher(self):
        self._cleanJobs()

        while not self.terminated:
            job_is_running = self.isJobRunning()
            if job_is_running and service.getPid() is None and datetime.timestamp(datetime.now()) - self.handler.getFileModificationTime(config.status_file) > 3:
                self.logger.error("Job crash detected. Marked as 'crashed' now and check log files.")
                self._cleanState(status)
            else:
                self._cleanJobs()
            
            with self.condition:
                self.condition.wait( 5 if len(self.running_jobs) > 0 or job_is_running else 600 )
                
    def _cleanState(self, status):
        self.lock.acquire()
        try:
            status.setState(config.status_file,u"crashed")
        finally:
            self.lock.release()

    def _cleanJobs(self):
        invalid_jobs = []
        git_hashes = {}
        
        for name in self.running_jobs:
            job = self.running_jobs[name]
            if self.isJobRunning() and job["config"] == self.state["config"] and job["deployment"] == self.state["deployment"] and job["git_hash"] == self.state["git_hash"]:
                continue
                    
            invalid_jobs.append(name)
            
            if job["git_hash"] not in git_hashes:
                git_hashes[job["git_hash"]] = []
                
            git_hashes[job["git_hash"]].append(job["deployment"])
            
        if len(invalid_jobs) > 0:
            self.lock.acquire()
            try:
                if config.access_token != "" and self.state is not None:
                    # process git hashes
                    for git_hash in git_hashes: 
                        self.logger.info("Clean states of git hash '{}'".format(git_hash))
                        for deployment in git_hashes[git_hash]:
                            GitHub.setState(repository_owner,config.access_token,git_hash,"error", deployment,"Build crashed")
                            GitHub.cancelPendingStates(repository_owner, config.access_token, git_hash, "Build skipped")

                # process logfiles
                for name in invalid_jobs:
                    self.logger.info("Clean file '{}'".format(name))
                    os.rename(name, name.replace("-running-","-crashed-"))
            finally:
                self.lock.release()
            
            #if service.getPid() is not None:
            #    service.cleanRunningJobs("all")
            
    def getJobs(self):
        return self.all_jobs
                            
    def getLastRefreshAsTimestamp(self):
        return self.last_mtime