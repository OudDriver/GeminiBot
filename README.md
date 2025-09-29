# GeminiBot: Use the Power of Gemini in Discord! 

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) 

**Get ready to experience the ultimate AI assistant at Discord!** GeminiBot brings Gemini by DeepMind right into your Discord server.  It's not just text; we're talking audio, video, YouTube, generating images, and even talking to it!  

## Table of Contents

- [About](#about)
- [Getting Started](#getting-started)
- [How to Fill config.json](#how-to-fill-configjson)
    - [Owner ID](#owner-id)
    - [Gemini API Key](#gemini-api-key)
    - [Wolfram|Alpha API Key](#wolframalpha-api-key)
    - [Model Names](#model-names)
    - [Discord Token](#discord-token)
    - [System Prompts](#system-prompts)
    - [Harm Block Threshold](#harm-block-threshold)
- [FAQ](#faq)

## About

This project is your implementation of the Gemini LLM in discord. Think of it as a (rather dumb) AI that can understand and respond to your request.  

**Here's what makes GeminiBot special:**

* **Multi-modality:**  Give it audio, video, YouTube links, or just talk to it! Gemini can process it all (check out the supported file formats [here](https://ai.google.dev/gemini-api/docs/prompting_with_media?lang=python#supported_file_formats)). 
* **YouTube Magic:** Want Gemini to analyze a YouTube video? No problem! ~~I use some big brain tricks with `pytubefix` and `ffmpeg` to make things work. Turns out, I can't use `pytube` because that failed miserably.~~ Turns out, I love Google as they did it for me (with less latency too).
* **Tool Integrations:** Tired of LLM messing up your math problems or not getting the weather? Or perhaps is *too offline*? This bot can use the power of Wolfram Alpha, DuckDuckGo, and others for accurate and reliable calculations. ~~It can even give you the steps (If you are lucky and the bot doesn't break down. In the event of the bot screwing up WolframAlpha, feel free to submit a bug report, it's not like I'm going to kill you if you submit useless bug reports.).~~ It's not going to give you the steps. Turns out, Gemini is really honking lazy. And also, WolframAlpha removed that feature from the API. Sad, right?

## Getting Started

1. **Clone the Repo:**  Grab the code and bring it to your machine (make sure you have Python installed). 
2. ~~**FFmpeg is Your Image Friend:** This project needs FFmpeg to handle all the cool media stuff. Don't worry, I've got instructions in the Installing FFmpeg section.~~  It absolutely doesn't need FFmpeg, Google has done the heavy lifting for me.
3. **Install Dependencies:**  Run:
   ```bash
   python setup.py
   ```
   and follow all instructions. Make sure your setup isn't so bad it can't run Docker.
   Sometimes, Linux likes to crap on itself, so, you may have to change the commands inside setup.py so it uses pip3.12 instead of pip, python3.12 instead of python, etc.
   Remember that the CMake command will fail if you're on Windows. It is used to build samplerate.
4. **Configure Your Bot:** Rename `config.example.json` to `config.json` and fill in your bot's details (API keys, etc.), or rename `config.template.json` to `config.json` and fill in the missing blanks.
5. **Launch GeminiBot!**  From your bot's directory, run:
   ```bash
   python bot.py
   ```
   **And that's it!** You're ready to use the power of Gemini in your Discord server.

# How to Fill config.json
## Owner ID
Open up Discord, go to **Settings**, click **Advanced** on the **APP SETTINGS** panel, and click **Developer Mode**. Click `esc`, right-click on your profile, and click **Copy ID**. Then, paste it in the config, of course. 

## Gemini API Key
Make sure you enable the [Generative Language API](https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com), or it will not work. Head over to [Google AI Studio](https://aistudio.google.com/app/prompts/new_chat) and click on that shiny blue button labeled "Get API key" at the top left of the screen. Then, click the boring "Create API Key" in the middle of your screen. Click the blue "Create API key in new project" or select an existing project (usually named "My First Project." I know you).

## Wolfram|Alpha API Key
Go to [the Wolfram|Alpha Api](https://products.wolframalpha.com/api/) and click on the boring orange button named "[Get API Access](https://developer.wolframalpha.com/)" Make a new Wolfram account and click on thet bright orange button labeled "Get an App ID." Give it a boring name like "MyAppID" and a Description because it is required. Then, select any API type. I recommend the "Full Results API." 

## Model Names
Go to [the Gemini API docs on the "all models section"](https://ai.google.dev/gemini-api/docs/models) and just input any of the model variants show (Except imagen, veo, text embedding, and the live variant). Make sure to include the clean name usually shown in blue.

## Discord Token
Really... It's **easy**. Go to [the Discord developer portal](https://discord.com/developers/applications), click on **New Application**, and click **Create**.
Go to the **Bot** section, enable all intents, click **Reset Token** and paste the Discord token into the config file. 
Then, scroll down, click on the **Administrator** permission, click **Copy**, paste it on a new tab, and invite the bot to your server.

## System Prompts
You can go ask ChatGPT for that, or copy my template at `config.template.json`!

## Harm Block Threshold
There are four values you can choose, `BLOCK_LOW_AND_ABOVE`, `BLOCK_MEDIUM_AND_ABOVE`, `BLOCK_ONLY_HIGH`, and `BLOCK_NONE`. They are self-explanatory enough.

# FAQ
* Why is this app giving me weird errors?
  * Well, it seems like you haven't updated the dependencies yet. Run `pip install --upgrade -r requirements.txt`. 
