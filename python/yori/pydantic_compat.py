"""
Pydantic compatibility layer for environments without pydantic

This provides a minimal BaseModel implementation that mimics pydantic's API
but doesn't require compilation or Rust.
"""

try:
    from pydantic import BaseModel, Field
    HAVE_PYDANTIC = True
except ImportError:
    HAVE_PYDANTIC = False

    # Simple BaseModel replacement
    class BaseModel:
        """Minimal BaseModel implementation without pydantic"""

        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self):
            """Return dict representation"""
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

        def json(self):
            """Return JSON representation"""
            import json
            return json.dumps(self.dict())

        @classmethod
        def parse_obj(cls, obj):
            """Parse from dict"""
            return cls(**obj)

    # Simple Field replacement
    def Field(default=None, **kwargs):
        """Minimal Field implementation"""
        return default


__all__ = ['BaseModel', 'Field', 'HAVE_PYDANTIC']
