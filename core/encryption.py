from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# .env dosyasindan anahtari al veya yeni bir tane uret (guvenlik icin .env'de saklanmali)
env_path = ".env"
if not os.path.exists(env_path) and os.path.exists("tools/.env"):
    env_path = "tools/.env"
load_dotenv(env_path, override=True)
SECRET_KEY = os.getenv("ENCRYPTION_KEY")

if not SECRET_KEY:
    # Eger anahtar yoksa uret ve .env'ye ekle (Sadece ilk kurulumda)
    SECRET_KEY = Fernet.generate_key().decode()
    # Not: Gercek ortamda bu kisim manuel yapilmalidir.
    # Burada otomatik eklemeye calisiyoruz:
    try:
        with open(env_path, "a") as f:
            f.write(f"\nENCRYPTION_KEY={SECRET_KEY}")
    except Exception as e:
        import logging
        logging.error(f"Failed to save encryption key to {env_path}: {e}")

cipher_suite = Fernet(SECRET_KEY.encode())

def encrypt_password(password: str) -> str:
    """Metni sifreler."""
    if not password: return ""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Sifreli metni cozer."""
    if not encrypted_password: return ""
    try:
        return cipher_suite.decrypt(encrypted_password.encode()).decode()
    except Exception as e:
        import logging
        logging.error(f"Decryption failed: {e}")
        return encrypted_password # Eger zaten sifreli degilse (eskiler) kendisini don
