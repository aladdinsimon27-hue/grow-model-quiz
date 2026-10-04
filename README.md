# Grow Model Quiz Agent

Automates daily quiz answers sent via SMS to a specific shortcode using Termux, Termux:API, and Groq.

## Setup

1. Install Termux and Termux:API from F-Droid.
2. Run `pkg update && pkg upgrade -y`
3. Run `pkg install -y python termux-api git`
4. Run `pip install requests`
5. Edit `config.json` and insert your Groq API key.
6. Run `python quiz_agent.py`

## How it works

- Reads recent SMS using `termux-sms-list`.
- Filters messages from the configured shortcode.
- Extracts the latest question.
- Sends the question to Groq for analysis.
- Sends the answer letter (A/B/C/D) back via `termux-sms-send`.
- Repeats for 5 questions.

## License

MIT
