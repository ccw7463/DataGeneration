from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer
from urllib.parse import urlparse, urlunparse, urljoin
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import json

def extract_info_from_url(full_url):
    """
        Des:
            URL에서 Base URL을 추출하는 함수
    """
    parsed_url = urlparse(full_url)  # URL을 파싱
    schema = parsed_url.scheme
    domain = parsed_url.netloc
    base_url = urlunparse((schema, domain, '', '', '', ''))  # Base URL만 재조합
    return {
        "schema":schema,
        "domain":domain,
        "base_url":base_url
    }
    
def extract_content(link:str) -> tuple[str, str]:
    """
        Des:
            주어진 링크에 대한 내용 추출하는 함수
    """
    loader = AsyncHtmlLoader(link)
    docs = loader.load()
    html2text = Html2TextTransformer()
    docs_transformed = html2text.transform_documents(docs,metadata_type="html")
    desc = docs_transformed[0].metadata.get('description',"")
    detailed_content = docs_transformed[0].page_content
    return desc,detailed_content

def initialize_browser():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('--window-size=1920,1080')

    try:
        home_path = os.path.expanduser('~')
        chrome_driver_path = os.path.join(home_path, '.wdm', 'drivers', 'chromedriver', 'linux64')
        latest_version = sorted(os.listdir(chrome_driver_path))[-1]  # 가장 최신 버전 선택
        chrome_driver_path = os.path.join(chrome_driver_path, latest_version, 'chromedriver')
        print("🖥ChromeDriver가 존재합니다.")
        browser = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
    except Exception as e:
        print("🖥ChromeDriver가 존재하지 않습니다. 설치과정을 진행합니다.")
        browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return browser

    
def load_sources(FILE_PATH):
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            SOURCES = json.load(f)
    else:
        SOURCES = []
    print(f"현재 DB에 저장된 데이터는 {len(SOURCES)}개 입니다.")  
    return SOURCES

def save_sources(FILE_NAME:str, SOURCES:list):
    with open(FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(SOURCES, f, ensure_ascii=False, indent=4)        
        

def get_dates_between(start_date: str, end_date: str) -> list:
    """
        Des:start_date와 end_date 사이의 모든 날짜를 리스트로 반환
        Args:
            start_date (str): 시작 날짜 (YYYY-MM-DD)
            end_date (str): 종료 날짜 (YYYY-MM-DD)
        Returns:
            list: 날짜 문자열 리스트 (YYYY-MM-DD 형식)
    """
    # 문자열을 datetime 객체로 변환
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    # 날짜 리스트 생성
    dates = []
    current = start
    
    # end 날짜도 포함하기 위해 다음날까지 반복
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
        
    return dates