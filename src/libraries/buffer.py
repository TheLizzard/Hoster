from __future__ import annotations


class BytesBuffer:
    def __init__(self, data:bytes=b""):
        self.data = data

    def __bool__(self) -> bool:
        return len(self.data) > 0

    def __len__(self) -> int:
        return len(self.data)

    def __add__(self, other:BytesBuffer) -> BytesBuffer:
        return BytesBuffer(self.data + other.data)

    def __iadd__(self, other) -> BytesBuffer:
        if isinstance(other, BytesBuffer):
            self.data += other.data
        elif isinstance(other, bytes):
            self.data += other
        else:
            raise ValueError("Can't add \"BytesBuffer\" to " \
                             f"\"{other.__class__.__name__}\"")
        return self

    def read(self, chunk_size:int=1024) -> bytes:
        data, self.data = self.data[:chunk_size], self.data[chunk_size:]
        return data

    def close(self) -> None:
        self.data = b""
