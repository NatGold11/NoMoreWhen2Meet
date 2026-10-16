from bs4 import BeautifulSoup
import requests 
import re
import datetime as dt
from dateutil import parser
from pytz import timezone as tz
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from playwright.sync_api import sync_playwright

def getUserInput():
    print("Welcome to NoMoreWhen2Meet")

    url = ""
    username = ""
    password = ""
    while True:
        print("\nPlease enter your When2Meet URL: ")
        url = input()
        if "when2meet.com" in url:
            break
        elif "*" in url:
            url = "https://www.when2meet.com/?39300665-esRbB"
            break
        else:
            print("Invalid URL")
    
    while True:
        print("\nPlease enter your desired When2Meet username: ")
        username = input()
        if len(username) > 0:
            break
        else:
            print("Invalid username")

    while True:
        print("Please enter your desired When2Meet password, or leave blank to skip: ")
        password = input()
        if len(password) == 0:
            password = None
            break
        else:
            break

    return (url, username, password)
    

def main():
    userInput = getUserInput()
    url = userInput[0]
    username = userInput[1]
    password = userInput[2]
    response = requests.get(url)
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    # Scrapes When2Meet for dates/times
    W2MDateTimes = []
    if(response.status_code ==  200):
        soup = BeautifulSoup(response.text, "html.parser")
        grouptime_id = re.compile(r'^GroupTime')
        W2MDateTimes = [(divs['id'][9:], parser.parse(divs['onmouseover'][21:].replace("\");", ""), ignoretz=True)) for divs in soup.find_all("div", id=grouptime_id)]

        for time in W2MDateTimes:
            print(time[1])

    # Sets up credentials/token for GCal access
    creds = None 
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(creds.to_json())


    validDateTimes = []
    try:
        service = build("calendar", "v3", credentials=creds)
        all_calendars = service.calendarList().list(minAccessRole="owner").execute()
        timeMin = W2MDateTimes[0][1].astimezone(tz('UTC')).isoformat()
        timeMax = (W2MDateTimes[len(W2MDateTimes)-1][1] + dt.timedelta(minutes=15)).astimezone(tz('UTC')).isoformat()
        for calendar in all_calendars['items']:
            event_result = service.events().list(calendarId=calendar['id'], timeMin=timeMin, timeMax=timeMax, singleEvents=True).execute()
            print(event_result)
            for event in event_result['items']:
                validDateTimes.append(event['summary'])
        # if not event_result['items']:
        #     validDateTimes.append(time)
    except HttpError as err:
        print("An error occurred: ", err)

    print(validDateTimes)
    
    # with sync_playwright() as p:
    #     browser = p.chromium.launch(headless=True)
    #     page = browser.new_page()
    #     page.goto(url)
    #     page.fill('input#name', username)
    #     if password is not None:
    #         page.fill('input#password', password)
    #     page.click('input[type=button]')

    #     for time in validDateTimes:
    #         youId = "YouTime" + time[0]
    #         page.click(f'div#{youId}')


if __name__ == "__main__":
    main()
