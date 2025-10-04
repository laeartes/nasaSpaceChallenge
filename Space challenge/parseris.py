import requests
from bs4 import BeautifulSoup
import csv

publications = {}

with open("C:\\Users\\zygim\\Documents\\GitHub\\nasaSpaceChallenge\\SB_publication_PMC.csv", "r", encoding="utf-8") as file:
    reader = csv.reader(file)
    next(reader)
    for row in reader:
        publications.update({row[0]:row[1]})        
headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"}

def scrape_publication(publication_name, publication_url, start="Abstract", end="Introduction"):
    
    url = publication_url  # change this to your target URL
    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-text elements
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Extract visible text
    text = soup.get_text(separator="\n", strip=True)

    the_index_of_abstraction = text.index(start)
    the_index_of_introduction = text.index(end)

    # Write to file
    with open(publication_name+".txt", "w", encoding="utf-8") as f:
        f.write(text[the_index_of_abstraction:the_index_of_introduction])
    print("Scraped text saved to scraped_text.txt")

scrape_publication()