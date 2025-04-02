# Beauty Salon Booking Service

A FastAPI-based backend service for beauty salon bookings powered by OpenAI GPT. The service provides webhook endpoints for receiving messages from multiple messaging platforms (WhatsApp, Telegram), processes them through GPT to collect booking information, and stores bookings in a PostgreSQL database.

## Features

- Multi-platform messaging support:
  - WhatsApp integration via the WhatsApp Business API
  - Telegram integration via the Telegram Bot API
  - Extensible design for adding more platforms
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
- Telegram Bot API access

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
   
   # WhatsApp configuration
   WHATSAPP_API_URL=https://graph.facebook.com/v22.0
   WHATSAPP_PHONE_NUMBER_ID= 
   WHATSAPP_VERIFY_TOKEN= *Set up in the Meta dashboard*
   WHATSAPP_API_KEY=
   WHATSAPP_GREETING_TEMPLATE=hello_world *Set up in the Meta dashboard*
   WHATSAPP_TEMPLATE_LANGUAGE_CODE=en_US *Set up in the Meta dashboard*
   
   # Telegram configuration
   TELEGRAM_API_TOKEN= *Bot token from BotFather*
   TELEGRAM_WEBHOOK_TOKEN= *Custom token for webhook verification*
   
   INITIALIZE_DB=false *Should I create (or recreate - db (drop tables) when restarting)*
   BACKEND_URL=https://dev.crm-beauty-salon... *backend url*
   AUTH_EMAIL=xxx@gmail.com *backend email*
   AUTH_PASSWORD=xxxx *backend password*
   ```

3. Build and start the Docker containers:
   ```bash
   docker-compose up -d
   ```

## Messaging Platforms Setup

### WhatsApp Setup

1. Create a WhatsApp Business account in the Meta Business Manager
2. Set up a WhatsApp Business API app in the Meta Developer Portal
3. Configure the webhook URL to point to your deployment at `/api/webhooks/whatsapp`
4. Set the same verification token in both the Meta Dashboard and your `.env` file
5. Create message templates in the Meta Dashboard and use the template name in your configuration

### Telegram Setup

1. Create a new bot using BotFather:
   - Open Telegram and search for `@BotFather`
   - Send the command `/newbot` and follow the instructions
   - Copy the API token provided by BotFather

2. Set the required environment variables:
   - `TELEGRAM_API_TOKEN`: The token provided by BotFather
   - `TELEGRAM_WEBHOOK_TOKEN`: A custom token you create for webhook verification
   - `BACKEND_URL`: Your application's public URL (needed for webhook setup)

3. The application will automatically set up the webhook for Telegram when it starts up

4. To test your Telegram bot:
   - Open Telegram and search for your bot's username
   - Start a conversation with your bot by sending `/start`
   ```