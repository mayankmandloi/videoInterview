# AI Video Interview POC

Single App Service POC for scheduling and running AI-led technical video interviews.

## Stack

- Python FastAPI
- Azure OpenAI
- LiveKit Cloud
- LiveKit Agents and LiveKit Inference for the AI interviewer participant
- SQLite for POC persistence
- Jinja templates and browser JavaScript

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://localhost:8000/admin`.

Default POC login:

- Username: `admin`
- Password: `admin123`

Change these values in environment variables before deploying.

## Required Environment Variables

```bash
APP_BASE_URL=https://your-app.azurewebsites.net
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-me
SESSION_SECRET=replace-with-long-random-value

AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT=your-chat-deployment

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-livekit-key
LIVEKIT_API_SECRET=your-livekit-secret
LIVEKIT_AGENT_NAME=technical-interviewer
LIVEKIT_INFERENCE_STT_MODEL=deepgram/flux-general-en
LIVEKIT_INFERENCE_STT_LANGUAGE=en
LIVEKIT_INFERENCE_LLM_MODEL=openai/gpt-oss-120b
LIVEKIT_INFERENCE_TTS_MODEL=cartesia/sonic-3
LIVEKIT_INFERENCE_TTS_VOICE=9626c31c-bec5-4cca-baa8-f8ba9e84c8bc
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

For Azure AI Foundry/OpenAI-compatible endpoints, `AZURE_OPENAI_ENDPOINT` can also be the full `/openai/v1` base URL, for example `https://ai-poc-bot.services.ai.azure.com/openai/v1`.

`AZURE_OPENAI_DEPLOYMENT` is used only for report generation. The realtime AI interviewer uses LiveKit Inference through `LIVEKIT_INFERENCE_*` settings, so no Azure realtime deployment is required.

## LiveKit Agent

The AI interviewer is a real LiveKit participant. The candidate token includes a room configuration that dispatches the agent named `technical-interviewer` when the candidate creates the room. The agent uses LiveKit Inference for speech-to-text, LLM responses, and text-to-speech.

Run the web app and agent locally in separate terminals:

```bash
uvicorn app.main:app --reload
python -m app.agent dev
```

For Azure App Service, `startup.sh` starts both:

```bash
python -m app.agent start &
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:${PORT:-8000}
```

## Azure App Service Deployment

1. Create an Azure App Service using a Python runtime.
2. Add all required environment variables in App Service Configuration.
3. Set startup command:

```bash
bash startup.sh
```

4. Deploy this repository through GitHub Actions, Azure CLI, or App Service Deployment Center.

## POC Limitations

- SQLite is only suitable for local/demo use on App Service.
- No production auth, email sending, durable recording, or role-based permissions.
- The AI interviewer joins as a real LiveKit audio participant using LiveKit Inference, but this POC does not yet persist the agent's realtime transcript automatically.
- Candidate notes are saved for the admin report; full transcript persistence should be added next through LiveKit transcription/session events.
