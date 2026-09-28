# RAJ AI — Always Listening Windows Voice Assistant

RAJ is a local Windows assistant with a browser dashboard and a Python desktop microphone engine.

## Always Listening
- RAJ starts with **Always Listening ON** by default.
- The Python backend listens directly to the Windows microphone.
- Say **"Raj" + your command**, for example:
  - "Raj open Chrome"
  - "Raj open YouTube"
  - "Raj increase volume"
  - "Raj take a screenshot"
  - "Raj close window"
- The browser is only the dashboard. The microphone engine runs in the Python backend.
- If the voice engine stops, the dashboard automatically tries to restart it while Always Listening is ON.

## Start with Windows
Run `enable_startup.bat` once. RAJ will launch automatically when you sign in to Windows.

To disable it, run `disable_startup.bat`.

## First-time setup
1. Extract the ZIP.
2. Run `start_raj.bat`.
3. Allow microphone access if Windows asks.
4. Keep **Always Listening ON**.
5. Say: **"Raj open Chrome"**.

## Microphone test
Run `test_microphone.bat` if RAJ does not hear you.

## Requirements
- Windows 10/11
- Python 3
- Working microphone
- Internet connection for Google speech-to-text used by SpeechRecognition
