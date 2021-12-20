from aiohttp.web import Request
import string
import random

strings = string.ascii_lowercase + string.digits

def getIp(request: Request):
    try:
        _ip = request.headers['X-Forwarded-For']
        if _ip.find(",") != -1:
            _ip = _ip.split(",")[0]
    except:
        _ip = request.remote
    
    return _ip

def is_eng_digits(text: str):
    text = text.lower()

    for char in strings:
        text = text.replace(char, "")
    
    return len(text) == 0

def password_formatter(password: str):
    if len(password) > 16:
        raise ValueError(f"Password is too long ({len(password)} letters)")
        
    while len(password) < 16:
        password += "0"
    
    return password

def random_string(length: int = 16):
    return "".join(random.choice(strings) for _ in range(length))