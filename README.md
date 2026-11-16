# 12V DC Motor Digital Twin

A browser-based Streamlit dashboard that reads live motor measurements from ThingSpeak.

## ThingSpeak field mapping

| Field | Measurement |
|---|---|
| Field 1 | Temperature (°C) |
| Field 2 | Vibration (events/s) |
| Field 3 | Current (A) |
| Field 4 | RPM |
| Field 5 | Voltage (V) |
| Field 6 | ESP32 status code (not used for dashboard condition calculation) |

The dashboard calculates NORMAL / WARNING / FAULT from the editable limits in Settings.
It does not display average labels or average values.

## Run on your computer

1. Install Python 3.10 or newer.
2. Extract this ZIP file.
3. Open Command Prompt in the extracted folder.
4. Install the packages:

   `python -m pip install -r requirements.txt`

5. Start the dashboard:

   `python -m streamlit run app.py`

6. Open the local URL shown in Command Prompt, usually `http://localhost:8501`.
7. In the left Settings panel, enter ThingSpeak Channel ID `3581766` and your channel Read API Key.

## Run remotely using Streamlit Community Cloud

1. Create a GitHub account if you do not already have one.
2. Create a new GitHub repository.
3. Upload `app.py` and `requirements.txt` to the repository.
4. Open https://share.streamlit.io/ and sign in with GitHub.
5. Choose **New app**, select the repository, branch, and `app.py`.
6. Before or after deployment, open the app's **Settings / Secrets** section.
7. Add the following secrets, replacing the value with your actual ThingSpeak Read API Key:

   ```toml
   THINGSPEAK_CHANNEL_ID = "3581766"
   THINGSPEAK_READ_API_KEY = "YOUR_READ_API_KEY"
   ```

8. Save the secrets and reboot the app.
9. Open the generated public app URL from any device with internet access.

Keep the Read API Key in Streamlit Secrets. Do not put it in a public GitHub repository.

## Settings

The left panel lets you edit:
- Temperature, vibration, current, and voltage warning/fault limits
- Dashboard title and subtitle
- Accent colour
- Which sensor cards and trend charts are visible
- Refresh interval and chart history length

The current settings are session-based. They apply while that browser session is active. A persistent shared settings store can be added later if settings must survive browser resets or be shared between users.

## Notes

- The ESP32 must be powered and connected to Wi-Fi for new readings to arrive.
- The app refreshes automatically. ThingSpeak's free channel update interval is normally at least 15 seconds; this dashboard defaults to 20 seconds.
- Your current ESP32 sketch uploads rolling-average sensor values. The dashboard does not label them as averages, but the underlying values remain rolling averages until the ESP32 firmware is changed.
- The dashboard is for monitoring and demonstration. Do not use it as the only protection against motor overheating, overcurrent, or overvoltage.
