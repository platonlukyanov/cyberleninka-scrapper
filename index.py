import json
import requests
from dataclasses import dataclass, asdict

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
    authors: list[str]
    year: int
    journal: str
    journal_link: str
    ocr: list[str]
    catalogs: list[Catalog] | None

@dataclass
class SearchResult:
    found: int
    articles: list[Article]

def main():
    url = "https://cyberleninka.ru/api/search"
    headers = {
        "accept": "*/*",
        "accept-language": "en-GB-oxendict,en;q=0.9",
        "content-type": "application/json",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Linux\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
    }
    data = {
        "mode": "articles",
        "q": "психические заболевания",
        "size": 3500,
        "from": 0,
        "year_from": 2024,
        "year_to": 2024
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response_json = response.json()
    search_result = SearchResult(found=response_json["found"], articles=[Article(**article) for article in response_json["articles"]])
    json_search_result = json.dumps(asdict(search_result), indent=4, ensure_ascii=False)

    with open("search_result_3.json", "w", encoding="utf-8") as f:
        f.write(json_search_result)   
    
    print(len(search_result.articles))

if __name__ == "__main__":
    main()
