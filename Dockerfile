FROM python:3.11-slim

WORKDIR /app

# Install build dependencies if needed
COPY pyproject.toml ./
COPY tiffin ./tiffin

RUN pip install --no-cache-dir .

EXPOSE 8765

CMD ["python", "-m", "tiffin", "serve", "--port", "8765"]
