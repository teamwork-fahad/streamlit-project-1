# HackMD Notes Dashboard

Streamlit dashboard for testing and managing HackMD notes through the HackMD REST API.

## Features

- List HackMD notes
- Open notes in HackMD
- Search notes by title, description, folders, tags, and content
- Filter by folders and tags
- Sort notes
- Edit title, description, tags, content, and permissions
- Delete notes with confirmation

## Local Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create `.streamlit/secrets.toml`:

```toml
HACKMD_API_TOKEN = "your-hackmd-api-token"
```

3. Run the app:

```bash
streamlit run app.py
```

## Deploy On Streamlit Community Cloud

1. Open Streamlit Community Cloud.
2. Create a new app from this GitHub repository.
3. Set the main file path to `app.py`.
4. Add this secret in the app settings:

```toml
HACKMD_API_TOKEN = "your-hackmd-api-token"
```

Never commit `.streamlit/secrets.toml` to GitHub.
