import openai
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi

openai.api_key = "YOUR_OPENAI_KEY"


def get_video_id(link: str):
    return link.split("v=")[-1].split("&")[0]


def get_transcript(video_id: str) -> str:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except Exception as e:
        return f"Error: {str(e)}"


def extract_strategy(transcript: str) -> str:
    prompt = f"""
You are an expert trader and Python developer. Extract a clear trading strategy in Python pseudocode from the text below:
---
{transcript[:4000]}
---
Return only the core logic, for example:

if close > ma50 and volume > 100000:
    buy()

Use pandas-style code if possible.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def generate_sample_strategy_code(logic: str) -> str:
    return f"""
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

df = yf.download("AAPL", start="2022-01-01", end="2023-01-01")
df["ma50"] = df["Close"].rolling(50).mean()

# Example strategy logic
{logic}

df[["Close", "ma50"]].plot()
plt.title("Strategy Example")
plt.grid(True)
plt.show()
"""


st.title("🧠 YouTube Trading Strategy Bot")

yt_link = st.text_input("📺 Paste YouTube video URL")

if yt_link:
    with st.spinner("Fetching transcript..."):
        video_id = get_video_id(yt_link)
        transcript = get_transcript(video_id)

    st.subheader("🎧 Transcript Preview")
    st.write(transcript[:1000] + "...")

    if st.button("🧠 Extract Strategy"):
        with st.spinner("Analyzing..."):
            logic = extract_strategy(transcript)
            st.subheader("🧩 Strategy Logic")
            st.code(logic, language="python")

            code = generate_sample_strategy_code(logic)
            st.subheader("🧪 Sample Generated Code")
            st.code(code, language="python")

            st.download_button(
                "💾 Download Strategy Code", code, file_name="strategy.py"
            )
