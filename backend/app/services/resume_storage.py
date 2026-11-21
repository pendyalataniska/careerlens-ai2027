import base64
import os
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import PROJECT_ROOT, Settings, get_settings

_FILE_MAGIC = b"CLRS1"


class PrivateResumeStorage:
    """Encrypted, non-public local storage for uploaded resume bytes."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        material = (
            self.settings.resume_encryption_key.get_secret_value().encode("utf-8")
            if self.settings.resume_encryption_key
            else self.settings.secret_key.get_secret_value().encode("utf-8")
        )
        self._key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"careerlens-resume-storage-v1",
        ).derive(material)
        configured_root = self.settings.resume_storage_dir
        self.root = (
            configured_root
            if configured_root.is_absolute()
            else PROJECT_ROOT / configured_root
        ).resolve()

    def save(self, resume_id: uuid.UUID, contents: bytes) -> str:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "posix":
            self.root.chmod(0o700)
        storage_key = f"{resume_id.hex}.clrs"
        destination = self._resolve_key(storage_key)
        nonce = os.urandom(12)
        encrypted = _FILE_MAGIC + nonce + AESGCM(self._key).encrypt(
            nonce, contents, resume_id.bytes
        )
        temporary = self.root / f".{resume_id.hex}.{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as file:
                file.write(encrypted)
                file.flush()
                os.fsync(file.fileno())
            if os.name == "posix":
                temporary.chmod(0o600)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return storage_key

    def read(self, resume_id: uuid.UUID, storage_key: str) -> bytes:
        encrypted = self._resolve_key(storage_key).read_bytes()
        if not encrypted.startswith(_FILE_MAGIC) or len(encrypted) < len(_FILE_MAGIC) + 12:
            raise ValueError("Stored resume has an invalid encrypted format.")
        nonce_start = len(_FILE_MAGIC)
        nonce = encrypted[nonce_start : nonce_start + 12]
        ciphertext = encrypted[nonce_start + 12 :]
        return AESGCM(self._key).decrypt(nonce, ciphertext, resume_id.bytes)

    def encrypt_metadata(self, resume_id: uuid.UUID, contents: bytes) -> str:
        nonce = os.urandom(12)
        encrypted = AESGCM(self._key).encrypt(
            nonce, contents, resume_id.bytes + b":contact-information-v1"
        )
        return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")

    def decrypt_metadata(self, resume_id: uuid.UUID, encrypted: str) -> bytes:
        contents = base64.urlsafe_b64decode(encrypted.encode("ascii"))
        if len(contents) < 12:
            raise ValueError("Encrypted resume metadata is invalid.")
        return AESGCM(self._key).decrypt(
            contents[:12],
            contents[12:],
            resume_id.bytes + b":contact-information-v1",
        )

    def delete(self, storage_key: str) -> None:
        self._resolve_key(storage_key).unlink(missing_ok=True)

    def _resolve_key(self, storage_key: str) -> Path:
        try:
            key_id = uuid.UUID(hex=Path(storage_key).stem)
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid resume storage key.") from exc
        if f"{key_id.hex}.clrs" != storage_key:
            raise ValueError("Invalid resume storage key.")
        resolved = (self.root / storage_key).resolve()
        if resolved.parent != self.root:
            raise ValueError("Invalid resume storage path.")
        return resolved
