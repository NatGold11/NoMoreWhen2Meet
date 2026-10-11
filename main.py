from bs4 import BeautifulSoup
import requests 
import re

def main():
    url = "https://www.when2meet.com/?39099702-4okF1"
    response = requests.get(url)
    print(response)

    if(response.status_code ==  200):
        soup = BeautifulSoup(response.text, "html.parser")
        grouptime_id = re.compile(r'^GroupTime')
        times = [{divs['id']: divs['onmouseover'][21:].replace("\");", "")} for divs in soup.find_all("div", id=grouptime_id)]

        for time in times:
            print(time)


if __name__ == "__main__":
    main()
