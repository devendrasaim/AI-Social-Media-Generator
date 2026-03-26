# 🎙️ The Social Speaker: Your 24/7 AI Instagram Engine

Stop overthinking your social media. **The Social Speaker** is a fully autonomous content engine that researches, writes, designs, and publishes premium "Dark Mode" Instagram carousels while you sleep. 

It doesn't just "generate posts"—it tells stories with a mysterious, captivating tone that connects with people.

---

## ✨ Why this is different
- **Autonomous Storytelling:** Uses Gemini and Perplexity to find trending news and turn it into engaging "Do you know...?" narratives.
- **Premium Aesthetics:** High-end dark mode designs with topographic textures and dynamic gradient headlines.
- **Smart Highlighting:** Automatically detects hooks and highlights them in **Vibrant Red** to stop the scroll.
- **Set & Forget:** Integrated with Windows Task Scheduler to run daily, completely hands-off.
- **Auto-Refill Queue:** When you run out of ideas, the AI brainstorms new topics for you based on your niche.

---

## 🛠️ How it works
1.  **Research:** It scans the web for the latest in AI, Tech Jobs, and CEO news.
2.  **Compose:** Gemini writes a 3-slide carousel with a mysterious "Social Speaker" persona.
3.  **Design:** The engine builds professional 1080x1080 images with custom typography.
4.  **Publish:** Content is instantly published to Instagram via the Blotato API.
5.  **Alert:** You get a Discord notification on your phone the second it's live.

---

## 🚀 Setting Up Your GURU

### 1. The Essentials
Clone the repo and install the requirements:
```bash
git clone <your-repo-url>
cd AI-Social-Media-Generator
pip install -r requirements.txt
```

### 2. Add Your Magic Keys
Rename `.env.example` to `.env` and add your keys:
- **Blotato API:** For publishing.
- **Gemini API:** For the "brains" and visuals.
- **Perplexity API:** For deep-web research.
- **Discord Webhook:** (Optional) For phone alerts.

### 3. Start the Pilot
To run a manual test:
```bash
python main.py --perplexity "Latest AI breakthroughs" --publish
```

To let it run on **Auto-Pilot**, simply add your topics to `topics_queue.txt` and set up a Windows Task Scheduler trigger for `automate.py`.

---

## 🛡️ Privacy & Security
This project uses a `.env` system to follow security best practices. **Never** share your `.env` file or API keys. The `.gitignore` is pre-configured to keep your sensitive logs and keys private.

---

*Made with 🧠 for creators who want to spend more time building and less time posting.*
