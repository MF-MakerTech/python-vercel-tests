# python-vercel-tests

A minimal FastAPI app deployed on Vercel. Send questions to OpenAI models
through the [Vercel AI Gateway](https://vercel.com/docs/ai-gateway).

## Endpoints

| Method | Path   | Description                              |
| ------ | ------ | ---------------------------------------- |
| GET    | `/`    | Health check                             |
| POST   | `/ask` | Ask a question via AI Gateway            |
| GET    | `/cron` | Scheduled job (Vercel Cron, daily 9 UTC) |

### Example request

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Vercel?"}'
```

Response:

```json
{
  "answer": "...",
  "model": "openai/gpt-4o-mini"
}
```

Optional fields on `/ask`:

- `model` — override the default model (e.g. `openai/gpt-4o`)

## Setup

1. Create an [AI Gateway API key](https://vercel.com/docs/ai-gateway/authentication-and-byok/api-keys) in the Vercel dashboard.

2. Copy the example env file and add your key:

   ```bash
   cp .env.example .env.local
   ```

3. Install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

4. Run locally:

   ```bash
   python3 main.py
   ```

   Open http://localhost:8000/docs for the interactive API explorer.

## Cron job

The project includes a [Vercel Cron Job](https://vercel.com/docs/cron-jobs) that
hits `GET /cron` every day at 9:00 UTC. The schedule is defined in
`vercel.json`:

```json
{
  "crons": [
    {
      "path": "/cron",
      "schedule": "0 9 * * *"
    }
  ]
}
```

Each run asks the AI Gateway a question (default from `CRON_QUESTION`) and
returns the answer. Set `CRON_SECRET` in Vercel — Vercel sends it as a
`Bearer` token so only scheduled invocations succeed.

Test locally:

```bash
curl http://localhost:8000/cron \
  -H "Authorization: Bearer your_random_cron_secret"
```

Cron jobs only run on **production** deployments, not preview deploys.

## Deploy to Vercel

1. Install the [Vercel CLI](https://vercel.com/docs/cli) and log in:

   ```bash
   npm i -g vercel
   vercel login
   ```

2. Deploy:

   ```bash
   vercel
   ```

   Vercel auto-detects the FastAPI app from `main.py` (the `app` instance).

3. Add environment variables in the Vercel project settings (or via CLI):

   ```bash
   vercel env add AI_GATEWAY_API_KEY
   vercel env add AI_MODEL
   vercel env add CRON_SECRET
   vercel env add CRON_QUESTION
   ```

   On Vercel deployments, OIDC auth (`VERCEL_OIDC_TOKEN`) is also available
   automatically if you skip the API key — see the
   [AI Gateway auth docs](https://vercel.com/docs/ai-gateway/authentication-and-byok/authentication).

4. Test the deployed API:

   ```bash
   curl -X POST https://your-project.vercel.app/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "Hello from Vercel!"}'
   ```

## How it works

The app uses the OpenAI Python SDK pointed at the AI Gateway:

```python
client = OpenAI(
    api_key=os.getenv("AI_GATEWAY_API_KEY"),
    base_url="https://ai-gateway.vercel.sh/v1",
)
```

Locally you need `AI_GATEWAY_API_KEY`. On Vercel, the same key works, or OIDC
can authenticate requests without storing a secret.
