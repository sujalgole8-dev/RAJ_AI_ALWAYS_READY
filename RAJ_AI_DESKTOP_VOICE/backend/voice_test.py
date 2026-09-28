"""One-click microphone test for RAJ."""
import speech_recognition as sr

print("=== RAJ MICROPHONE TEST ===")
print("Available microphones:")
for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"  {i}: {name}")
print()

try:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Calibrating for background noise...")
        r.adjust_for_ambient_noise(source, duration=1)
        print("Speak now: say 'open Chrome' and wait...")
        audio = r.listen(source, timeout=8, phrase_time_limit=7)
    print("Audio captured. Converting speech to text...")
    text = r.recognize_google(audio, language="en-IN")
    print("RAJ HEARD:", text)
    print("MICROPHONE TEST PASSED")
except sr.WaitTimeoutError:
    print("FAILED: No speech was detected within 8 seconds.")
except sr.UnknownValueError:
    print("FAILED: Audio was captured, but speech could not be understood.")
except sr.RequestError:
    print("FAILED: Speech-to-text service needs an internet connection.")
except Exception as e:
    print("FAILED:", repr(e))

input("\nPress Enter to close...")
