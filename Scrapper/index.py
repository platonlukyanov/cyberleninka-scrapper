import json
from bs4 import BeautifulSoup
import requests
from dataclasses import dataclass, asdict
from dacite import from_dict
from tqdm import tqdm
from loguru import logger
import time

logger.remove()
logger.add("log.log", level="DEBUG")

HEADERS = {
        "accept": "*/*",
        "accept-language": "en-GB-oxendict,en;q=0.9",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Linux\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
}

BASE_URL = "https://cyberleninka.ru"
@dataclass
class Catalog:
    id: int
    alias_name: str
    acronym: str

@dataclass
class Article:
    name: str
    annotation: str
    link: str
    authors: list[str] | None
    year: int
    journal: str
    journal_link: str
    ocr: list[str]
    catalogs: list[Catalog] | None

@dataclass
class ArticleDetails:
    views: int | None
    downloads: int | None
    doi: str | None
    research_area: str | None
    key_words: list[str] | None

@dataclass
class ArticleDOIDetails:
    indexed_datetime: str | None
    reference_count: int | None
    volume: int | None
    is_referenced_by_count: int | None

@dataclass
class FullArticle(Article, ArticleDetails, ArticleDOIDetails):
    pass

@dataclass
class SearchResult:
    found: int
    articles: list[Article]

@dataclass
class DetailedResult:
    articles: list[FullArticle]

@dataclass
class Journal:
    name: str
    link: str | None
    views: int | None
    downloads: int | None
    hirsh_index: int | None
    articles_count: int | None
    catalogs: list[str] | None

@dataclass
class Journals:
    journals: list[Journal]

def fetch_articles_list(from_index: int = 0, limit: int = 1000) -> SearchResult:
    url = "https://cyberleninka.ru/api/search"
    
    data = {
        "mode": "articles",
        "q": "психические заболевания",
        "size": limit,
        "from": from_index,
        "year_from": 2024,
        "year_to": 2024,
        "catalogs": [8, 2, 14, 15, 23]
    }
    headers = {**HEADERS, "content-type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response_json = response.json()

    if not "articles" in response_json:
        logger.debug(response.text)
    search_result = SearchResult(found=response_json["found"], articles=[Article(**article) for article in response_json["articles"]])
    return search_result

def dump_dataclass(dc: dataclass, filename: str = "search_result.json"):
    json_search_result = json.dumps(asdict(dc), indent=4, ensure_ascii=False)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(json_search_result)   

def load_articles_list(filename: str) -> SearchResult:
    with open(filename, "r", encoding="utf-8") as f:
        articles_list_obj = json.load(f)
        search_result = from_dict(SearchResult, articles_list_obj)
    return search_result

def fetch_article_details(url: str) -> ArticleDetails:
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, "html.parser")
    if soup.find(title="Просмотры") is None:
        views = None
    else:
        views = int(soup.find(title="Просмотры").text)
    if soup.find(title="Загрузки") is None:
        downloads = None
    else:
        downloads = int(soup.find(title="Загрузки").text)
    
    if soup.find(string="Область наук") is None:
        research_area = None
    else:
        research_area = soup.find(string="Область наук").parent.parent.find("a").text
    keywords = [el.text for el in soup.find_all(title="Найти все статьи с этим ключевым словом")]
    if (soup.select_one('.label-doi') is None):
        doi = None
    else:
        doi = soup.select_one('.label-doi').attrs['title'].replace("Статье выдан DOI: ", "")

    return ArticleDetails(views=views,
                          downloads=downloads,
                          research_area=research_area,
                          key_words=keywords,
                          doi=doi)

def fetch_article_doi_details(doi: str) -> ArticleDetails:
    doi_first_part = doi.split("/")[0]
    doi_second_part = doi.split("/")[1]
    url = f"https://api.crossref.org/works/{doi_first_part}/{doi_second_part}"
    response = requests.get(url)

    if response.status_code != 200:
        logger.error(f"Error fetching article details for DOI {doi}. Response code: {response.status_code}")
        return ArticleDOIDetails(indexed_datetime=None,
                                 reference_count=None,
                                 volume=None,
                                 is_referenced_by_count=None)

    response_json = response.json()
    article_doi_details = ArticleDOIDetails(indexed_datetime=response_json["message"]["indexed"]["date-time"] if "indexed" in response_json["message"] else None,
                                            reference_count=response_json["message"]["reference-count"] if "reference-count" in response_json["message"] else None,
                                            volume=response_json["message"]["volume"] if "volume" in response_json["message"] else None,
                                            is_referenced_by_count=response_json["message"]["is-referenced-by-count"] if "is-referenced-by-count" in response_json["message"] else None)
    return article_doi_details

def fetch_full_article(article: Article) -> FullArticle:
    article_details = fetch_article_details(BASE_URL + article.link)
    if article_details.doi is None:
        article_doi_details = ArticleDOIDetails(
            indexed_datetime=None,
            reference_count=None,
            volume=None,
            is_referenced_by_count=None
        )
    else: article_doi_details = fetch_article_doi_details(article_details.doi)
    full_article = FullArticle(**article.__dict__, **article_details.__dict__, **article_doi_details.__dict__)
    return full_article

def fetch_journal(journal_link: str) -> Journal:
    url = BASE_URL + journal_link
    html_text = requests.get(url, headers=HEADERS).text
    soup = BeautifulSoup(html_text, "html.parser")
    if soup.find(title="Просмотрели статей") is None:
        print(soup.text)
        print(url)
    views = int(soup.find(title="Просмотрели статей").select_one("span").text)
    downloads = int(soup.find(title="Скачали статей").select_one("span").text)
    hirsh_index = int(soup.find(title="Индекс Хирша").select_one("span").text)

    articles_count = int(soup.select_one(".right-label").text.replace("всего статей: ", ""))
    
    if soup.select_one(".labels") is None:
        catalogs = None
        logger.debug(f"No catalogs for journal {journal_link}")
    else:
        catalogs = [l.text for l in soup.select_one(".labels").select(".label")]

    name = soup.find("h1").text

    journal = Journal(
        name=name,
        link=journal_link,
        views=views,
        downloads=downloads,
        hirsh_index=hirsh_index,
        articles_count=articles_count,
        catalogs=catalogs
    )
    return journal

def main():
    # search_result_1 = fetch_articles_list(from_index=0, limit=1000)
    # search_result_2 = fetch_articles_list(from_index=1000, limit=1000)
    # search_result_3 = fetch_articles_list(from_index=2000, limit=1000)

    # search_result = SearchResult(found=len(search_result_1.articles) + len(search_result_2.articles) + len(search_result_3.articles),
                                #  articles=search_result_1.articles + search_result_2.articles + search_result_3.articles)
    # dump_dataclass(search_result, "search_result_final.json")
    search_result = load_articles_list("search_result_final.json")

    unique_journals = set()
    for article in search_result.articles:
        unique_journals.add(article.journal_link)
    
    journals = []
    for journal_link in tqdm(unique_journals):
        journals.append(fetch_journal(journal_link))
        time.sleep(1)
    
    print(len(journals))
    print(journals[0])

    dump_dataclass(Journals(journals), "journals.json")
    # full_articles = []

    # for article in tqdm(search_result.articles):
    #     full_articles.append(fetch_full_article(article))

    # dump_dataclass(DetailedResult(full_articles), "full_articles.json")
    # journal = fetch_journal("/journal/n/sovremennye-problemy-zdravoohraneniya-i-meditsinskoy-statistiki")

    # print(journal)

if __name__ == "__main__":
    main()
