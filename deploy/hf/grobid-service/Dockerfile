FROM lfoppiano/grobid:0.9.0

WORKDIR /opt/grobid

COPY grobid.yaml /opt/grobid/grobid.yaml
COPY proxy.py /opt/grobid/proxy.py
COPY start.sh /opt/grobid/start.sh

RUN chmod +x /opt/grobid/start.sh \
    && pip install --no-cache-dir fastapi uvicorn requests

EXPOSE 7860

CMD ["/opt/grobid/start.sh"]

