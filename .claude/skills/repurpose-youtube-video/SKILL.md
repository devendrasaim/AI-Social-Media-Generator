---
name: repurpose-youtube-video
description: Repurpose a YouTube video into an optimized Instagram post. Extracts video content, generates a caption and visual, shows a review, and publishes via Blotato.
argument-hint: <youtube-url>
disable-model-invocation: true
---

# Repurpose YouTube Video to Instagram Post

The user wants to turn a YouTube video into an Instagram post with an AI-generated caption and visual.

## Prerequisites

1. Check that the `.env` file in the project root has both keys set:
   - `BLOTATO_API_KEY` — must be non-empty
   - `GEMINI_API_KEY` — must be non-empty
   - **NEVER ask the user to share their API keys in the chat.** If keys are missing, tell them to edit the `.env` file directly.

2. Ensure Python dependencies are installed. If not, run:
   ```
   pip install -r requirements.txt
   ```

## Run the Tool

Execute the repurpose script with the YouTube URL:

```
python repurpose.py $ARGUMENTS
```

The script will:
1. Ask the user for a tone/style
2. Extract video content from YouTube via Blotato API
3. Generate an Instagram caption + image prompt via Gemini
4. Generate a visual (Blotato templates -> Pollinations.ai -> Picsum fallback)
5. Display the post for review
6. On approval, publish to Instagram via Blotato
7. Log results to `published_posts.csv`

## If Something Goes Wrong

- **Missing API keys**: Tell the user to add them to `.env` (never ask for keys in chat)
- **Instagram not connected**: Tell the user to connect Instagram in their Blotato dashboard at https://app.blotato.com
- **Timeout errors**: Suggest trying again — Blotato processing can be slow during peak times
- **Gemini errors**: Check that the GEMINI_API_KEY is valid and has quota remaining
- **Image issues**: The script tries 3 sources in order: Blotato templates (best quality), Pollinations.ai, then Picsum (placeholder). Blotato-hosted images are most reliable for publishing.

## Post-Run

After the script completes, summarize:
- Whether the Instagram post was published successfully
- The live URL of the post
- Any errors that occurred

The full log is maintained in `published_posts.csv` in the project root.
