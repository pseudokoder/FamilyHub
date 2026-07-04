import os

from app import create_app

app = create_app()

if __name__ == '__main__':
  # PORT is overridable (macOS parks its AirPlay Receiver on the classic
  # Flask default, 5000) — same 12-factor-config habit as app/config.py.
  app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
