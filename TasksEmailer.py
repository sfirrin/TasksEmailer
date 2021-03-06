import httplib2
import os
import datetime
import time
import calendar
import base64
import praw
import random
import yweather
from email.mime.text import MIMEText
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

# Change this constant to your location
LOCATION = 'Chapel Hill, NC'

# Put the tasks you don't want to see in the email to this list
# Or make it an empty list if you want the email to show of all your events
BLACKLIST = ['INLS 512', 'COMP 401', 'INLS 490', 'COMP 283', 'PHIL 698']

try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = ('https://www.googleapis.com/auth/tasks.readonly  '
          'https://mail.google.com/ '
          'https://www.googleapis.com/auth/calendar.readonly')
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'TasksEmailer'


def get_credentials():
    """
    This function taken mostly from the Tasks API quickstart page

    Gets valid user credentials from storage.
    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)

    credential_path = os.path.join(credential_dir, 'tasksemailer.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_address(service):
    profile = service.users().getProfile(userId='me').execute()
    return profile['emailAddress']


def get_calendar_events(service):
    # The gcal API requires the 'Z' to indicate UTC
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    eventsResult = service.events().list(
        calendarId='primary', timeMin=now, maxResults=40,
        singleEvents=True, orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    events_output = []
    if not events:
        print('No events were found')
    date_now = datetime.date.today()
    for event in events:
        if event.get('summary') not in BLACKLIST:
            if event.get('start').get('dateTime'):
                event_datetime = event['start'].get('dateTime')
                event_datetime = datetime.datetime.strptime(
                    event_datetime, '%Y-%m-%dT%H:%M:00-05:00')
                time_str = event_datetime.strftime('%I:%M')

                if time_str[0] == '0':
                    time_str = time_str[1:]
                if event_datetime.hour > 12:
                    time_str += 'p'
                else:
                    time_str += 'a'

                event_str = time_str + ' ' + event.get('summary')

            else:
                event_date = event['start'].get('date')
                event_datetime = datetime.datetime.strptime(event_date,
                                                            '%Y-%m-%d')
                event_str = 'All day - ' + event['summary']
            tdelta_event = (event_datetime.date() - date_now).days
            if tdelta_event <= 7:
                event_list = [event_str, tdelta_event]
                events_output.append(event_list)
    return events_output


def get_current_tasks(service):
    """
    :param service: The google tasks service
    :return: A list containing lists for each task due in the next 7 days
             The task list item's 0 index is the name,
             the 1 index is the number of days until the task is due
             the
    """
    tasks = service.tasks().list(tasklist='@default').execute()

    time_now = datetime.date.today()
    upcoming_tasks = []
    for task in tasks['items']:
        # Create a list for each task
        item = []
        item.append(task['title'])
        if "due" in task.keys():
            due = time.strptime(task['due'], '%Y-%m-%dT%H:%M:%S.000Z')
            due_datetime = datetime.date.fromtimestamp(time.mktime(due))
            tdelta_due = (due_datetime - time_now).days
            item.append(tdelta_due)

            if "completed" in task.keys():
                # If the task has been completed
                # append the number of days since completion
                completed = time.strptime(task['completed'],
                                          '%Y-%m-%dT%H:%M:%S.000Z')
                due = time.strptime(task['due'], '%Y-%m-%dT%H:%M:%S.000Z')
                completed_datetime = datetime.date.fromtimestamp(
                    time.mktime(completed))
                tdelta_completed = (time_now - completed_datetime).days
                item.append(tdelta_completed)
            # If the item is due in 7 or less days and the due date has not
            # passed or the task is overdue and not completed
            if item[1] <= 7 and (item[1] >= 0 or len(item) < 3):
                upcoming_tasks.append(item)
    return upcoming_tasks


def get_aww_image():
    # Returns a list with the url, reddit url, title, and score
    # of a random top 30 reddit.com/r/aww post that is a jpg
    reddit = praw.Reddit(user_agent="TasksEmailer by /u/sj-f")
    top_aww = reddit.get_subreddit("aww").get_top_from_day(limit=10)
    post_options = []
    skip_keywords = ['gifv', 'gallery', 'topic']
    for post in top_aww:
        url = post.url
        if not post.is_self:
            # Skip non-imgur and non-jpg posts
            if 'imgur' not in url or any(kw in url for kw in skip_keywords):
                continue
            if 'jpg' not in url:
                url += '.jpg'
            post_info = [url, post.short_link, post.title, post.score]
            post_options.append(post_info)
    return random.choice(post_options)


def get_weather():
    weather_client = yweather.Client()
    woeid = weather_client.fetch_woeid(LOCATION)
    weather = weather_client.fetch_weather(woeid)
    forecasts = weather['forecast']
    forecasts = sorted(forecasts, key=lambda k: k['date'])
    forecasts[0]['day'] = 'Today'
    forecasts[1]['day'] = 'Tomorrow'
    weather_html = ('<a href="https://weather.yahoo.com/">'
                    '\n<h3>Weather</h3></a>')
    for fc in forecasts:
        day_forecast = []
        weather_html += ('\n<li>' + fc['day'] + ': ')
        weather_html += fc['text'] + ' ('
        weather_html += fc['low'] + '-'
        weather_html += fc['high'] + ')</li>'
    weather_html += '\n</ul>'
    return weather_html


def create_body(task_list):
    """
    :param task_list: The list of upcoming tasks generated by get_current_task
    :return: A string message displaying the upcoming tasks in a nice way
    """
    today = datetime.date.today()
    aww = get_aww_image()
    # This sets up the html and embeds the /r/aww image at the top
    # of the email body message
    message = ('<!doctype html>\n<head></head><body>\n<img style="max-width'
               ':100%" src="' + aww[0] + '"</img>\n')
    reddit_aww_info = ('<p><a href="' + aww[1] + '">' + aww[2] + ' - ' +
                       str(aww[3]) + '</a>\n')

    # This dict used to convert the 'days away' into string days of the week
    days_of_week = {0: 'Today', 1: 'Tomorrow', 7: 'A week from today'}
    for day in range(2, 7):
        weekday_number = (today + datetime.timedelta(days=day)).weekday()
        days_of_week[day] = calendar.day_name[weekday_number]

    current_day = None
    for task in task_list:
        # Compares the current task's due date to the current_day variable and
        # adds a new <h3> tag for the day if necessary
        # This looks like a bit of a mess because of the html tags
        if task[1] < 0 and current_day is None:
            message += '<h3>Overdue</h3>\n<ul>\n'
            current_day = task[1]
        elif task[1] == 0 and current_day != 0:
            if current_day:
                message += '\n</ul>\n'
            message += '<h3>Today</h3> \n <ul>\n'
            current_day = 0
        elif current_day is None or task[1] > current_day:
            if current_day is not None:
                message += '\n</ul>'
            current_day = task[1]
            message += '<h3>' + days_of_week[current_day] + '</h3>\n<ul>\n'
        message += '<li>'
        # Bolds the event / task if 'exam' is in the description
        if 'exam' in task[0].lower():
            message += '<strong>' + task[0] + '</strong>'
        else:
            message += task[0]
        if len(task) > 2:
            message += ' (Completed)'
        message += '</li>\n'
    message += '\n</ul>\n'
    # Adding the weather list and reddit post info to the end of the body
    message += get_weather() + '\n'
    message += reddit_aww_info + '</body>'
    return message


def create_email(body, address):
    """
    :param body: The body text of the email
    :param address: The eamil address to send to
    :return: Nothing -- sends an email to the specified address
    """
    today = datetime.date.today()
    subject = 'Tasks for ' + calendar.day_name[today.weekday()] + ', ' \
              + calendar.month_name[today.month] + ' ' + str(today.day)
    message = MIMEText(body, 'html')

    message['to'] = address
    message['from'] = 'TasksEmailer'
    message['subject'] = subject
    utf_encoded_message = message.as_string().encode('utf8')
    b64_message = base64.urlsafe_b64encode(utf_encoded_message)
    b64_decoded = b64_message.decode('utf-8')
    return {'raw': b64_decoded}


def send_message(service, user_id, message):
    """Send an email message.
    Slightly modified version of the example used on the Gmail API website
     here: https://developers.google.com/gmail/api/guides/sending
    Args:
      service: Authorized Gmail API service instance.
      can be used to indicate the authenticated user.
      message: Message to be sent.
      user_id: the user's google account. Can substitute 'me' if sending
       to self
    Returns:
      Sent Message.
    """

    message = (service.users().messages().send(
        userId=user_id, body=message).execute())
    print('Message successfully sent!')
    print('Message Id: %s' % message['id'])
    return message


def main():
    """Creates an email based on a user's upcoming tasks / events and
       Sends the email to the user from their own gmail address
    """
    # Connecting to the Google apis for Tasks, Calendar, and Gmail
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    tasks_service = discovery.build('tasks', 'v1', http=http)
    gcal_service = discovery.build('calendar', 'v3', http=http)
    gmail_service = discovery.build('gmail', 'v1', http=http)
    # Storing upcoming tasks and events in a list and sorting it by days away
    upcoming_events = get_calendar_events(gcal_service)
    upcoming_tasks = get_current_tasks(tasks_service)
    tasks_events = sorted(upcoming_tasks + upcoming_events,
                          key=lambda k: (k[1], k[0]))
    # Creating the email and sending it off
    email_body = create_body(tasks_events)
    address = get_address(gmail_service)
    email = create_email(email_body, address)
    send_message(gmail_service, 'me', email)

if __name__ == '__main__':
    main()
