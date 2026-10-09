"""Public donation metadata only. No Ko-fi API key belongs in an image."""
from pathlib import Path
URL = 'https://ko-fi.com/transcendenceia'
MESSAGE = ('Cuando un equipo falla, detrás hay recuerdos, trabajo y personas que no quieren perderlos. '
           'LA AGUJA nace para ayudarles a recuperarlos. Si te acompañó en un momento difícil, '
           'tu café nos ayuda a seguir cuidando este proyecto libre. Gracias por sostenerlo.')


def qr_path():
    installed = Path('/usr/share/aguja/donation-qr.png')
    return installed if installed.is_file() else Path(__file__).resolve().parents[1] / 'branding/donation/qr.png'
