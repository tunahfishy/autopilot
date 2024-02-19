# Autopilot

Autopilot is an agent that can interact with the browser and complete tasks for you. 

## Setup

Create an .env file with your `OPENAI_API_KEY`

### Docker

Build docker image:

`docker build -t autopilot .`

Run the script: 

`python main.py`

### Own venv

Create and activate your virtual environment:

`python3.10 -m venv env`

`source env/bin/activate`

Install the PIP dependencies:

`python3.10 -m pip install -r requirements.txt`

Install playwright:

`playwright install`

Run the script: 

`python main.py`


## Examples

Try asking the bot to "buy an apple for you"

## Next steps

Autopilot is very experimental and not fully built out. We're excited for new ways to map parts of an images to html. Feel free to suggest new ways to do this more accurately, or to more accurately decide on next steps when previous steps did not work. 