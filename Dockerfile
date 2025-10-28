FROM python:3.14-slim AS python-base
WORKDIR /app
COPY ./api/requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
COPY ./api/ /app

FROM node:24 AS frontend-builder
WORKDIR /app
COPY ./frontend /app
RUN npm install -g @quasar/cli && npm install && quasar build

FROM python-base
COPY --from=frontend-builder /app/dist/spa /app/static
WORKDIR /app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
ENTRYPOINT ["uvicorn"]
CMD ["--host", "0.0.0.0", "main:app"]
