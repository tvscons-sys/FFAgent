"""Simple cached FAQ responses for common vehicle support issues.

This keeps the existing retrieval pipeline intact while allowing the chatbot to
answer a small set of common, user-friendly questions without running the heavy
vector search flow.
"""

from __future__ import annotations

import re
from functools import lru_cache

FAQ_ITEMS = [
    {
        "id": "map_not_working",
        "question": "Why is my map not working?",
        "keywords": ["map", "navigation", "nav", "route"],
        "answer": (
            "If your navigation is not working, it may be because your phone is running on an older software version.\n\n"
            "The recommended fix is to update your phone's operating system to the newest Android or Apple iOS version, "
            "and make sure you are using the latest version of the app for the best experience."
        ),
    },
    {
        "id": "otp_not_received",
        "question": "Why am I not getting the OTP?",
        "keywords": ["otp", ],
        "answer": (
            "There are a few reasons why you might not be getting the verification code.\n\n"
            "Your vehicle might not be properly connected to the network, so it needs to be in an area with good network coverage.\n\n"
            "You might also be trying to log in with a different mobile number than the one you originally used when booking or taking delivery.\n\n"
            "You will need to use your original contact number."
        ),
    },
    {
        "id": "bluetooth_call_screen_missing",
        "question": "Why is the call screen missing?",
        "keywords": [ "incoming call", "call screen", "missed call"],
        "answer": (
            "The phone call screen on your cluster may not be working because a background service responsible for the phone app was missing a necessary restart when the vehicle started up.\n\n"
            "To solve this issue right now, you can simply reboot the system. A permanent fix is also coming in Release 1.0.4 to prevent this from happening again."
        ),
    },
    {
        "id": "vehicle_data_not_syncing",
        "question": "Why is my vehicle data not syncing?",
        "keywords": ["sync", "data not syncing", "customer app", "app not syncing", "vehicle data"],
        "answer": (
            "Your vehicle data might not be syncing with the mobile app for a few reasons.\n\n"
            "One common cause is a buffer overflow issue where the temporary data storage fills up. Another possibility is a system reboot during an active trip, which can cause current trip data to be lost.\n\n"
            "Temporary network issues can also prevent communication, which usually resolves itself automatically without any action needed.\n\n"
            "A software update, Release 1.0.4, is coming to address these issues, but in the meantime, clearing the temporary data buffer on the vehicle can help."
        ),
    },
    {
        "id": "service_due_still_shown",
        "question": "Why is the service reminder still showing?",
        "keywords": ["service due", "service reminder", "service warning", "service due warning"],
        "answer": (
            "When your service is complete, the Flying Flea service team needs to reset the reminder to start the countdown for your next service interval.\n\n"
            "If it is still showing, it likely has not been reset yet. I recommend contacting your Authorized Flying Flea Dealer to have them reset it for you."
        ),
    },
    {
        "id": "cloud_not_connecting",
        "question": "Why is my vehicle not connecting to the cloud?",
        "keywords": ["cloud", "not connecting", "onboarding", "setup", "customer app onboarding"],
        "answer": (
            "The issue where the customer app was not connecting with the cloud was caused by a system requirement where a specific identifier, the SOM BLE MacID, was required when writing to the database, even though it was not required at the supplier feed.\n\n"
            "To fix this, the required check was removed in the CRM service, and the supplier feed was automated with all the needed parameters so it will not fail.\n\n"
            "This fix was fully completed and released in August 2026."
        ),
    },
    {
        "id": "fault_ticket_not_received",
        "question": "Why was my fault not sent to GRID?",
        "keywords": ["grid", "fault ticket", "ticket not received", "grafana", "fault report"],
        "answer": (
            "Your fault was not sent to GRID because the vehicle was missed from the authorized vehicles filters.\n\n"
            "Support tickets for these faults are only created for authorized customer vehicles."
        ),
    },
    {
        "id": "wifi_disconnects_when_app_opens",
        "question": "Why does my Wi-Fi disconnect when I open the app?",
        "keywords": ["wifi", "wi-fi", "disconnect", "home wifi", "wifi disconnect"],
        "answer": (
            "If you are using a phone with Android 14 or an older version, opening the app can cause your home Wi-Fi to disconnect.\n\n"
            "This happens because of a system limitation in those older phone versions that causes the Wi-Fi to disconnect and connect to the vehicle cluster.\n\n"
            "To help prevent this, the owner manual recommends keeping your phone's operating system and the app updated to the latest versions for the best experience."
        ),
    },
    {
        "id": "app_logs_me_out",
        "question": "Why does the app log me out automatically?",
        "keywords": ["sign out", "logs me out", "logout", "auto sign out"],
        "answer": (
            "The app was logging you out automatically because of a network drop when returning to the home screen.\n\n"
            "This caused a temporary connection failure, and the app mistakenly treated that failure as an invalid session, which forced you to be logged out.\n\n"
            "An update has been released to fix this so that temporary connection issues no longer sign you out. The changes have already been pushed out, though it may take a little time to reach all Android and iOS devices through the standard app store update process."
        ),
    },
    {
        "id": "password_pin_overlap",
        "question": "Why is the PIN screen overlapping the home screen?",
        "keywords": ["pin screen", "password", "overlap", "home screen", "screen overlap"],
        "answer": (
            "I'm sorry, but the provided support documents do not contain information explaining why the PIN screen is overlapping the home screen."
        ),
    },
]


def _normalize(text: str) -> str:
    """Normalize text to make FAQ matching stable and simple."""
    if not text:
        return ""
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@lru_cache(maxsize=1)
def get_faq_suggestions() -> list[str]:
    """Return a small list of short, user-friendly FAQ prompts."""
    return [item["question"] for item in FAQ_ITEMS]


def match_faq(query: str) -> dict | None:
    """Return an FAQ only when the user selected or typed its exact question."""
    if not query or not query.strip():
        return None

    normalized = _normalize(query)
    for item in FAQ_ITEMS:
        if normalized == _normalize(item["question"]):
            return item

    return None
