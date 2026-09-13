# AI Social Media Generator

A small Python program that turns an idea into a finished Instagram carousel post and puts it on Instagram for you.

You give it a topic (or a YouTube link). It reads up on the topic, writes the words, draws the pictures, puts them together into three square slides, shows them to you, and — if you say yes — posts them.

---

## What it actually does, step by step

Think of it like a tiny factory with five machines in a row:

1. **Find the facts.** It either reads the transcript of a YouTube video you gave it, or it asks Perplexity (a search-powered AI) what's new about a topic.
2. **Write the post.** It sends those facts to Google Gemini and asks for a caption, three slides of text, and five hashtags.
3. **Make the pictures.** For each slide it asks an AI to draw a picture, then uses that picture to build a 1080×1080 image: black background, a headline in a purple-to-blue gradient at the top, the picture in the middle, and the text at the bottom.
4. **Show you.** The finished slides get copied into a folder called `carousel_review/` so you can open them and look. It asks "Publish post? (yes/no)".
5. **Post and write it down.** If you say yes, it logs into Instagram and uploads the carousel, then adds a row to `published_posts.csv` with the date, the topic, and the link to the post.

There is also a second mode where it does all of this **on its own**, on a schedule, without asking you anything. More on that below.

---

## What you need before you start

- **Python 3.10 or newer** (this project was built on 3.12).
- **An Instagram account** you're happy to have the program post from.
- **A Google Gemini API key** — free to get at https://aistudio.google.com/apikey. This is the "brain" that writes the words and draws the pictures.
- **A Perplexity API key** — from https://www.perplexity.ai/settings/api. Only needed if you want to give it a *topic* instead of a YouTube link.

If you skip the Gemini key, the program still runs, but it falls back to a plain template caption and plain pictures. It's much better with the key.

---

## Setting it up (one time)

### 1. Install the Python packages

```bash
cd AI-Social-Media-Generator
pip install -r requirements.txt
```

### 2. Create your secrets file

Copy `.env.example` to a new file named `.env`, then open it and fill in your own values:

```bash
copy .env.example .env
```

(On Mac/Linux use `cp` instead of `copy`.)

The `.env` file is where your passwords and API keys live. It is listed in `.gitignore`, so it will never be uploaded if you put this project on GitHub. **Never share this file with anyone and never paste its contents into a chat.**

### 3. Log into Instagram once

Instagram doesn't like robots logging in out of nowhere, so you do the login yourself once and the program saves the result:

```bash
python setup_instagram.py
```

It will ask for a code from your email or phone, or ask you to tap "This was me" in the Instagram app. Follow whatever it says on screen. When it finishes, it creates a file called `instagram_session.json`. From then on the program reuses that instead of logging in fresh every time.

If posting ever stops working with a message about the session expiring, just run this command again.

---

## Using it by hand

**From a topic:**

```bash
python main.py --perplexity "Latest AI tools for students"
```

**From a YouTube video:**

```bash
python main.py "https://www.youtube.com/watch?v=xxxxxxxxxxx"
```

It will build the post, drop the slides in `carousel_review/`, print the caption, and wait for you to type `yes` or `no`.

### The options you can add

| Option | What it does |
|---|---|
| `--perplexity "topic"` | Use a topic instead of a YouTube link. Leave the topic out and it uses a default one. |
| `--tone "casual and fun"` | Change the writing style. Default is `professional and engaging`. |
| `--publish` | Don't ask — just post it. |
| `--verbose` | Print a lot more detail about what it's doing. Useful when something breaks. |

Example with everything:

```bash
python main.py --perplexity "AI news this week" --tone "casual and fun" --publish --verbose
```

---

## Letting it run on its own

`automate.py` is the hands-off mode. When you run it, it:

1. Makes sure two copies aren't running at once (it writes a small `automation.lock` file).
2. Sends a "starting" notification, if you set up Discord or email.
3. Looks at `topics_queue.txt`. If there are fewer than 3 topics left, it asks Gemini to brainstorm 7 new ones and adds them to the file.
4. Deletes review images older than 7 days and empties the `temp/` folder.
5. Takes the **first** topic off the list (and removes it from the file so it isn't reused).
6. Runs `main.py` with that topic and `--publish`, so no one has to say yes.
7. Sends a "done" or "failed" notification and writes everything to `automation_log.txt`.

Run it yourself with:

```bash
python automate.py
```

### Your topic list

`topics_queue.txt` is a plain text file. One topic per line. Lines starting with `#` are ignored, so you can use them as notes. Example:

```
# AI tool news
How to use Gemini to study for an exam
Three free AI tools that replace paid apps
```

### Running it every day automatically

On Windows, use Task Scheduler to run `run_generator.bat` at whatever time you want.

**Important:** open `run_generator.bat` first and change the folder path inside it to wherever this project actually lives on your computer. The path in the file right now is from a different machine and will not work as-is.

---

## Getting told when it posts

Optional, but handy. Fill these in inside `.env`:

- `DISCORD_WEBHOOK_URL` — a webhook from your Discord server (Channel Settings → Integrations → Webhooks). You get a message in that channel every run.
- `SMTP_USER`, `SMTP_PASSWORD`, `NOTIFICATION_EMAIL` — for email alerts. With Gmail you must use an **App Password** (https://myaccount.google.com/apppasswords), not your normal password.

Leave them blank and the program simply won't send notifications.

---

## What's in each file

```
main.py                 The one-post-at-a-time command. Start here.
automate.py             The hands-off version that runs on a schedule.
setup_instagram.py      Run once to log into Instagram and save the session.
list_models.py          Small helper: prints which Gemini models your key can use.
run_generator.bat       What Windows Task Scheduler runs.

core/config.py          Reads .env, sets up logging, holds all the file paths.
core/content_engine.py  Gets the facts (YouTube or Perplexity) and writes the post (Gemini).
core/visual_engine.py   Draws the three slide images with Pillow.
core/publisher.py       Logs into Instagram, uploads the carousel, writes the CSV log.
core/brainstormer.py    Refills topics_queue.txt when it runs low.
core/notifier.py        Sends the Discord and email alerts.
core/maintenance.py     Deletes old files so the folder doesn't fill up.

fonts/                  Google Sans font files used on the slides.
topics_queue.txt        Your list of topics waiting to be posted.
published_posts.csv     A record of every post that went out.
automation_log.txt      What automate.py did, with timestamps.
carousel_review/        The finished slides, for you to look at.
temp/                   Scratch images. Cleared automatically.
```

---

## What the slides look like

Every slide is a 1080×1080 square, split into three bands:

- **Top 15%** — the headline, in capitals, filled with a purple-to-cyan gradient.
- **Middle 55%** — the AI-generated picture, in a rounded card with a soft shadow.
- **Bottom 30%** — the body text in white. If the text starts with a question, that question is coloured red to catch the eye.

Behind all of it is a black background with faint wavy "topographic map" lines.

There are always three slides: two with real content, and a last one that says "Follow for more". If you put a ready-made image at `resources/last_slide_cta.jpg`, the program uses that file for the last slide instead of generating one — which saves you API calls.

---

## When things don't work

**Nothing gets posted / "session expired"**
Run `python setup_instagram.py` again.

**"PERPLEXITY_API_KEY not set"**
You used `--perplexity` without that key in `.env`. Either add the key, or give it a YouTube link instead.

**The caption looks basic and the pictures are just a plain gradient**
Your Gemini key is missing, wrong, or out of free quota for the day. The program is deliberately built to keep going instead of crashing — it falls back to simpler options. Check `automation_log.txt` for the reason.

**The YouTube link doesn't work**
Some videos have no transcript available. There's nothing to read, so it stops. Use a different video or use a topic instead.

**"Automation already running"**
A previous run didn't finish cleanly. Delete `automation.lock` and try again.

### Built-in backups

The program tries hard not to fail. At each risky step it has a plan B:

| Step | First choice | Then | Then |
|---|---|---|---|
| Write the post | gemini-2.5-flash | gemini-2.0-flash → 2.0-flash-lite | A plain template caption |
| Make the picture | Gemini image model | Pollinations.ai (free, no key) | A dark gradient drawn by Pillow |
| Fonts | Google Sans files in `fonts/` | Pillow's default font | — |

---

## A note on safety

This project logs into Instagram with your real username and password using `instagrapi`, which is an unofficial library. That means:

- Your credentials sit in `.env` on your own computer. Keep that file private.
- Automated posting is not something Instagram officially supports. Posting too often can get an account restricted. Start slow — once a day is plenty.
- Use an account you can afford to lose, not your main one, until you're confident.

---

## Built with

Python · [google-genai](https://pypi.org/project/google-genai/) (Gemini) · [Perplexity API](https://docs.perplexity.ai/) · [Pillow](https://pillow.readthedocs.io/) · [instagrapi](https://github.com/subzeroid/instagrapi) · [youtube-transcript-api](https://pypi.org/project/youtube-transcript-api/)
