#!/usr/bin/env python3
"""
Entry point for PyInstaller packaging.
Ensures working directory and config resolution work in both dev and frozen exe.
"""
import os
import sys
import logging

def setup_paths():
    """Set up sys.path and working directory for frozen exe."""
    if getattr(sys, "frozen", False):
        # Running in a PyInstaller bundle
        # _MEIPASS is the temporary folder where bundled assets are extracted
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
        # Ensure config and uploads are next to the exe, not inside _MEIPASS
        os.chdir(os.path.dirname(sys.executable))
    else:
        # Running in normal Python environment
        base_path = os.path.abspath(".")
    # Add app to path if not already
    app_path = os.path.join(base_path, "app")
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    return base_path

def main():
    base_path = setup_paths()
    # Import after path setup
    from app.main import app
    import uvicorn

    # Optional: read host/port from config or env
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    # For exe, we don't use --reload
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
