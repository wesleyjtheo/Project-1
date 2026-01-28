# Deployment Guide

## Environment Setup

### Local Development

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Install dependencies:**
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   ./start_web.sh
   ```

### Production Deployment

#### Environment Variables

Set these environment variables in your deployment platform:

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | `https://xxxxx.supabase.co` |
| `SUPABASE_KEY` | Supabase anon/public key | `eyJhbGci...` |

#### Deployment Platforms

##### Heroku
```bash
heroku config:set SUPABASE_URL=your_url
heroku config:set SUPABASE_KEY=your_key
```

##### Railway
Add environment variables in the Railway dashboard or via CLI:
```bash
railway variables set SUPABASE_URL=your_url
railway variables set SUPABASE_KEY=your_key
```

##### Render
Add environment variables in the Render dashboard under "Environment".

##### Docker
Create a `.env` file (not committed) or pass as environment variables:
```bash
docker run -e SUPABASE_URL=your_url -e SUPABASE_KEY=your_key your-image
```

##### AWS/GCP/Azure
Use their respective secret management services:
- AWS: Systems Manager Parameter Store or Secrets Manager
- GCP: Secret Manager
- Azure: Key Vault

## Security Best Practices

1. **Never commit `.env` to version control** ✓ (already in `.gitignore`)
2. **Use `.env.example` as template** for team members
3. **Rotate keys regularly** on Supabase dashboard
4. **Use different keys for dev/staging/prod** environments
5. **Enable Row Level Security (RLS)** on Supabase tables in production

## Verifying Setup

Test that environment variables are loaded:
```bash
python -c "from supabase_client import get_supabase_client; print('✅ Connected!')"
```

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY must be set in .env file"

- Check that `.env` file exists in the project root
- Verify the variable names are exact (case-sensitive)
- Ensure no extra spaces around the `=` sign

### Environment variables not loading

- Make sure `python-dotenv` is installed: `pip install python-dotenv`
- Check file encoding (should be UTF-8)
- Restart the application after changing `.env`

## Migration from Hardcoded Credentials

If you have existing code with hardcoded credentials:

1. Create `.env` file with credentials
2. Update code to use `os.getenv()` with `python-dotenv`
3. Remove hardcoded credentials from all files
4. Add `.env` to `.gitignore`
5. Commit changes (credentials now secure)
