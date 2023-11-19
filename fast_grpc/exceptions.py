class GRPCException(Exception):
    key: str | None = None
    description: str | None = None
    data: dict | None = None

    def __init__(
            self,
            key: str | None = None,
            description: str | None = None,
            data: dict | None = None,
    ):
        self.key = key or self.key
        self.description = description or self.description
        self.data = data or self.data
