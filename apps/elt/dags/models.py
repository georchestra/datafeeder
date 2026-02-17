from pydantic import Literal

SourceType = Literal["FILE", "URL", "FTP", "DATABASE", "API"]
