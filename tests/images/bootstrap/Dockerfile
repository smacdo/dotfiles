FROM alpine:latest
RUN apk add --no-cache bash
RUN apk add --no-cache git
RUN apk add --no-cache zsh
RUN apk add --no-cache curl
COPY . /root/.dotfiles
WORKDIR /root/.dotfiles
RUN ./bootstrap.py
WORKDIR /root