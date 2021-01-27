FROM ubuntu:18.04
RUN apt-get update && apt-get install -y apt-mirror
ADD mirror.list /etc/apt/mirror.list
ADD sources.list /sources.list
ADD syncmirror.sh /syncmirror.sh
CMD /syncmirror.sh

