import sys
import os

# Añade la carpeta backend al path de python para que resuelva los módulos 'app'
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

