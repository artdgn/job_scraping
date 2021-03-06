import abc
import os

import pandas as pd

from jobs_ranker.config.common import LABELED_ROOT_DIR
from jobs_ranker.utils.instrumentation import LogCallsTimeAndOutput
from jobs_ranker.utils.logger import logger


class LabelsAPI(abc.ABC):
    url_col = 'url'
    label_col = 'label'
    timestamp_col = 'timestamp'
    pos_label = 'y'
    neg_label = 'n'

    @abc.abstractmethod
    def is_valid_label(self, label: str):
        return False

    @abc.abstractmethod
    def add_label(self, url, label):
        pass

    @abc.abstractmethod
    def export_df(self):
        return pd.DataFrame()

    @abc.abstractmethod
    def export_html_table(self):
        return ''


class LabeledJobs(LabelsAPI, LogCallsTimeAndOutput):

    def __init__(self, task_name, dup_dict=None):
        super().__init__()
        self.filename = self._task_name_to_filename(task_name)
        self.dup_dict = dup_dict if dup_dict is not None else {}
        self._df = None
        self.load()

    @staticmethod
    def _task_name_to_filename(task_name):
        return os.path.join(LABELED_ROOT_DIR, f'{task_name}.csv')

    def save(self):
        self._df.to_csv(self.filename, index=None)

    def load(self):
        if os.path.exists(self.filename):
            self._df = pd.read_csv(self.filename). \
                drop_duplicates(subset=[self.url_col], keep='last')
        else:
            self._df = pd.DataFrame({self.url_col: [], self.label_col: [], self.timestamp_col: []})

    def _urls_with_dups(self, url):
        return self.dup_dict.get(url, [url])

    def is_labeled(self, url):
        return self._df[self.url_col].isin(self._urls_with_dups(url)).any()

    def add_label(self, url, label):
        if self.is_valid_label(label):
            self.load()
            self._df = self._df.append(
                pd.DataFrame({self.url_col: [url],
                              self.label_col: [label],
                              self.timestamp_col: [str(pd.datetime.now())]}))
            self.save()
            logger.info(f'Added label: {label} for {url}')

    def is_valid_label(self, label: str):
        try:
            number = float(label.
                           replace(self.pos_label, '1.0').
                           replace(self.neg_label, '0.0'))
            if not 0 <= number <= 1:
                raise ValueError
            return True

        except ValueError:
            logger.error(f'Invalid label : {label}')
            return False

    def __repr__(self):
        total = len(self._df)
        neg = (self._df.loc[:, self.label_col] == self.neg_label).sum()
        pos = (self._df.loc[:, self.label_col] == self.pos_label).sum()
        return (f'LabeledJobs: {total} labeled ({neg / total:.1%} neg, '
                f'{pos / total:.1%} pos, '
                f'{(total - pos - neg) / total:.1%} partial relevance)')

    def export_df(self, dedup=True):

        df = self._df.copy()

        df[self.label_col] = df[self.label_col]. \
            replace(self.pos_label, '1.0'). \
            replace(self.neg_label, '0.0'). \
            astype(float)

        if dedup:
            all_urls = df[self.url_col].values
            for url in all_urls:
                dup_urls = self.dup_dict.get(url, [])
                if (len(dup_urls) >= 2  # has dups
                    and df[self.url_col].eq(url).any()  # url still here
                    and df[self.url_col].isin(dup_urls).sum() >= 2  # dups are still here
                ):
                    dups_rows = df.loc[df[self.url_col].isin(dup_urls)]
                    # keep last
                    remove_urls = dups_rows.iloc[:-1][self.url_col].values
                    df = df.loc[~df[self.url_col].isin(remove_urls)]
        return df

    def export_html_table(self):
        ## simpler version:
        # return df.to_html(na_rep='', render_links=True)
        return (self.export_df()
                .fillna('')
                .style
                .format({'url': lambda l: f'<a href="{l}" target="_blank">{l}</a>'})
                .set_table_attributes('class="table-sm table-bordered table-hover table-striped"')
                .background_gradient(cmap='Purples', subset=['label'])
                .render())


def labels_history_table(task_name):
    labeler = LabeledJobs(task_name=task_name)
    labeler.load()
    return labeler.export_html_table()