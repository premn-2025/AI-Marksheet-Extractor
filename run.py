#!/usr/bin/env python3
"""
Marksheet Extraction API Runner
"""
import uvicorn
from app.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )