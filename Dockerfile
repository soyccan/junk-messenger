FROM ubuntu:20.04

RUN sed -ir "s/archive.ubuntu.com/tw.archive.ubuntu.com/g" /etc/apt/sources.list && \
    sed -ir "s/security.ubuntu.com/tw.archive.ubuntu.com/g" /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -yq cmake g++

WORKDIR /root
COPY . /root
RUN ./build.sh

CMD ["./build/junk-messenger"]
