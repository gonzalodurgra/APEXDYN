import sys
import os

# Añade la carpeta backend al path de python para que resuelva "app"
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

from app.main import app