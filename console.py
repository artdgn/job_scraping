#!/usr/bin/env python

from argparse import ArgumentParser

from jobs_ranker.io import text
from jobs_ranker.scraping.crawling import CrawlProcess
from jobs_ranker.joblist.ranking import JobsRanker
from jobs_ranker.tasks.configs import TasksConfigsDao


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("-t", "--task-json", type=str, default="",
                        help="path to json file or task name with file in the ./data dir "
                             "that contains the task configuration")
    parser.add_argument("-s", "--scrape", action="store_true",
                        help="whether to scrape. default false")
    parser.add_argument("-c", "--no-http-cache", action="store_false",
                        help="whether to use http cache (helpful for debugging scraping). default true")
    parser.add_argument("-r", "--recalc", action="store_true",
                        help="whether to recalc model after every new label. default false")
    parser.add_argument("-n", "--no-dedup", action="store_true",
                        help="prevent deduplication of newest scrapes w/r to historic scrapes. default false")
    parser.add_argument("-a", "--assume-negative", action="store_true",
                        help="assume jobs left unlabeled previously as labeled negative. default false")
    return parser.parse_args()


def main():
    args = parse_args()

    task_chooser = text.TaskChooser(tasks_dao=TasksConfigsDao())
    task_config = task_chooser.load_or_choose_task(task_name=args.task_json)

    if args.scrape:
        crawl_proc = CrawlProcess(task_config=task_config,
                                  http_cache=not args.no_http_cache)
        crawl_proc.start()
        crawl_proc.join()

    ranker = JobsRanker(
        task_config=task_config,
        dedup_new=(not args.no_dedup),
        skipped_as_negatives=args.assume_negative)

    ranker.load_and_process_data(background=False)

    labeling_loop = text.LabelingLoop(ranker=ranker)

    labeling_loop.run_loop(recalc_everytime=args.recalc)


if __name__ == '__main__':
    main()