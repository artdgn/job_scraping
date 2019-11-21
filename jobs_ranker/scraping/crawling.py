import datetime
import os
import subprocess

import pandas as pd
import pandas.errors

from jobs_ranker.tasks.configs import TaskConfig

from jobs_ranker import common
from jobs_ranker.utils.logger import logger


class CrawlProcess:

    def __init__(self, task_config: TaskConfig, http_cache=False):
        self.task_config = task_config
        self.http_cache = http_cache
        crawl_name = f'jora-{common.current_date()}'

        self.log_path = os.path.join(
            self.task_config.scrapy_log_dir,
            f'log-{common.current_timestamp()}.log')

        self.crawl_output_path = os.path.join(
            self.task_config.crawls_dir, f'{crawl_name}.csv')

        self.jobdir_path = os.path.join(
            self.task_config.crawl_job_dir, crawl_name)

        self.subproc = None

    def _settings_dict(self):
        return {
            'FEED_FORMAT': 'csv',
            'FEED_URI': f'file://{self.crawl_output_path}',
            'JOBDIR': self.jobdir_path,
            'LOG_FILE': self.log_path,
            'HTTPCACHE_ENABLED': self.http_cache
        }

    def start(self):
        joined_start_urls = ','.join(self.task_config.search_urls)

        commands = [
            'scrapy', 'crawl', 'jora-spider',
            '-a', f'start_urls="{joined_start_urls}"']
        for k, v in self._settings_dict().items():
            commands.extend(['-s', f'{k}="{v}"'])

        self.subproc = subprocess.Popen(
            ' '.join(commands),
            shell=True,
            cwd=os.path.dirname(__file__),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        logger.info(f'Started scraping task "{self.task_config.name}".\n\t'
                    f'check log file at {self.log_path}\n\t'
                    f'output file at {self.crawl_output_path}')

    def join(self):
        out, err = self.subproc.communicate()
        out = out.strip().decode()
        err = err.strip().decode()
        if out:
            logger.info(f'crawl process stdout:\n{out}')
        if err:
            logger.info(f'crawl process stderr:\n{err}')


class CrawlsFilesDao:

    @staticmethod
    def read_scrapy_file(filename):
        try:
            df = pd.read_csv(filename)
        except pandas.errors.EmptyDataError:
            return pd.DataFrame()
        else:
            drop_cols = ([col for col in df.columns
                          if col.startswith('download_')] + ['depth'])
            df.drop(drop_cols, axis=1, inplace=True, errors='ignore')
            df['scraped_file'] = filename
            return df

    @staticmethod
    def all_crawls(task_config: TaskConfig,
                   raise_on_missing=True,
                   ignore_empty=True):
        all_crawls = [os.path.join(task_config.crawls_dir, f)
                      for f in sorted(os.listdir(task_config.crawls_dir))]

        if ignore_empty:
            all_crawls = [path for path in all_crawls if os.stat(path).st_size]

        if raise_on_missing and not all_crawls:
            raise FileNotFoundError(
                f'No crawls found for task "{task_config.name}", '
                f'please run scraping.')
        return all_crawls

    @classmethod
    def days_since_last_crawl(cls, task_config: TaskConfig):
        latest = cls.all_crawls(task_config)[-1]
        date = os.path.splitext(latest)[0][-10:]
        current_date = datetime.datetime.now().date().isoformat()
        return (pd.to_datetime(current_date) - pd.to_datetime(date)).days

    @classmethod
    def rows_in_file(cls, filepath):
        return len(cls.read_scrapy_file(filepath))
