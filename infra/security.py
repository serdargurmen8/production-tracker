"""
infra/security.py
-------------------
Şifre hash'leme / doğrulama.

Ek bir bağımlılık (bcrypt, passlib vb.) gerektirmemek için
Python'ın standart kütüphanesindeki PBKDF2-HMAC-SHA256 kullanılır
(NIST SP 800-132 tarafından da önerilen, kurulum gerektirmeyen bir
yöntemdir). Her şifre için ayrı rastgele salt üretilir; hash asla
düz metin olarak saklanmaz.

Saklanan format:
    pbkdf2_sha256$<iterasyon>$<salt-hex>$<hash-hex>

Bu format sayesinde ileride iterasyon sayısı artırılmak istenirse
eski kayıtlar bozulmadan yeni girişlerde yeniden hash'lenebilir.
"""

import hashlib
import hmac
import os

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


def hash_password(plain_password: str) -> str:
    """Düz metin şifreyi veritabanında saklanacak hash string'ine çevirir."""

    if not plain_password:
        raise ValueError("Şifre boş olamaz.")

    salt = os.urandom(_SALT_BYTES)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )

    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Girilen şifreyi, veritabanında saklanan hash ile karşılaştırır.
    Format bozuksa veya boşsa (eski/geçersiz kayıt) güvenli tarafta
    kalınır ve False döner.
    """

    if not plain_password or not stored_hash:
        return False

    try:
        algorithm, iterations_str, salt_hex, hash_hex = stored_hash.split("$")

        if algorithm != _ALGORITHM:
            return False

        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)

        derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            int(iterations_str),
        )

        return hmac.compare_digest(derived, expected)

    except (ValueError, AttributeError, TypeError):
        return False
