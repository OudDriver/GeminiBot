# GeminiBot: Use the Power of Gemini in Discord! 

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) 

**Get ready to experience the (sassy) AI assistant at Discord!** GeminiBot brings Gemini by DeepMind right into your Discord server.  It's not just text; we're talking audio, video, and even YouTube!  

## Table of Contents

- [About](#about)
- [Getting Started](#getting-started)
- [Installing FFmpeg](#installing-ffmpeg)
    - [Windows](#windows)
    - [MacOS](#macos)
    - [Linux](#linux)
- [API Keys](#api-keys)
    - [Gemini API](#gemini-api)
    - [Wolfram|Alpha API](#wolframalpha-api)
- [FAQ](#faq)

## About

This project is your implementation of the Gemini LLM in discord. Think of it as a (rather dumb) AI that can understand and respond to your request.  

**Here's what makes GeminiBot special:**

* **Multi-modality:**  Give it audio, video, or even YouTube links! Gemini can process it all (check out the supported file formats [here](https://ai.google.dev/gemini-api/docs/prompting_with_media?lang=python#supported_file_formats)). 
* **YouTube Magic:** Want Gemini to analyze a YouTube video? No problem! I use some big brain tricks with `pytubefix` and `ffmpeg` to make things work. Turns out, I can't use `pytube` because that failed miserably.
* **Wolfram Alpha Integration:** Tired of LLM messing up your math problems? This bot can use the power of Wolfram Alpha for accurate and reliable calculations. It can even give you the steps (If you are lucky and the bot doesn't break down. In the event of the bot screwing up WolframAlpha, feel free to submit a bug report, it's not like I'm gonna kill you if you submit useless bug reports.).

## Getting Started

1. **Clone the Repo:**  Grab the code and bring it to your machine (make sure you have Python installed). 
2. **FFmpeg is Your Image Friend:** This project needs FFmpeg to handle all the cool media stuff. Don't worry, I've got instructions in the [Installing FFmpeg](#installing-ffmpeg) section. 
3. **Install Dependencies:**  Make sure everything works smoothly by installing the necessary packages:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Your Bot:** Rename `config.example.json` to `config.json` and fill in your bot's details (API keys, etc.), or rename `config.template.json` to `config.json` and fill in the missing blanks.
5. **Launch GeminiBot!**  From your bot's directory, run:
   ```bash
   python bot.py
   ```
   **And that's it!** You're ready to use the power of Gemini in your Discord server.

## Installing FFmpeg

### Windows

**Easy Mode (Chocolatey or Winget):** 
If you have Chocolatey or Winget, you're in for a treat! Just run:

```bash
choco install ffmpeg-full 
```

or 

```bash
winget install ffmpeg
```

**Hard Mode:**
1. **Download:** Head over to [https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z) to download the latest FFmpeg (make sure you have a 7z extractor like 7zip).
2. **Extract:**  Extract the files to a location of your choice (e.g., `C:\ffmpeg`).
3. **Add to PATH:**
    1. Search for "environment variables" in the Start menu.
    2. Select "Edit environment variables for your account".
    3. Find the "Path" variable in the "User variables" section and click "Edit...".
    4. Click "New" and add the path to your FFmpeg `bin` folder (e.g., `C:\ffmpeg\bin`).
    5. Click "OK" on all open windows to save.
4. **Verify:** Open a new command prompt (cmd) or PowerShell and type `ffmpeg -version`. You should see the FFmpeg version information. 

### MacOS

1. **Install Homebrew (if you don't have it):**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 
   ```
2. **Install FFmpeg:**
   ```bash
   brew install ffmpeg 
   ```
3. **Verify:** Type `ffmpeg -version` in Terminal. 

### Linux

Most Linux distributions make it super easy! Use your package manager:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Fedora/CentOS/RHEL:**
```bash
sudo dnf install ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S ffmpeg 
```

**Verify:** After installation, type `ffmpeg -version` in your terminal.

# API Keys
## Gemini API
Make sure you enable the [Generative Language API](https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com), or it will not work. Head over to [Google AI Studio](https://aistudio.google.com/app/prompts/new_chat) and click on that shiny blue button labeled "Get API key" at the top left of the screen. Then, click the boring "Create API Key" in the middle of your screen. Click the blue "Create API key in new project" or select an existing project (usually named "My First Project." I know you).

## Wolfram|Alpha API
Go to [the Wolfram|Alpha Api](https://products.wolframalpha.com/api/) and click on the boring orange button named "[Get API Access](https://developer.wolframalpha.com/)" Make a new Wolfram account and click on thet bright orange button labeled "Get an App ID." Give it a boring name like "MyAppID" and a Description because it is required. Then, select any API type. I recommend the "Full Results API." 

# FAQ
* Damn, why is this app giving me weird errors?
  * Well, it seems like you haven't updated the dependencies yet. Run `pip install --upgrade -r requirements.txt`. 