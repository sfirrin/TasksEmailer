GTasks-Emailer
=============
About
-----

My motivation for making this was that I am good about putting things into my Calendar and Tasks, but would get distracted and forget what is coming up. My solution was to make this script that sends me an email with the tasks and events coming up in the next 7 days. 

To make it a little less of a chore to go through my tasks right when I wake up I had the script embed an image from a top post in http://reddit.com/r/aww, usually a cute dog or something. And then to add a little more usefulness I used the yweather Python module to tell me the upcoming days' forecast.

I might try and convert this into a webapp in the future but for now it is a standalone script that requires a little more effort to set up.

Currently I have the script run on a schedule using http://pythonanywhere.com because my computer isn't on 24/7 so I'm going to give instuctions on how to get that set up below. You could also use another service or your own computer to run the script on a schedule but you might have to change a few things about the setup.

Setup
--------
In order to have the email show weather for your location and blacklist the events that you want, you'll need to do some very simple editing of TasksEmailer.py.

1. Download TasksEmailer.py from the GitHub page

2. Open it with your preferred text editor

3. Change the LOCATION constant to your location

4. Change the values in the BLACKLIST constant to the events that you don't want to show up in the email


Whether you're installing on PythonAnywhere or your own machine you'll have to get your Google account set up for this to work.

1. Go to https://console.developers.google.com/start/api?id=gmail and create a new project

2. In the 'Overview' tab from the left sidebar search for and enable the 'Calendar API' and the 'Tasks API'

3. Select the 'Credentials' tab from the left sidebar

4. Select the 'OAuth Consent Screen' tab at the top of the page and enter 'GTasks Emailer' into the box marked 'Product name shown to users' and click 'Save'

3. Select the 'Create Credentials' button in the 'Credentials' tab and choose 'Oauth client ID'

4. You should be sent to an 'Application Type' page. Select 'Other' and name it 'GTasks Emailer'

5. In the table 'OAuth 2.0 Client IDs' you should see a row titled 'GTasks Emailer'. At the far right of the row click the download button to download the client_secret_*.json file.

6. Rename the json file so that it is only client_secret.json

You're done!

PythonAnywhere Setup
--------------------
1. Sign up for a free account at http://pythonanywhere.com

2. Go to the 'Files' tab and upload TasksEmailer.py and client_secret.json

3. Open a bash console and enter the following command to install the dependencies:

```bash
	>>> pip install --user praw google-api-python-client yweather
```

4. Enter this command into the console to authorize the script to use your Google account

```bash
	>>> python TasksEmailer.py --noauth_local_webserver
```

5. Copy the link, paste it into a new browser tab's address box, and click 'Allow'

6. You should be redirected to a new page with a code. Copy this and paste it into the PythonAnywhere console (Ctrl-V)

7. Return to your PythonAnywere home page and click the 'Schedule' tab and set up scheduling for TasksEmailer.py however you want

Enjoy!
	
