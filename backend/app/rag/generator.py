"""Evidence-grounded response generation, citation binding, and abstention engine."""


from app.rag.models import Citation, EvidenceChunk


class GroundedGenerator:
    """Generates clinically grounded responses with explicit inline citations and strict abstention."""

    MULTILINGUAL_ABSTENTION_MESSAGES = {
        "en": (
            "Insufficient authoritative clinical evidence: ClintelAI could not locate verified medical "
            "guidance from WHO, ICMR, MoHFW, or PubMed addressing this specific query. To ensure medical safety "
            "and prevent misinformation, we abstain from generating unverified medical guidance. "
            "Please consult a registered healthcare professional for clinical advice."
        ),
        "ta": (
            "போதுமான அதிகாரப்பூர்வ மருத்துவ சான்றுகள் இல்லை: ClintelAI இந்த குறிப்பிட்ட கேள்விக்கு "
            "WHO, ICMR அல்லது MoHFW இலிருந்து சரிபார்க்கப்பட்ட வழிகாட்டுதலைக் கண்டறிய முடியவில்லை. "
            "மருத்துவப் பாதுகாப்பை உறுதி செய்வதற்காக, சரிபார்க்கப்படாத ஆலோசனைகளை நாங்கள் வழங்குவதில்லை. "
            "தயவுசெய்து பதிவுசெய்த மருத்துவரை அணுகவும்."
        ),
        "hi": (
            "अपर्याप्त आधिकारिक चिकित्सीय साक्ष्य: ClintelAI इस विशिष्ट प्रश्न पर WHO, ICMR या MoHFW से "
            "सत्यापित चिकित्सीय मार्गदर्शन प्राप्त नहीं कर सका। सुरक्षा सुनिश्चित करने के लिए हम असत्यापित "
            "जानकारी उत्पन्न नहीं करते हैं। कृपया किसी पंजीकृत चिकित्सक से परामर्श करें।"
        ),
        "ml": (
            "ആധികാരിക മെഡിക്കൽ തെളിവുകൾ അപര്യാപ്തമാണ്: ഈ നിർദ്ദിഷ്ട അന്വേഷണത്തിന് WHO, ICMR അല്ലെങ്കിൽ "
            "MoHFW-ൽ നിന്നുള്ള പരിശോധിച്ചുറപ്പിച്ച മാർഗ്ഗനിർദ്ദേശങ്ങൾ കണ്ടെത്താൻ ClintelAI-ക്ക് കഴിഞ്ഞില്ല. "
            "സുരക്ഷ ഉറപ്പാക്കാൻ ഞങ്ങൾ സ്ഥിരീകരിക്കാത്ത വിവരങ്ങൾ നൽകുന്നില്ല. ദയവായി ഒരു ഡോക്ടറെ സമീപിക്കുക."
        ),
        "te": (
            "సరిపడా అధికారిక వైద్య ఆధారాలు లేవు: ఈ నిర్దిష్ట ప్రశ్నకు WHO, ICMR లేదా MoHFW నుండి "
            "ధృవీకరించబడిన వైద్య మార్గదర్శకాలను ClintelAI కనుగొనలేకపోయింది. భద్రతను నిర్ధారించడానికి మేము "
            "ధృవీకరించని సలహాలను అందించము. దయచేసి రిజిస్టర్డ్ వైద్యుడిని సంప్రదించండి."
        ),
        "kn": (
            "ಸಾಕಷ್ಟು ಅಧಿಕೃತ ವೈದ್ಯಕೀಯ ಪುರಾವೆಗಳಿಲ್ಲ: ಈ ನಿರ್ದಿಷ್ಟ ಪ್ರಶ್ನೆಗೆ WHO, ICMR ಅಥವಾ MoHFW ನಿಂದ "
            "ಪರಿಶೀಲಿಸಿದ ವೈದ್ಯಕೀಯ ಮಾರ್ಗದರ್ಶನವನ್ನು ಪಡೆಯಲು ClintelAI ಗೆ ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಸುರಕ್ಷತೆಯನ್ನು ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಲು "
            "ನಾವು ಪರಿಶೀಲಿಸದ ಸಲಹೆಯನ್ನು ನೀಡುವುದಿಲ್ಲ. ದಯವಿಟ್ಟು ನೋಂದಾಯಿತ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ."
        ),
    }

    MULTILINGUAL_SECTION_HEADERS = {
        "en": {
            "findings": "Evidence-Grounded Clinical Summary",
            "guidelines": "Key Authoritative Recommendations",
            "precautions": "Clinical Precautions & Red Flags",
        },
        "ta": {
            "findings": "சான்று சார்ந்த மருத்துவ சுருக்கம்",
            "guidelines": "முக்கிய அதிகாரப்பூர்வ பரிந்துரைகள்",
            "precautions": "மருத்துவ முன்னெச்சரிக்கைகள் மற்றும் எச்சரிக்கை அறிகுறிகள்",
        },
        "hi": {
            "findings": "साक्ष्य-आधारित चिकित्सीय सारांश",
            "guidelines": "प्रमुख आधिकारिक दिशानिर्देश",
            "precautions": "चिकित्सीय सावधानियां और खतरे के संकेत",
        },
        "ml": {
            "findings": "തെളിവ് അടിസ്ഥാനമാക്കിയുള്ള മെഡിക്കൽ സംഗ്രഹം",
            "guidelines": "പ്രധാന ആധികാരിക ശുപാർശകൾ",
            "precautions": "മുൻകരുതലുകളും അപകട സൂചനകളും",
        },
        "te": {
            "findings": "ఆధారిత వైద్య సారాంశం",
            "guidelines": "ముఖ్య అధికారిక మార్గదర్శకాలు",
            "precautions": "వైద్య జాగ్రత్తలు మరియు ప్రమాద సంకేతాలు",
        },
        "kn": {
            "findings": "ಸಾಕ್ಷ್ಯಾಧಾರಿತ ವೈದ್ಯಕೀಯ ಸಾರಾಂಶ",
            "guidelines": "ಪ್ರಮುಖ ಅಧಿಕೃತ ಮಾರ್ಗದರ್ಶನಗಳು",
            "precautions": "ವೈದ್ಯಕೀಯ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು ಮತ್ತು ಎಚ್ಚರಿಕೆ ಚಿಹ್ನೆಗಳು",
        },
    }

    @classmethod
    def generate_response(
        cls,
        query: str,
        evidence: list[tuple[EvidenceChunk, float]],
        language: str = "en",
        emergency_detected: bool = False,
    ) -> tuple[str, list[Citation], bool, str | None]:
        """Synthesizes an evidence-grounded answer with inline citations or triggers abstention.

        Delegates to the configured LLM provider (mock or gemini) with full evidence grounding.

        Returns:
            (answer_text, citations_list, abstained_bool, abstention_reason)
        """
        from app.rag.providers.factory import get_llm_provider

        provider = get_llm_provider()
        return provider.generate_grounded_response(
            query=query,
            evidence=evidence,
            language=language,
            emergency_detected=emergency_detected,
        )
