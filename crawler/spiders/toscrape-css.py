# -*- coding: utf-8 -*-
import scrapy

# scrapy crawl toscrape-css -o jora-ml-4.csv -s JOBDIR=crawls/jora-ml-4

class ToScrapeCSSSpider(scrapy.Spider):
    name = "toscrape-css"
    start_urls = [
        'https://au.jora.com/j?l=Sydney+NSW&q=machine+learning&sa=110000&sp=facet_salary_min'
    ]
    base_url = 'https://au.jora.com'

    def parse(self, response):
        for job in response.css('#jobresults').css('.job'):
            rel_url = job.css(".jobtitle").css('a::attr(href)').extract_first()
            rel_url = rel_url.split('?')[0] if rel_url else None
            full_url = (self.base_url + rel_url) if rel_url else None
            item = {
                'title': job.css(".jobtitle::text").extract_first(),
                'url': full_url,
                'salary': job.css(".salary::text").extract_first(),
                'date': job.css(".date::text").extract_first(),
                'company': job.css(".company::text").extract_first(),
            }
            if full_url:
                yield scrapy.Request(full_url, callback=self.parse_job_page, meta=item)
            else:
                yield item

        next_page_url = response.css('.next_page').css('a::attr(href)').extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(self.base_url + next_page_url))

    def parse_job_page(self, response):
        item = response.meta
        item['description'] = '\n'.join(response.css('.summary p::text').extract())
        yield item