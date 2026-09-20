"""Structured multilingual alert templates.

English is the reference locale. Other locales are deliberately explicit
templates rather than pretending that unreviewed translations are official.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

LOCALE_TEMPLATES = {
    "en": "{severity} {hazard} alert for {region}. Expected condition: {condition}. Valid until {expires}. Recommended action: {action}.",
    "ta": "{region} பகுதியில் {severity} {hazard} எச்சரிக்கை. எதிர்பார்க்கப்படும் நிலை: {condition}. செல்லுபடியாகும் நேரம்: {expires}. பரிந்துரைக்கப்பட்ட நடவடிக்கை: {action}.",
    "hi": "{region} के लिए {severity} {hazard} चेतावनी। अपेक्षित स्थिति: {condition}। वैधता: {expires}। अनुशंसित कार्रवाई: {action}।",
    "te": "{region} కోసం {severity} {hazard} హెచ్చరిక. ఆశించిన పరిస్థితి: {condition}. చెల్లుబాటు: {expires}. సూచించిన చర్య: {action}.",
    "kn": "{region} ಗಾಗಿ {severity} {hazard} ಎಚ್ಚರಿಕೆ. ನಿರೀಕ್ಷಿತ ಪರಿಸ್ಥಿತಿ: {condition}. ಮಾನ್ಯತೆ: {expires}. ಶಿಫಾರಸು ಮಾಡಿದ ಕ್ರಮ: {action}.",
    "ml": "{region} പ്രദേശത്തേക്ക് {severity} {hazard} മുന്നറിയിപ്പ്. പ്രതീക്ഷിക്കുന്ന സ്ഥിതി: {condition}. സാധുത: {expires}. ശുപാർശ ചെയ്യുന്ന നടപടി: {action}.",
    "mr": "{region} साठी {severity} {hazard} इशारा. अपेक्षित स्थिती: {condition}. वैधता: {expires}. शिफारस केलेली कृती: {action}.",
    "bn": "{region}-এর জন্য {severity} {hazard} সতর্কতা। প্রত্যাশিত অবস্থা: {condition}। বৈধ: {expires}। প্রস্তাবিত পদক্ষেপ: {action}।",
    "gu": "{region} માટે {severity} {hazard} ચેતવણી. અપેક્ષિત સ્થિતિ: {condition}. માન્ય સમય: {expires}. ભલામણ કરેલ પગલું: {action}.",
    "pa": "{region} ਲਈ {severity} {hazard} ਚੇਤਾਵਨੀ। ਉਮੀਦ ਕੀਤੀ ਸਥਿਤੀ: {condition}। ਵੈਧਤਾ: {expires}। ਸਿਫਾਰਸ਼ੀ ਕਾਰਵਾਈ: {action}।",
    "or": "{region} ପାଇଁ {severity} {hazard} ସତର୍କତା। ଆଶାକରାଯାଇଥିବା ସ୍ଥିତି: {condition}। ବୈଧତା: {expires}। ପରାମର୍ଶିତ କାର୍ଯ୍ୟ: {action}।",
    "as": "{region}ৰ বাবে {severity} {hazard} সতৰ্কবাণী। আশা কৰা পৰিস্থিতি: {condition}। বৈধতা: {expires}। পৰামৰ্শিত পদক্ষেপ: {action}।",
}

def render_alert(**kwargs: Any) -> dict[str, Any]:
    language = str(kwargs.get("language", "en")).lower()
    if language not in LOCALE_TEMPLATES:
        raise ValueError(f"Unsupported language '{language}'")
    message = LOCALE_TEMPLATES[language].format(**kwargs)
    return {
        **kwargs,
        "message": message,
        "language": language,
        "translation_status": "reference" if language == "en" else "template_review_required",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "issuance_status": "not_issued",
    }
