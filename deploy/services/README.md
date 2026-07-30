# Standalone Services

These services run as standalone Docker containers (not HF Spaces).

## GROBID

- Port: 8070
- Build: `docker build -t scholarform-grobid deploy/services/grobid`
- Run: `docker run -p 8070:8070 scholarform-grobid`

## DOCX Converter

- Port: 8080
- Build: `docker build -t scholarform-docx-converter deploy/services/docx-converter`
- Run: `docker run -p 8080:8080 scholarform-docx-converter`
