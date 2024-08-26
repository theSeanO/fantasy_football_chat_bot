FROM python:3.9.9-slim-bullseye
# For Raspberry Pi hosting, use this Python image instead:
# FROM python:3.9.9-slim-buster

# Install app
ADD . /usr/src/gamedaybot
WORKDIR /usr/src/gamedaybot
RUN python3 setup.py install

# Launch app
CMD ["python3", "gamedaybot/espn/espn_bot.py"]