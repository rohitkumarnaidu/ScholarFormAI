FROM lfoppiano/grobid:0.8.2

WORKDIR /opt/grobid

COPY grobid.yaml /opt/grobid/grobid.yaml
COPY proxy.py /opt/grobid/proxy.py
COPY start.sh /opt/grobid/start.sh

COPY requirements.txt /opt/grobid/requirements.txt

RUN chmod +x /opt/grobid/start.sh \
    && pip install --no-cache-dir -r /opt/grobid/requirements.txt

EXPOSE 8070

CMD ["/opt/grobid/start.sh"]

