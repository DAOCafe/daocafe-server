# Environment-Based Configuration

This project now uses environment-based configuration to separate development and production settings. This document explains how to use this setup.

## Environment Files

The project includes two environment files:

- `.env.development`: Contains settings for local development
- `.env.production`: Contains settings for production deployment

## How to Use

### Development

By default, the application will load settings from `.env.development`. This provides development-friendly settings like:

- DEBUG mode enabled
- Long JWT token lifetimes for easier testing
- Local development hosts and CORS origins

### Production

To run the application with production settings:

1. Set the `DJANGO_ENV_FILE` environment variable to `.env.production`:

   ```bash
   export DJANGO_ENV_FILE=.env.production
   ```

2. Or specify it when running the application:

   ```bash
   DJANGO_ENV_FILE=.env.production python manage.py runserver
   ```

The production environment includes:

- DEBUG mode disabled
- Secure JWT token lifetimes (15 minutes for access tokens, 7 days for refresh tokens)
- Token rotation and blacklisting enabled
- Production domain names for ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS

## Docker Deployment

For Docker deployment, you can set the environment variable in your docker-compose.yml file:

```yaml
services:
  api:
    # ...
    environment:
      - DJANGO_ENV_FILE=.env.production
    # ...
```

## Important Security Notes

1. **JWT Settings**: In production, JWT tokens have shorter lifetimes and token rotation is enabled
2. **Nonce Handling**: In production, nonces are deleted after verification to prevent replay attacks
3. **Debug Mode**: In production, DEBUG is set to False
4. **Allowed Hosts**: In production, only specific domain names are allowed
5. **CORS Origins**: In production, only specific origins are allowed

## Customizing Environment Files

You can customize the environment files to match your specific needs. Make sure to update:

- `ALLOWED_HOSTS` with your actual production domain names
- `CORS_ALLOWED_ORIGINS` with your actual frontend domain names
- Database credentials
- Secret keys and API keys

## Adding New Environment Variables

When adding new environment variables:

1. Add them to both `.env.development` and `.env.production` files
2. Update the settings.py file to use the environment variable with a default value:

   ```python
   MY_SETTING = os.environ.get('MY_SETTING', 'default_value')
   ```

3. For environment-specific settings, use the DEBUG flag:

   ```python
   if DEBUG:
       # Development setting
       MY_SETTING = 'development_value'
   else:
       # Production setting
       MY_SETTING = os.environ.get('MY_SETTING', 'production_default')
