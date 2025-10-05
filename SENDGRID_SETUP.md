# SendGrid Email Integration Setup Guide

## 1. Create SendGrid Account

1. Go to: https://sendgrid.com/
2. Sign up for a free account
3. Complete email verification

## 2. Create API Key

1. Go to SendGrid Dashboard → Settings → API Keys
2. Click "Create API Key"
3. Choose "Restricted Access" 
4. Give it a name like "Cookie Licking Detector"
5. Grant permissions:
   - Mail Send: Full Access
   - Template Engine: Read Access (if using templates)
6. Copy the generated API key (starts with `SG.`)

## 3. Add to Environment

Add to your `.env` file:
```bash
SENDGRID_API_KEY=SG.your_api_key_here
FROM_EMAIL=noreply@yourdomain.com
```

## 4. Verify Sender Email

1. Go to SendGrid Dashboard → Settings → Sender Authentication
2. Choose "Single Sender Verification"
3. Add your from email address and complete verification

## 5. Test Email Integration

```bash
python3 -c "
from app.services.notification_service import NotificationService
service = NotificationService()
print('Email service configured:', bool(service.sendgrid_configured))
"
```

## For Development

You can test without SendGrid - the service will log email attempts without actually sending emails.