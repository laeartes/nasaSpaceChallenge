import requests
from bs4 import BeautifulSoup
import csv
import json 

publications = {}
with open("SB_publication_PMC.csv", "r", encoding="utf-8") as file:
    reader = csv.reader(file)
    next(reader)
    for row in reader:
        publications.update({row[0]:row[1]})

headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"}

def parsing(pub_name, url):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    json_dictionary = {"name":pub_name, "link":url}
    sections = soup.find_all("section")
    all_section_names = []
    for sec in sections:
        if 'class' in sec.attrs and "main-article-body" in sec['class']:
            subsections = sec.find_all("section")
            inner_text = {}
            for subsec in subsections:
                if (subsec.h2 is not None):
                    Section_name = subsec.h2.string # creating sections
                    all_section_names.append(Section_name) 
                    temp_text = "" #section inner-text
                    subsec.h2.decompose() # removing the section name from the text
                    # print(Section_name)
                    if subsec.h3 is not None:
                        subsection_name = subsec.h3.string # printing subsections, if they exist 
                        temp_text +=  subsection_name + "\n"
    
                    for paragraph in subsec.find_all("p"):
                        par = paragraph.get_text(separator="", strip=True)
                        temp_text += par + "\n"
                        # print(paragraph.get_text(separator="", strip=True))
                    if (Section_name == "References"):
                        ref = subsec.get_text(separator="", strip=True)
                        temp_text += ref
                inner_text.update({Section_name: temp_text})
    json_dictionary.update({"sectionNames": all_section_names})
    json_dictionary.update({"sections": inner_text})
    print("done:", pub_name)
    return json_dictionary

LIST =[]
for NAME in publications:
    LINK = publications[NAME]
    LIST.append(parsing(NAME, LINK))

with open("straipsnis.json", "w", encoding="utf-8") as f:
        json.dump(LIST, f, ensure_ascii=False, indent=4)