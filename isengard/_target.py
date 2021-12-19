from typing import Optional
from hashlib import sha256
from struct import pack, unpack


class Target:
    __slots__ = ()

    def generate_fingerprint(self) -> Optional[bytes]:
        raise NotImplementedError

    def clean(self) -> None:
        raise NotImplementedError

    def distclean(self) -> None:
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__} {self}>"

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))


class FileTarget(Target):
    __slots__ = ("path", )

    def __init__(self, path):
        self.path = Path(path)

    def __str__(self):
        return f"{self.path}"

    def delete(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def generate_fingerprint(self) -> Optional[bytes]:
        fingerprint = bytearray(40)  # 8 bytes timestamp + 32 bytes sha256 hash
        try:
            fingerprint[:32] = pack("!q", self.path.stat().st_mtime)
            fingerprint[32:] = sha256(self.path.read_bytes()).digest()
            return fingerprint
        except FileNotFoundError:
            return None


class FolderTarget(Target):
    __slots__ = ("path", )

    def __str__(self):
        return f"{self.path}"

    def __init__(self, path):
        self.path = Path(path)

    def generate_fingerprint(self) -> Optional[bytes]:
        try:
            # TODO: also test path is a directory
            return pack("!q", self.path.stat().st_mtime)
        except FileNotFoundError:
            return None


class VirtualTarget(Target):
    __slots__ = ("name", )

    def __str__(self):
        return f"{self.name}@"

    def __repr__(self):
        return f"<VirtualTarget {self.name}@>"

    def __init__(self, name):
        self.name = name

    def generate_fingerprint(self) -> Optional[bytes]:
        return None
