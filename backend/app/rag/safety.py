"""Clinical safety boundary enforcement, red-flag emergency detection, and medical disclaimers."""

import re

from app.rag.models import EmergencyEscalation


class MedicalSafetyEngine:
    """Enforces clinical boundaries, detects emergency symptoms, and prevents diagnostic overreach."""

    # Red-flag clinical emergency keywords and patterns
    EMERGENCY_PATTERNS = {
        "CRITICAL": [
            r"\b(crushing|severe|radiating|pressure)\s+(chest\s+pain|chest\s+tightness)\b",
            r"\bchest\s+pain\s+(radiating|spreading)\s+to\s+(arm|jaw|neck|back)\b",
            r"\b(can'?t\s+breathe|severe\s+shortness\s+of\s+breath|gasping|choking|stridor)\b",
            r"\b(sudden\s+numbness|facial\s+droop|face\s+drooping|slurred\s+speech|cannot\s+speak|arm\s+weakness)\b",
            r"\b(coughing\s+up\s+blood|vomiting\s+blood|coffee[\s\-]ground\s+vomit|massive\s+bleeding|uncontrolled\s+bleeding)\b",
            r"\b(anaphylaxis|throat\s+swelling|closing\s+throat|tongue\s+swelling)\b",
            r"\b(suicid(e|al)|kill\s+myself|end\s+my\s+life|want\s+to\s+die)\b",
            r"\b(loss\s+of\s+consciousness|unresponsive|passed\s+out|fainted\s+and\s+not\s+waking)\b",
            # Indic Critical patterns
            r"(நெஞ்சு\s*வலி|மூச்சுத்\s*திணறல்|இரத்த\s*வாந்தி|தற்கொலை|மயங்கி)",
            r"(सीने\s*में\s*दर्द|सांस\s*लेने\s*में\s*दिक्कत|खून\s*की\s*उल्टी|बेहोश|आत्महत्या)",
            r"(നെഞ്ചുവേദന|ശ്വാസംമുട്ടൽ|രക്തം\s*ഛർദ്ദി|ആത്മഹത്യ|ബോധക്ഷയം)",
            r"(ఛాతీ\s*నొప్పి|శ్వాస\s*ఆడకపోవడం|రక్తం\s*వాంతులు|ఆత్మహత్య|స్పృహ\s*తప్ప)",
            r"(ಎದೆ\s*ನೋವು|ಉಸಿರಾಟದ\s*ತೊಂದರೆ|ರಕ್ತ\s*ವಾಂತಿ|ಆತ್ಮಹತ್ಯೆ|ಪ್ರಜ್ಞೆ\s*ತಪ್ಪ)",
        ],
        "HIGH": [
            r"\b(severe\s+abdominal\s+pain|persistent\s+vomiting\s+and\s+fever)\b",
            r"\b(dengue\s+warning\s+signs|mucosal\s+bleeding|bleeding\s+gums\s+with\s+fever)\b",
            r"\b(hypoglycemia|blood\s+sugar\s+(below|less\s+than)\s+50|confusion\s+with\s+diabetes)\b",
            r"\b(seizure|convulsion|fitting)\b",
            r"\b(high\s+fever\s+in\s+infant|baby\s+not\s+feeding\s+and\s+lethargic)\b",
            r"\b(severe\s+headache\s+with\s+blurred\s+vision\s+in\s+pregnancy)\b",
            # Indic High patterns
            r"(வயிற்று\s*வலி|வலிப்பு|தீவிர\s*காய்ச்சல்)",
            r"(पेट\s*में\s*तेज\s*दर्द|दौरा|तेज\s*बुखार)",
            r"(കഠിനമായ\s*വയറുവേദന|ഫിറ്റ്സ്|അതികഠിനമായ\s*പനി)",
            r"(తీవ్రమైన\s*కడుపునొప్పి|మూర్ఛ|అధిక\s*జ్వరం)",
            r"(ತೀವ್ರ\s*ಹೊಟ್ಟೆ\s*ನೋವು|ಫಿಟ್ಸ್|ಹೆಚ್ಚಿನ\s*ಜ್ವರ)",
        ]
    }

    MULTILINGUAL_EMERGENCY_MESSAGES = {
        "en": "IMMEDIATE EMERGENCY ACTION REQUIRED: Your symptoms indicate a potential medical emergency. Immediately dial 112 or 108 or proceed to the nearest emergency hospital. Do not wait for online information.",
        "ta": "உடனடி அவசர மருத்துவ உதவி தேவை: உங்கள் அறிகுறிகள் உயிருக்கு ஆபத்தான அவசரநிலையைக் குறிக்கின்றன. உடனடியாக 112 அல்லது 108 என்ற எண்ணை அழைக்கவும் அல்லது அவசர சிகிச்சை பிரிவுக்குச் செல்லவும்.",
        "hi": "तत्काल आपातकालीन चिकित्सा सहायता आवश्यक है: आपके लक्षण एक संभावित आपातकालीन चिकित्सा स्थिति का संकेत देते हैं। तुरंत 112 या 108 पर कॉल करें या नजदीकी आपातकालीन अस्पताल जाएं।",
        "ml": "അടിയന്തിര വൈദ്യസഹായം ആവശ്യമാണ്: നിങ്ങളുടെ ലക്ഷണങ്ങൾ ഗുരുതരമായ അടിയന്തിരാവസ്ഥയെ സൂചിപ്പിക്കുന്നു. ഉടൻ തന്നെ 112 അല്ലെങ്കിൽ 108 എന്ന നമ്പറിൽ വിളിക്കുകയോ അടുത്തുള്ള ആശുപത്രിയിൽ പോകുകയോ ചെയ്യുക.",
        "te": "తక్షణ అత్యవసర వైద్య సహాయం అవసరం: మీ లక్షణాలు ప్రాణాంతక అత్యవసర పరిస్థితిని సూచిస్తున్నాయి. వెంటనే 112 లేదా 108 కి కాల్ చేయండి లేదా సమీప అత్యవసర ఆసుపత్రికి వెళ్లండి.",
        "kn": "ತಕ್ಷಣದ ತುರ್ತು ವೈದ್ಯಕೀಯ ನೆರವು ಅಗತ್ಯವಿದೆ: ನಿಮ್ಮ ರೋಗಲಕ್ಷಣಗಳು ಸಂಭಾವ್ಯ ವೈದ್ಯಕೀಯ ತುರ್ತುಸ್ಥಿತಿಯನ್ನು ಸೂಚಿಸುತ್ತವೆ. ತಕ್ಷಣವೇ 112 ಅಥವಾ 108 ಗೆ ಕರೆ ಮಾಡಿ ಅಥವಾ ಹತ್ತಿರದ ತುರ್ತು ಆಸ್ಪತ್ರೆಗೆ ಭೇಟಿ ನೀಡಿ.",
    }

    MULTILINGUAL_DISCLAIMERS = {
        "en": "Medical Disclaimer: ClintelAI provides evidence-grounded health information from authoritative global and national bodies (WHO, ICMR, MoHFW). It is NOT a clinical diagnosis or medical prescription. Always consult a qualified physician for personalized clinical care. In medical emergencies, immediately dial 112 or 108.",
        "ta": "மருத்துவ மறுப்புரை: ClintelAI அதிகாரப்பூர்வ உலகளாவிய மற்றும் தேசிய சுகாதார அமைப்புகளின் (WHO, ICMR, MoHFW) சான்றுகளின் அடிப்படையில் தகவல்களை வழங்குகிறது. இது மருத்துவ நோயறிதல் அல்லது மருந்துச்சீட்டு அல்ல. மருத்துவ அவசரநிலைகளில் உடனடியாக 112 அல்லது 108 ஐ அழைக்கவும்.",
        "hi": "चिकित्सीय अस्वीकरण: ClintelAI आधिकारिक निकायों (WHO, ICMR, MoHFW) से साक्ष्य-आधारित स्वास्थ्य जानकारी प्रदान करता है। यह कोई चिकित्सीय निदान या नुस्खा नहीं है। आपात स्थिति में तुरंत 112 या 108 पर कॉल करें।",
        "ml": "മെഡിക്കൽ നിരാകരണം: ClintelAI ആധികാരിക ഏജൻസികളുടെ (WHO, ICMR, MoHFW) തെളിവുകളെ അടിസ്ഥാനമാക്കി ആരോഗ്യ വിവരങ്ങൾ നൽകുന്നു. ഇത് രോഗനിർണ്ണയമോ കുറിപ്പടിയോ അല്ല. അടിയന്തിര സാഹചര്യങ്ങളിൽ 112 അല്ലെങ്കിൽ 108 ഡയൽ ചെയ്യുക.",
        "te": "వైద్య నిరాకరణ: ClintelAI అధికారిక సంస్థల (WHO, ICMR, MoHFW) నుండి ఆధారాలతో కూడిన ఆరోగ్య సమాచారాన్ని అందిస్తుంది. ఇది వైద్య నిర్ధారణ లేదా ప్రిస్క్రిప్షన్ కాదు. అత్యవసర పరిస్థితుల్లో వెంటనే 112 లేదా 108 కి కాల్ చేయండి.",
        "kn": "ವೈದ್ಯಕೀಯ ಹಕ್ಕುತ್ಯಾಗ: ClintelAI ಅಧಿಕೃತ ಸಂಸ್ಥೆಗಳಿಂದ (WHO, ICMR, MoHFW) ಸಾಕ್ಷ್ಯ ಆಧಾರಿತ ಆರೋಗ್ಯ ಮಾಹಿತಿಯನ್ನು ಒದಗಿಸುತ್ತದೆ. ಇದು ವೈದ್ಯಕೀಯ ರೋಗನಿರ್ಣಯ ಅಥವಾ ಪ್ರಿಸ್ಕ್ರಿಪ್ಷನ್ ಅಲ್ಲ. ತುರ್ತು ಸಂದರ್ಭಗಳಲ್ಲಿ ತಕ್ಷಣವೇ 112 ಅಥವಾ 108 ಗೆ ಕರೆ ಮಾಡಿ.",
    }

    @classmethod
    def evaluate_emergency(cls, query: str, language: str = "en") -> EmergencyEscalation:
        """Evaluates whether the user's query contains red-flag emergency symptoms."""
        query_lower = query.lower()
        detected_symptoms: list[str] = []
        highest_level = "NONE"

        # Check CRITICAL
        for pattern in cls.EMERGENCY_PATTERNS["CRITICAL"]:
            match = re.search(pattern, query_lower)
            if match:
                detected_symptoms.append(match.group(0))
                highest_level = "CRITICAL"

        # Check HIGH if not already critical
        if highest_level != "CRITICAL":
            for pattern in cls.EMERGENCY_PATTERNS["HIGH"]:
                match = re.search(pattern, query_lower)
                if match:
                    detected_symptoms.append(match.group(0))
                    highest_level = "HIGH"

        if highest_level != "NONE":
            action_msg = cls.MULTILINGUAL_EMERGENCY_MESSAGES.get(
                language, cls.MULTILINGUAL_EMERGENCY_MESSAGES["en"]
            )
            return EmergencyEscalation(
                is_emergency=True,
                level=highest_level,
                symptoms_detected=detected_symptoms,
                action_message=action_msg,
                emergency_numbers=["112", "108"],
            )

        return EmergencyEscalation(
            is_emergency=False,
            level="NONE",
            symptoms_detected=[],
            action_message="",
            emergency_numbers=["112", "108"],
        )

    @classmethod
    def sanitize_medical_text(cls, text: str) -> str:
        """Enforces clinical boundaries so generation never speaks as a definitive diagnostic authority."""
        # Replace definitive diagnoses phrases
        replacements = [
            (r"\bYou have ([a-zA-Z\s]+)\b", r"Clinical guidelines indicate these symptoms may be associated with \1"),
            (r"\bYou are diagnosed with\b", r"Potential clinical considerations include"),
            (r"\bI prescribe\b", r"Standard clinical guidelines frequently indicate"),
            (r"\bTake (\d+\s*mg)\b", r"Consult your physician regarding appropriate dosing of"),
        ]
        sanitized = text
        for pattern, repl in replacements:
            sanitized = re.sub(pattern, repl, sanitized, flags=re.IGNORECASE)
        return sanitized

    @classmethod
    def get_disclaimer(cls, language: str = "en") -> str:
        """Returns the appropriate localized clinical disclaimer."""
        return cls.MULTILINGUAL_DISCLAIMERS.get(language, cls.MULTILINGUAL_DISCLAIMERS["en"])
