from src.Fetch_Data.sec_crawling import SEC_Crawler
from src.Fetch_Data.sec_db import SEC_Database
from src.Fetch_Data.sec_parsing import SEC_Parser

class SEC_Fetcher:
    def __init__(self, ticker : str):
        self.ticker = ticker
        self.crawler = SEC_Crawler()
        self.database = SEC_Database()
    
    def fetch_sec_data(self):
        new_filing_paths = []
        result = self.crawler.crawl_filings_in_window(ticker = self.ticker, only_today = False)
        for metadata, file_path in result:

            if metadata["form"] == "4":
                parser = SEC_Parser(self.ticker, file_path)
                filename = parser.parse_form_4()
                new_filing_paths.append(filename)
            elif metadata["form"] == "144":
                parser = SEC_Parser(self.ticker, file_path)
                filename = parser.parse_form_144()
                new_filing_paths.append(filename)
            else:
                print(f"❌ 지원하지 않는 폼: {metadata['form']}")
                continue
        print(f"✅ SEC 데이터 파싱 완료: {len(new_filing_paths)}개")

        return new_filing_paths

if __name__ == "__main__":
    fetcher = SEC_Fetcher("AAPL")
    new_filing_paths = fetcher.fetch_sec_data()
    for i, path in enumerate(new_filing_paths, 1):
        print(f"{i}/{len(new_filing_paths)}: {path}")