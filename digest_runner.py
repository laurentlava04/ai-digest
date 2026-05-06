"""
AI Daily Digest Runner
Calls the Claude API to generate the daily AI briefing, then posts it to Slack.

Requirements:
  pip install anthropic slack-sdk

Environment variables (set as GitHub Actions secrets or .env):
  ANTHROPIC_API_KEY   — your Anthropic API key
  SLACK_BOT_TOKEN     — Slack bot OAuth token (xoxb-...)
  SLACK_CHANNEL       — target channel, e.g. #ai-digest
"""

import os
import sys
import anthropic
from datetime import date
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# ── Configuration ────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_BOT_TOKEN   = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL     = os.environ.get("SLACK_CHANNEL", "#ai-briefing")

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8000

DIGEST_PROMPT = f"""
Today is {date.today().strftime("%B %d, %Y")}.

Generate the daily AI briefing following these exact instructions:

You are producing a structured daily AI news briefing for Laurent — a Senior Applied
Scientist specializing in agentic systems and LLMs. Coverage window: last 24 hours.

Use web_search to gather content across these sections. Run multiple searches as needed.

SECTION ORDER AND SEARCH STRATEGY:

1. 📄 Research Papers — Focus on agents & agentic systems, LLMs & foundation models.
   Search: "arXiv LLM agents paper site:arxiv.org", "new foundation model paper today",
   "agentic AI research arxiv". Skip narrow benchmark papers unless exceptional.
   Label pre-prints as [Pre-print – not peer reviewed].

2. 🤝 Industry News & Partnerships — Focus on deals that shift the competitive landscape.
   Search: "AI partnership announcement today", "AI company deal collaboration".

3. 🛠️ New AI Tool Features — Flag anything relevant to: Bedrock, Claude, OpenAI APIs,
   RAG systems, multi-agent frameworks.
   Search: "Claude update", "OpenAI GPT new feature", "Gemini update", "AI tool release".

4. 💰 Startup Funding & Launches — Only raises >$20M or notable seed rounds.
   Search: "AI startup funding today", "AI company launch raise".

5. ⚖️ Regulation & Policy — Prioritize EU/US policy, near-term compliance implications.
   Search: "AI regulation policy today", "EU AI Act", "AI governance news".

6. 🗣️ Thought Leaders — Search for recent public posts from these people on X/LinkedIn:
   Andrej Karpathy (@karpathy), Yann LeCun, Dario Amodei (@darioamodei),
   Sam Altman (@sama), Demis Hassabis, Fei-Fei Li, François Chollet (@fchollet),
   Nathan Lambert (@natolambert), Simon Willison (@simonw), Ethan Mollick (@emollick),
   Andriy Burkov, Andrew Ng (@AndrewYNg).
   Only include posts with substantive signal value. Skip hot takes.
   Search pattern: "[name] site:x.com" or "[name] AI post today".
   Only show this section if 2+ quality posts were found.

OUTPUT FORMAT — follow exactly:

# 🤖 AI Daily Digest — {date.today().strftime("%B %d, %Y")}
**Coverage window:** Last 24 hours
**Sources:** Web · Social posts

---

## 📄 Research Papers
*Focus: Agents & agentic systems · LLMs & foundation models*

### [Title] — [Lab]
**[URL]**
[2–3 sentence summary: what was proposed, key result, why it matters]

---

## 🤝 Industry News & Partnerships
### [Headline]
**[Source + URL]**
[2–3 sentence summary]

---

## 🛠️ New AI Tool Features
### [Tool]: [What changed]
**[Source + URL]**
[2–3 sentence summary]

---

## 💰 Startup Funding & Launches
### [Company] raises [amount] — [Focus]
**[Source + URL]**
[2–3 sentence summary]

---

## ⚖️ Regulation & Policy
### [Headline]
**[Source + URL]**
[2–3 sentence summary]

---

## 🗣️ Thought Leaders
*(omit this section if fewer than 2 substantive posts found)*
### [Name] [handle]
**[URL if available]**
[What they said and why it's notable]

---

## 💡 Laurent's Picks
*1–2 items most relevant to Laurent's work on agentic systems, CAMBot/MCP architecture,
or applied LLM science at Amazon Business.*
- **[Item]**: [One sentence on why it's directly relevant]

STYLE RULES:
- Lead with the news, not with context.
- 2–3 sentences max per item — no padding.
- Use → to introduce implications: "→ Relevant for RAG pipeline builders."
- If a section has nothing, write: "Nothing significant surfaced today."
- If something is uncertain, say so.
""".strip()

# ── Claude API call ───────────────────────────────────────────────────────────

def generate_digest() -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("Calling Claude API to generate digest...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": DIGEST_PROMPT}],
    )

    # Extract text content from the response
    digest_text = ""
    for block in response.content:
        if block.type == "text":
            digest_text += block.text

    if not digest_text.strip():
        raise ValueError("Claude returned an empty response — check API call.")

    print(f"Digest generated ({len(digest_text)} chars).")
    return digest_text


# ── Slack posting ─────────────────────────────────────────────────────────────

def post_to_slack(digest: str, channel: str) -> None:
    client = WebClient(token=SLACK_BOT_TOKEN)

    # Slack has a 3000-char limit per block — split into chunks if needed
    chunks = split_into_chunks(digest, max_length=2900)

    print(f"Posting {len(chunks)} message block(s) to {channel}...")
    thread_ts = None

    for i, chunk in enumerate(chunks):
        try:
            if i == 0:
                resp = client.chat_postMessage(
                    channel=channel,
                    text=chunk,
                    mrkdwn=True,
                )
                thread_ts = resp["ts"]
            else:
                # Post continuations as thread replies to keep channel clean
                client.chat_postMessage(
                    channel=channel,
                    text=chunk,
                    thread_ts=thread_ts,
                    mrkdwn=True,
                )
        except SlackApiError as e:
            print(f"Slack error on chunk {i}: {e.response['error']}", file=sys.stderr)
            raise

    print("Successfully posted to Slack.")


def split_into_chunks(text: str, max_length: int = 2900) -> list[str]:
    """Split text on section boundaries (---) to keep sections intact."""
    sections = text.split("\n---\n")
    chunks = []
    current = ""

    for section in sections:
        candidate = current + ("\n---\n" if current else "") + section
        if len(candidate) <= max_length:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            # If single section exceeds limit, hard-split it
            if len(section) > max_length:
                for j in range(0, len(section), max_length):
                    chunks.append(section[j:j + max_length].strip())
                current = ""
            else:
                current = section

    if current:
        chunks.append(current.strip())

    return chunks


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        digest = generate_digest()
        post_to_slack(digest, SLACK_CHANNEL)
        print("✅ Done.")
    except Exception as e:
        print(f"❌ Failed: {e}", file=sys.stderr)
        sys.exit(1)
