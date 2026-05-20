# AI Video Interview POC - Application Flow Explanation

This document outlines the end-to-end flow of the AI Video Interview Proof of Concept (POC) application.

## 1. System Overview

The AI Video Interview POC is a full-stack application designed to automate technical interviews. It leverages **FastAPI** for the backend, **LiveKit** for real-time audio/video communication, and **Azure OpenAI** for intelligent interview conduction and report generation.

### Key Technologies
- **Backend**: FastAPI (Python)
- **Database**: SQLite (SQLAlchemy ORM)
- **Real-time Communication**: LiveKit Cloud / LiveKit Agents
- **AI Models**: 
  - **Azure OpenAI (GPT-4o)**: Report generation and LLM logic.
  - **Deepgram**: Speech-to-Text (STT).
  - **Cartesia**: Text-to-Speech (TTS).
- **Frontend**: Jinja2 Templates, Vanilla JavaScript, CSS.

---

## 2. Core Workflows

### A. Administrator Workflow (Recruiter)
1. **Authentication**: Admin logs in via `/admin/login` using credentials defined in environment variables.
2. **Dashboard**: Upon login, the admin is redirected to `/admin`, where they can view a list of all scheduled, in-progress, and completed interviews.
3. **Scheduling**:
   - Admin fills a form with Candidate Name, Email, Role, Skills, and Duration.
   - The system generates a unique, secure URL token for the interview.
   - The interview record is stored in the database with a `scheduled` status.
4. **Reviewing Results**:
   - Once an interview is `completed`, the admin can click on the interview to view a detailed report.
   - The report includes an overall score, a hiring recommendation, a summary, and specific strengths/concerns.
   - **Regeneration**: If the initial report is unsatisfactory, the admin can trigger a regeneration using the "Regenerate Report" button.

### B. Candidate Workflow (Interviewee)
1. **Joining the Interview**:
   - The candidate opens the unique URL provided by the recruiter (e.g., `/interview/{token}`).
   - The page initializes the LiveKit client and checks the interview status.
2. **Initialization & Dispatch**:
   - When the candidate clicks "Start Interview":
     - The backend updates the interview status to `in_progress`.
     - A LiveKit access token is generated for the candidate.
     - The backend calls the LiveKit API to **dispatch** the AI agent (`technical-interviewer`) into the specific room.
3. **The Live Interview**:
   - The candidate joins the room and meets the AI Interviewer.
   - The AI agent introduces itself and begins the technical assessment based on the role and skills specified by the admin.
   - **Transcript Capture**: The frontend captures snippets of the conversation and sends them to the backend via `/api/interviews/{token}/answer` to ensure a persistent record for report generation.
   - **Monitoring**: The system monitors for cheating (e.g., tab switching) and logs flags via `/api/interviews/{token}/flag`.
4. **Completion**:
   - At the end of the duration or when the agent concludes, the session ends.
   - The candidate clicks "Finish", which triggers the `/api/interviews/{token}/finish` endpoint.
   - The backend sets the status to `completed` and immediately calls Azure OpenAI to process the gathered transcript and generate the final report.

---

## 3. Technical Flow & Integration Points

### LiveKit Agent Integration
The AI Interviewer is implemented as a **LiveKit Agent** (`app/agent.py`). 
- It uses the `VoicePipelineAgent` to handle the real-time interaction loop.
- **Inference**: It integrates with Deepgram for STT, Azure OpenAI for the "brain" (LLM), and Cartesia for the "voice" (TTS).
- **Context**: When dispatched, the agent receives the candidate's metadata (role, skills) as part of its initial prompt, allowing it to tailor the interview.

### Database Schema
- **Interviews**: Stores candidate info, status, and configuration.
- **TranscriptTurns**: Stores the dialogue/notes from the interview session.
- **Reports**: Stores the AI-generated evaluation.
- **CheatingFlags**: Logs any suspicious activity detected during the session.

### Report Generation
The `app/services/azure_openai.py` service handles the final analysis. It takes the `TranscriptTurns` associated with an interview, feeds them into GPT-4o with a specialized prompt, and parses the structured JSON response into the `Report` model.
