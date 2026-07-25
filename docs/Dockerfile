FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install mkdocs-material mkdocs-git-revision-date-localized-plugin mkdocs-minify-plugin
COPY . .
RUN mkdocs build

FROM nginx:1.27-alpine
COPY --from=builder /app/site /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
