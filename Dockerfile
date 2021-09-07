FROM python:3.9.0-buster

RUN apt-get update
RUN /usr/local/bin/python -m pip install --upgrade pip

ENV APP_USER twilio
ENV FLASK_APP gordon
ENV APP_DIR /home/twilio/app/gordon
ENV APP_INSTALL_DIR /app/gordon
ENV GORDON_RUN_MODE api

RUN mkdir -p /home/twilio
RUN groupadd -r twilio &&\
    useradd -r -g twilio -d /home/twilio -s /sbin/nologin -c "Twilio Docker image user" twilio

RUN chown twilio /home/twilio
RUN chgrp twilio /home/twilio

RUN mkdir -p $APP_INSTALL_DIR
COPY gordon $APP_INSTALL_DIR/gordon
COPY bin $APP_INSTALL_DIR/bin
COPY requirements.txt $APP_INSTALL_DIR
RUN pip3 install -r $APP_INSTALL_DIR/requirements.txt

USER $APP_USER
RUN mkdir -p $APP_DIR

ADD --chown=twilio:twilio gordon $APP_DIR/gordon
ADD --chown=twilio:twilio bin $APP_DIR/bin
WORKDIR $APP_DIR

EXPOSE 9001

CMD (/bin/bash ./bin/run.sh)
