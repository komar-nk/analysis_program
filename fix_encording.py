
import os
import sys
import locale
import shutil
from pathlib import Path, PureWindowsPath


def setup_encoding():
    """Настроить правильную кодировку для Windows"""
    if sys.platform == "win32":
        for encoding in ['utf-8', 'cp1251', 'cp1252', 'cp866']:
            try:
                sys.stdout.reconfigure(encoding=encoding)
                sys.stderr.reconfigure(encoding=encoding)
                break
            except:
                pass

        locale.setlocale(locale.LC_ALL, '')

        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'


def get_correct_path(path_str):
    """Получить правильный путь для Windows"""
    try:
        if isinstance(path_str, str):
            path = Path(path_str)
            try:
                return str(path.resolve())
            except:
                # Подход 3: Используем Windows путь
                return str(PureWindowsPath(path_str))
    except:
        return path_str
    return path_str


