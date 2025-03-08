# Beauty Salon Booking Service

A FastAPI-based backend service for beauty salon bookings powered by OpenAI GPT. The service provides webhook endpoints for receiving messages from WhatsApp, processes them through GPT to collect booking information, and stores bookings in a PostgreSQL database.

## Features

- WhatsApp integration via the WhatsApp Business API
- Stateless GPT conversation processing with database persistence
- Stateful conversations with complete history stored in PostgreSQL
- Booking management with confirmation workflow
- RESTful API for managing bookings and conversations
- Docker Compose setup for easy deployment
- Concurrent handling of multiple users

## Requirements

- Python 3.10+
- PostgreSQL
- OpenAI API key
- WhatsApp Business API access

## Installation

### Using Docker (recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/salon-booking-service.git
   cd salon-booking-service
   ```

2. Create a `.env` file with your configuration:
   ```