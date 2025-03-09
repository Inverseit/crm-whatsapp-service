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
   ```ini
   OPENAI_API_KEY=
   WHATSAPP_API_URL=https://graph.facebook.com/v22.0
   WHATSAPP_PHONE_NUMBER_ID= 
   WHATSAPP_VERIFY_TOKEN= *Set up in the the dashboard*
   WHATSAPP_API_KEY=
   INITIALIZE_DB=false *Should I create (or recreate - db (drop tables) when restarting)*
   WHATSAPP_GREETING_TEMPLATE=hello_world *Set up in the the dashboard*
   WHATSAPP_TEMPLATE_LANGUAGE_CODE=en_US *Set up in the the dashboard*
   BACKEND_URL=https://dev.crm-beauty-salon... *backend url*
   AUTH_EMAIL=xxx@gmail.com *backend email*
   AUTH_PASSWORD=xxxx *backend password*
```