# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# docker-compose.yml
# ---
# version: '3.8'

# services:
#   web:
#     build: .
#     ports:
#       - "8000:8000"
#     volumes:
#       - .:/app
#     environment:
#       - POSTGRES_USER=postgres
#       - POSTGRES_PASSWORD=postgres
#       - POSTGRES_DB=salon_booking
#       - POSTGRES_HOST=db
#       - POSTGRES_PORT=5432
#       - OPENAI_API_KEY=${OPENAI_API_KEY}
#       - DEBUG=True
#     depends_on:
#       - db
#     restart: unless-stopped

#   db:
#     image: postgres:16
#     volumes:
#       - postgres_data:/var/lib/postgresql/data/
#     environment:
#       - POSTGRES_USER=postgres
#       - POSTGRES_PASSWORD=postgres
#       - POSTGRES_DB=salon_booking
#     ports:
#       - "5432:5432"
#     restart: unless-stopped

# volumes:
#   postgres_data: