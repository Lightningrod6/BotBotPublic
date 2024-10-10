import bs4
import requests

url = "https://rustlabs.com/group=itemlist"

items = requests.get(url)

soup = bs4.BeautifulSoup(items.text, "html.parser")

with open("itemlist.txt", "a") as f:
    for item in soup.find_all("span", class_="r-cell"):
        f.write(item.text + "\n")