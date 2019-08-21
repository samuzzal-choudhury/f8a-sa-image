FROM registry.centos.org/centos/centos:7

RUN yum install -y epel-release &&\
    yum install -y gcc git python36-pip python36-requests httpd httpd-devel python36-devel &&\
    yum install -y nodejs &&\
    yum clean all &&\
    pip3 install --upgrade pip

RUN useradd -d /coreapi coreapi

COPY main.py /coreapi/main.py
RUN chmod +x /coreapi/main.py

COPY package.json /coreapi/package.json
COPY requirements.txt /coreapi/requirements.txt
RUN pip3 install -r /coreapi/requirements.txt

CMD ["/coreapi/main.py"]
