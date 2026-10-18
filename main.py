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

def progress_bar(progress, total):
    percent = int(100*(progress/float(total)))
    bar = '█' * percent +  '-' * (100-percent)
    print(f"\r|{bar}| {percent:.2f}%", end="\r")

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

def scrapeW2M(url):
    response = requests.get(url)
    W2MDateTimes = []
    if(response.status_code ==  200):
        soup = BeautifulSoup(response.text, "html.parser")
        grouptime_id = re.compile(r'^GroupTime')
        W2MDateTimes = [(divs['id'][9:], parser.parse(divs['onmouseover'][21:].replace("\");", ""), ignoretz=True)) for divs in soup.find_all("div", id=grouptime_id)]

        # for time in W2MDateTimes:
        #     print(time[1])
    print("W2M page scraped ✓")
    return W2MDateTimes

def checkCreds(SCOPES):
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

    return creds

def checkGCal(creds, W2MDateTimes):
    calDateTimes = []
    calTz = ""
    try:
        service = build("calendar", "v3", credentials=creds)
        all_calendars = service.calendarList().list(minAccessRole="owner").execute()
        timeMin = W2MDateTimes[0][1].astimezone(tz('UTC')).isoformat()
        timeMax = (W2MDateTimes[len(W2MDateTimes)-1][1] + dt.timedelta(minutes=15)).astimezone(tz('UTC')).isoformat()
        tzCollected = False
        for calendar in all_calendars['items']:
            event_result = service.events().list(calendarId=calendar['id'], timeMin=timeMin, timeMax=timeMax, singleEvents=True).execute()
            print("Checking calendar: ", calendar['summary'], " ✓")
            for event in event_result['items']:
                # Skips event if all-day
                if 'date' in event['start']:
                    continue
                if not tzCollected: 
                    calTz = event['start']['timeZone']
                    tzCollected = True
                startTime = parser.parse(event['start']['dateTime'])
                endTime = parser.parse(event['end']['dateTime'])
                calDateTimes.append(
                            (startTime - dt.timedelta(minutes=startTime.minute % 15,
                                seconds=startTime.second,
                                microseconds=startTime.microsecond), 
                                endTime - dt.timedelta(minutes=endTime.minute % 15,
                                seconds=endTime.second,
                                microseconds=endTime.microsecond)))
    except HttpError as err:
        print("An error occurred: ", err)

    # print(calDateTimes)
    print("Pulled GCal events ✓")
    return (calDateTimes, calTz)

def findAvailableTimes(W2MDateTimes, calDateTimes, calTz):
    # timetable structure: {dateTime : [id, isValid]}
    timetable = {}
    for time in W2MDateTimes:
        timetable.update({time[1].astimezone(tz(calTz)):[time[0], True]})

    print("Searching for available times: ")
    for idx, event in enumerate(calDateTimes):
        progress_bar(idx, len(calDateTimes))
        currTime = event[0]
        while currTime <= event[1]:
            if currTime in timetable:
                timetable[currTime][1] = False
            currTime = currTime + dt.timedelta(minutes=15)

    print()
    print("Found available times ✓")
    return timetable

def submitValidTimes(username, password, url, validDateTimes):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.fill('input#name', username)
        if password is not None:
            page.fill('input#password', password)
        page.click('input[type=button]')

        for time in validDateTimes:
            if validDateTimes[time][1]:
                youId = "YouTime" + validDateTimes[time][0]
                page.click(f'div#{youId}')

    print("Filled out When2Meet ✓")

# <======================= MAIN ============================> #

def main():
    userInput = getUserInput()
    url = userInput[0]
    username = userInput[1]
    password = userInput[2]
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    # Scrapes When2Meet for dates/times
    W2MDateTimes = scrapeW2M(url)

    # Sets up credentials/token for GCal access
    creds = checkCreds(SCOPES)

    # Calls GCal API and builds list of event times within W2M duration
    calInfo = checkGCal(creds, W2MDateTimes)
    calDateTimes = calInfo[0]
    calTz = calInfo[1]

    # Creates list of available times 
    validDateTimes = findAvailableTimes(W2MDateTimes, calDateTimes, calTz)
    
    # Uses website automation to select valid times
    submitValidTimes(username, password, url, validDateTimes)

    print("\n<==============================================>\n")
    print("SUCCESS")
    print("URL: ", url)
    print("Username: ", username)
    if password is not None:
        print("Password: ", password)
    


if __name__ == "__main__":
    main()
