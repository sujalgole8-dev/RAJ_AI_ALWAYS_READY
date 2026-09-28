"""Desktop microphone voice engine for RAJ.
Uses the Windows microphone directly through SpeechRecognition/PyAudio.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import speech_recognition as sr


class VoiceEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 250
        self.recognizer.pause_threshold = 0.7
        self.recognizer.phrase_threshold = 0.2
        self.recognizer.non_speaking_duration = 0.4
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.listening = False
        self.always = False
        self.latest_text = ""
        self.latest_id = 0
        self.error = ""
        self._lock = threading.Lock()

    def status(self):
        with self._lock:
            return {
                "listening": self.listening,
                "always": self.always,
                "text": self.latest_text,
                "id": self.latest_id,
                "error": self.error,
            }

    def _set_error(self, message: str):
        with self._lock:
            self.error = message

    def _publish(self, text: str):
        with self._lock:
            self.latest_text = text
            self.latest_id += 1
            self.error = ""

    def start(self, always: bool = False):
        if self.thread and self.thread.is_alive():
            with self._lock:
                self.always = always
            return True
        self.stop_event.clear()
        with self._lock:
            self.always = always
            self.listening = True
            self.error = ""
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.stop_event.set()
        with self._lock:
            self.listening = False
            self.always = False
        return True

    def _run(self):
        try:
            with sr.Microphone() as source:
                # Quick calibration. The user does not need to do anything.
                self.recognizer.adjust_for_ambient_noise(source, duration=0.7)
                self.recognizer.dynamic_energy_threshold = True

                while not self.stop_event.is_set():
                    try:
                        with self._lock:
                            always = self.always
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=7)
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as exc:
                        self._set_error(f"Microphone error: {exc}")
                        break

                    try:
                        # Google's speech endpoint is used only for speech-to-text;
                        # the actual Windows commands remain local and whitelisted.
                        text = self.recognizer.recognize_google(audio, language="en-IN").strip()
                        if text:
                            self._publish(text)
                            if not always:
                                break
                    except sr.UnknownValueError:
                        self._set_error("I could not understand that. Try again.")
                        if not always:
                            break
                    except sr.RequestError as exc:
                        self._set_error("Speech service needs internet access.")
                        if not always:
                            break
                    except Exception as exc:
                        self._set_error(f"Voice recognition error: {exc}")
                        if not always:
                            break
        except OSError:
            self._set_error("No microphone was found. Check Windows microphone permissions and input device.")
        except Exception as exc:
            self._set_error(f"Voice engine could not start: {exc}")
        finally:
            with self._lock:
                self.listening = False
            # Small delay avoids a race with a new start request.
            time.sleep(0.05)


voice_engine = VoiceEngine()
