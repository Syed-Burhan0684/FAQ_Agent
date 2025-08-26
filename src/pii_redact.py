import re

# simple PII redaction: emails, phone numbers, CNIC-like numbers (Pakistan), credit card-like
_email_re = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_phone_re = re.compile(r"(\+?\d[\d\- ]{7,}\d)")
_cc_re = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_cnic_re = re.compile(r"\b\d{5}-\d{7}-\d\b")


def redact_pii(text: str) -> str:
    t = _email_re.sub('[REDACTED_EMAIL]', text)
    t = _phone_re.sub('[REDACTED_PHONE]', t)
    t = _cc_re.sub('[REDACTED_CC]', t)
    t = _cnic_re.sub('[REDACTED_CNIC]', t)
    return t
