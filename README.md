# FF AI Support Assistant

This project contains the hybrid edge-cloud implementation for the FF AI Support Assistant.

## Project Structure

## Android command-line build

From `android-sdk`, use `gradlew.bat assembleDebug` after generating the Gradle wrapper.
The sample app defaults to `10.0.2.2` for an Android emulator. For a physical phone, use the
computer's LAN address and keep the FastAPI server reachable on that address:

```powershell
.\gradlew.bat :sample-app:assembleDebug -PffBackendUrl=http://192.168.1.10:8000/
```

The backend must expose `POST /chat` and `POST /ticket`. The SDK caches the latest 100 messages
in app-private SharedPreferences and resumes the cached session on launch.