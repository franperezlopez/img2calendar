Lanngchain agent based on  AutoGPT. The agent takes as input an image (poster event or similar), and then generates the iCalendar (*.ics) file in order to add the event to your calendar. The agent makes use of different tools in order to extract information about the event 

Install python dependencies using conda/miniconda `conda install -f environment.yml``

Then you need to install node dependencies and pull the docker image for playwright
```sh
cd src/playw
npm install
npm update playwright
npx playwright install
docker pull mcr.microsoft.com/playwright
```

The streamlit application is ideal for testing and debugging purposes, as let you watch the *reasoning process*.

```sh
streamlit run app.py
```

The telegram bot is ideal for showing the agent with a light client. It works attaching an image to the message, and then returns the event as ics file.

```sh
python -m bot
```