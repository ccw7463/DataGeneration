import feedparser
from urllib.parse import quote
from typing import List, Dict, Optional
from utils.util import initialize_browser, extract_info_from_url, extract_content
from datetime import datetime
import time

class RSSGetter:
    """
        Des:
            Google News에서 뉴스를 검색하고 특정 기간에 해당하는 뉴스를 필터링하는 클래스.
    """

    def __init__(self):
        self.base_url = "https://news.google.com/rss"
        self.browser = initialize_browser()
        
    def __call__(self,
                 start_date:str=None,
                 end_date:str=None,
                 en_keyword:str="latest shipping news",
                 ko_keyword:str="최신 해운 뉴스",
                 k:int=5):
        """
            Des:
                특정 키워드에 대한 뉴스 자료들을 검색하는 함수
            Args:
                en_keyword (str): 영어 키워드
                ko_keyword (str): 한국어 키워드
                k (int): 검색할 뉴스 개수
                start_date (str): 시작 날짜
                end_date (str): 종료 날짜
            Returns:
                tuple: 영어 뉴스와 한국어 뉴스의 리스트
        """
        self.k = k
        self.start_date = start_date
        self.end_date = end_date
        if self.start_date is None:
            self.start_date = self.BEFORE_A_WEEK_BASE_DATE
        if self.end_date is None:
            self.end_date = self.BASE_DATE
        en_news = self.search_by_keyword(keyword=en_keyword,lang="en")
        ko_news = self.search_by_keyword(keyword=ko_keyword,lang="ko")
        return en_news,ko_news
    
    def set_language(self,
                     lang: str = "ko"):
        """
            Des:
                언어 설정 함수
            Args:
                lang (str): 언어
        """
        if lang == "ko":
            self.hl = "ko"
            self.gl = "KR"
            self.ceid = "KR:ko"
            print("### 🚩 한국어로 작성된 뉴스 자료들을 검색합니다.")
        else:
            self.hl = "en"
            self.gl = "US"
            self.ceid = "US:en"
            print("### 🚩 영어로 작성된 뉴스 자료들을 검색합니다.")
            
    def search_by_keyword(self,
                          keyword: Optional[str] = None,
                          lang: str = "ko") -> List[Dict[str, str]]:
        """
            Des:
                특정 키워드에 대한 뉴스 자료들을 검색하는 함수
            Args:
                keyword (str): 검색할 키워드
                lang (str): 언어
            Returns:
                list: 검색된 뉴스 자료들의 리스트
        """
        self.set_language(lang=lang)
        
        # RSS URL 생성
        if keyword:
            encoded_keyword = quote(keyword)
            self.url = f"{self.base_url}/search?q={encoded_keyword}&hl={self.hl}&gl={self.gl}&ceid={self.ceid}"
        else:
            self.url = f"{self.base_url}?hl={self.hl}&gl={self.gl}&ceid={self.ceid}"

        # RSS URL에서 뉴스 데이터를 가져옵니다.
        self.fetch_news() 
        
        # 특정 날짜 범위에 해당하는 뉴스 항목만 필터링합니다.
        if self.start_date or self.end_date:
            self.filter_by_date()

        # 뉴스 항목에서 필요한 정보만 추출하여 딕셔너리 형태로 반환합니다.
        self.collect_news()
        print(f"{len(self.collected_news)}개의 뉴스 자료를 수집하였습니다.")
        return self.collected_news


    def fetch_news(self):
        """
            Des:
                RSS URL에서 뉴스 데이터를 가져오는 함수
        """
        self.news_list = feedparser.parse(self.url).entries[:self.k]

    def filter_by_date(self):
        """
            Des:
                뉴스 항목에서 특정 날짜 범위에 해당하는 항목만 필터링합니다.
        """
        start_date_obj = datetime.strptime(self.start_date, "%Y-%m-%d") if self.start_date else None
        end_date_obj = datetime.strptime(self.end_date, "%Y-%m-%d") if self.end_date else None
        filtered_news = []
        for news in self.news_list:
            published_date = datetime.strptime(news.get("published", ""), "%a, %d %b %Y %H:%M:%S %Z")
            if start_date_obj and published_date < start_date_obj:
                continue
            if end_date_obj and published_date > end_date_obj:
                continue
            filtered_news.append(news)
        self.news_list = filtered_news

    def collect_news(self):
        """
            Des:
                뉴스 항목에서 필요한 정보만 추출하여 딕셔너리 형태로 반환합니다.
        """
        self.collected_news = []
        for news in self.news_list:
            ref = news.get("source", {}).get("title")  # RSS의 source.title 필드를 사용
            if not ref:  # source 정보가 없는 경우 URL에서 도메인 추출
                ref = extract_info_from_url(news.get("link"))['domain']
            
            link = self.get_redirected_url(news.get("link"))
            self.collected_news.append({
                "ref": ref,
                "date": news.get("published"),
                "link": link,
                "title": news.get("title"),
                "content": extract_content(link)
            })
    
    
    def get_redirected_url(self, 
                           initial_url: str) -> str:
        """
            Des:
                초기 URL에서 리다이렉트된 URL을 가져오는 함수
            Args:
                initial_url (str): 초기 URL
            Returns:
                str: 리다이렉트된 URL
        """
        self.browser.get(initial_url)
        time.sleep(5)  # JavaScript가 실행될 시간을 충분히 제공 (수정필요)
        
        if self.browser.current_url == initial_url:
            return self.browser.current_url
        else:
            return self.browser.current_url
        
    