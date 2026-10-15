from bs4 import BeautifulSoup
import requests 
import re
import datetime as dt
from dateutil import parser
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def main():
    url = "https://www.when2meet.com/?39099702-4okF1"
    response = requests.get(url)
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    # Scrapes When2Meet for dates/times
    if(response.status_code ==  200):
        soup = BeautifulSoup(response.text, "html.parser")
        grouptime_id = re.compile(r'^GroupTime')
        W2MDateTimes = [{divs['id']: parser.parse(divs['onmouseover'][21:].replace("\");", ""))} for divs in soup.find_all("div", id=grouptime_id)]

        for time in W2MDateTimes:
            print(time)

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
    for timeid, time in W2MDateTimes:
        try:
            service = build("calendar", "v3", credentials=creds)
            event_result = service.events().list(calendarId="primary", timeMin=time, timeMax=time+dt.timedelta(minutes=15), singleEvent=True).execute()
            if not event_result:
                validDateTimes.append(timeid)
        except HttpError as err:
            print("An error occurred: ", err)

    for timeid in validDateTimes:
        print(timeid)

    # Searches GCal for free times

    # try:
    #     service = build("calendar", "v3", credentials=creds)
    #     now = dt.datetime.now().isoformat() + "Z"
    #     event_result = service.events().list(calendarId="primary", timeMin=now, maxResults=10, singleEvents=True, orderBy="startTime").execute()
    #     events = event_result.get("items", [])

    #     if not events:
    #         print("No upcoming events found")
    #         return

    #     for event in events:
    #         start = event['start'].get('dateTime', event['start'].get('date'))
    #         print(start, event["summary"])
        
    # except HttpError as err:
    #     print("An error occurred: ", err)


if __name__ == "__main__":
    main()
