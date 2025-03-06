# NGINX Setup with Docker Compose Profiles

This document explains how to use the NGINX configuration with Docker Compose profiles for both development and production environments.

## Overview

The project now uses Docker Compose profiles to conditionally include the NGINX service:

- **Development Mode**: NGINX is not included, and the API is directly accessible on port 8000
- **Production Mode**: NGINX is included as a reverse proxy with SSL support

## Development Mode

For local development, simply run:

```bash
docker-compose up -d
```

This will start all services except NGINX. The API will be accessible at:
- http://localhost:8000/api/

## Production Mode

For production deployment, use the `production` profile:

```bash
docker-compose --profile production up -d
```

This will include the NGINX service, which provides:
- SSL termination with Cloudflare certificates
- Security headers
- Rate limiting
- Access control

## SSL Certificates

Before deploying to production, you need to set up Cloudflare Origin Certificates:

1. Log in to your Cloudflare dashboard
2. Go to SSL/TLS > Origin Server
3. Click "Create Certificate"
4. Select:
   - RSA (2048) as the private key type
   - Hostnames: `api.dao.cafe` and `dao.cafe`
   - Validity: 15 years (maximum)
5. Click "Create"
6. Save the generated files:
   - Origin Certificate as `nginx/ssl/certificate.pem`
   - Private Key as `nginx/ssl/private.key`

## Security Features

The NGINX configuration includes several security features:

1. **Rate Limiting**:
   - Non-authenticated requests: 30 requests/minute
   - Authenticated requests: 120 requests/minute

2. **Security Headers**:
   - HTTP Strict Transport Security (HSTS)
   - X-Content-Type-Options
   - X-Frame-Options
   - Content Security Policy
   - Referrer Policy

3. **Access Control**:
   - Only accepts requests from dao.cafe domain
   - Only allows connections from Cloudflare IP addresses

## Cloudflare Setup

To complete the setup with Cloudflare:

1. Add DNS records for your domains:
   - A record for `api.dao.cafe` pointing to your server IP
   - A record for `dao.cafe` pointing to your frontend server

2. Set SSL/TLS mode to "Full (strict)" in Cloudflare dashboard

3. Enable all security features in Cloudflare:
   - Web Application Firewall
   - Bot Fight Mode
   - Browser Integrity Check

## Testing Your Setup

To verify your production setup is working correctly:

1. Check NGINX logs:
   ```bash
   docker-compose logs nginx
   ```

2. Test SSL configuration:
   ```bash
   curl -I https://api.dao.cafe
   ```

3. Verify security headers:
   ```bash
   curl -I https://api.dao.cafe | grep -E 'Strict-Transport-Security|X-Content-Type-Options|X-Frame-Options'
