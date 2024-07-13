# GeminiBot

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) 

A Gemini LLM implementation in Discord. 

## Table of Contents

- [About](#about)
- [Getting Started](#getting-started)
- [Installing FFmpeg](#installing-ffmpeg)
    - [Windows](#windows)
    - [MacOS](#macos)
    - [Linux](#linux)

## About

This project is a cool implementation of the Gemini LLM by Google in Discord. It supports audio, video, and audio inputs. Check [https://ai.google.dev/gemini-api/docs/prompting_with_media?lang=python#supported_file_formats](https://ai.google.dev/gemini-api/docs/prompting_with_media?lang=python#supported_file_formats) for supported file formats. 

It also supports YouTube videos input. It uses the `pytube` to download the video and audio seperately (due to a constraint in the package) and uses `ffmpeg` to combine those two. Then, it sends it to the the Gemini API server. Using the uploaded fiels in the Gemini API server, the bot will prompt Gemini the text you submitted and the video (with audio... hopefully).
## Getting Started

Clone this repo to your machine with python installed. This projects need FFmpeg. Refer to [Installing FFmpeg](#installing-ffmpeg) to get started on that. After that, run
```bash
pip install -r requirements.txt
```
This ensures that all dependencies are installed correctly.

Make a `config.json` file at the directory of your bot. It should consists of
- `GeminiAPI`: Your API key for Gemini API
- `DiscordToken`: Your Discord bot token
- `OwnerID`: Your Owner ID


Then, start the bot using
```bash
python bot.py
```
at the bot working directory. 

## Installing FFmpeg

### Windows

If you have Chocolatey or Winget, you are in luck! Just run
```bash
choco install ffmpeg-full
```
or
```bash
winget install ffmpeg
```
And skip the hassle of doing it manually! Or else, just follow the instructions below.

1. **Download:** Go to [https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z) for a direct download of the latest FFmpeg version. Make sure you have an app that can extract 7z files (e.g., 7zip).
2. **Extract:** Extract the downloaded zip file to a location of your choice (e.g., `C:\ffmpeg`).
3. **Add to PATH:** 
    1. Open the Start menu and search for "environment variables".
    2. Select "Edit environment variables for your account".
    3. In the "User variables for {user}" section, find the "Path" variable and click "Edit...".
    4. Click "New" inside teh "Edit enviroment table" window and add the path to your FFmpeg `bin` folder (e.g., `C:\ffmpeg\bin`).
    5. Click "OK" on all open windows to save the changes.
4. **Verify:** Open a new command prompt (cmd) or powershell and type `ffmpeg -version`. If the installation was successful, you'll see the FFmpeg version information.

### MacOS

1. **Install Homebrew (if you haven't already):** 
    * Open Terminal and paste the following command:
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```
    * Follow the on-screen instructions.
2. **Install FFmpeg:** Run the following command in Terminal:
    ```bash
    brew install ffmpeg
    ```
3. **Verify:** Type `ffmpeg -version` in Terminal. 

### Linux

Most Linux distributions have FFmpeg available in their package repositories. You can install it using your distribution's package manager. For example:

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

**Verify:** After installation, type `ffmpeg -version` in your terminal to verify. 