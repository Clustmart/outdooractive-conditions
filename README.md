# outdooractive-conditions
Extract all conditions from Outdooractive for further processing

## Motivation
I would like to be informed by e-mail (optionally create a ticket in Jira) for all conditions published on the outdooactive.com platform in my region. 

### Prerequisite
You nedd an Outdooractive API license, see more in chapter [API Reference](API-Reference)

## Setup
### Installation

You want to work with venv, so in the project folder create your venv folder and activate the python environment (so all dependencies you install )
```shell
python3 -m venv env
source env/bin/activate
```

Install dependencies:

```shell
python3 -m pip install -r requirements.txt
```

### Configuration
Rename config.ini. example to config.ini and fill in the parameters left blank, as described in the file. 
Rename conditions.empty.db to conditions.db

## Usage

## API Reference
http://developers.outdooractive.com/Overview/Getting-Started.html - Getting started with the Outdooractive API
http://developers.outdooractive.com/Overview/Guidelines.html#terms-and-conditions - Outdooractive Terms&Conditions
https://developer.atlassian.com/server/jira/platform/rest-apis/ - Documentation for Atlassian APIs
