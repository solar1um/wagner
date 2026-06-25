import sys
import os
import json
import threading
import webbrowser
import subprocess
import ctypes
import flask
import webview
from wagner.backend import api


def _should_register_shell():
    if sys.platform != 'win32':
        return False
    try:
        key = r'Software\Classes\.acd\shell\wagner'
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key):
            return False
    except OSError:
        return True


def _register_shell():
    if sys.platform != 'win32':
        return False, 'Not Windows'
    try:
        import winreg
        exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        if not getattr(sys, 'frozen', False):
            exe = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
        else:
            exe = f'"{exe}"'
        icon = exe.replace('"', '')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r'Software\Classes\.acd\shell\wagner') as k:
            winreg.SetValue(k, '', winreg.REG_SZ, 'Edit with Wagner')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r'Software\Classes\.acd\shell\wagner\command') as k:
            winreg.SetValue(k, '', winreg.REG_SZ, f'{exe} "%1"')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r'Software\Classes\.acd') as k:
            pass

        return True, None
    except Exception as e:
        return False, str(e)


def _unregister_shell():
    if sys.platform != 'win32':
        return False, 'Not Windows'
    try:
        import winreg
        import winreg as _wr
        key_path = r'Software\Classes\.acd\shell\wagner'
        def _delkey(root, path):
            try:
                _wr.DeleteKey(root, path)
            except OSError:
                pass
        _delkey(winreg.HKEY_CURRENT_USER, key_path + r'\command')
        _delkey(winreg.HKEY_CURRENT_USER, key_path)
        return True, None
    except Exception as e:
        return False, str(e)


def _get_first_run_flag_path():
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    return os.path.join(appdata, '.wagner', 'first_run_done')


def _check_first_run():
    flag = _get_first_run_flag_path()
    if os.path.exists(flag):
        return False
    os.makedirs(os.path.dirname(flag), exist_ok=True)
    with open(flag, 'w') as f:
        f.write('1')
    return True


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'wagner')  # noqa: SLF001
    return os.path.dirname(os.path.abspath(__file__))


def create_app(initial_file=None):
    static_folder = os.path.join(_get_base_dir(), 'static')

    app = flask.Flask(__name__, static_folder=static_folder, static_url_path='')

    @app.route('/')
    def index():
        path = os.path.join(static_folder, 'index.html')
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        injected = f'<script>window._INITIAL_FILE={json.dumps(initial_file or "")};</script>'
        html = html.replace('</head>', injected + '\n</head>')
        return html

    app.register_blueprint(api, url_prefix='/api')
    app.config['initial_file'] = initial_file
    return app


class ACDTunerAPI:
    def __init__(self, initial_file=None):
        self.initial_file = initial_file

    def get_initial_file(self):
        return self.initial_file or ''

    def should_register(self):
        return sys.platform == 'win32' and _should_register_shell()

    def register_shell(self):
        ok, err = _register_shell()
        return {'ok': ok, 'error': err}

    def unregister_shell(self):
        ok, err = _unregister_shell()
        return {'ok': ok, 'error': err}

    def is_first_run(self):
        if not hasattr(self, '_first_run'):
            self._first_run = _check_first_run()
        return self._first_run

    def select_file_dialog(self):
        try:
            result = webview.windows[0].create_file_dialog(
                webview.OPEN_DIALOG,
                directory='',
                file_types=('ACD Files (*.acd)',),
                allow_multiple=False
            )
            if result and len(result) > 0:
                return result[0]
        except Exception:
            pass
        return ''

    def get_system_info(self):
        return {
            'platform': sys.platform,
            'frozen': getattr(sys, 'frozen', False),
        }


def main():
    initial_file = None
    if len(sys.argv) > 1:
        candidate = sys.argv[1]
        if os.path.isfile(candidate) and candidate.lower().endswith('.acd'):
            initial_file = os.path.abspath(candidate)

    app = create_app(initial_file)
    api_obj = ACDTunerAPI(initial_file)

    window = webview.create_window(
        'Wagner',
        app,
        js_api=api_obj,
        width=1100,
        height=750,
        min_size=(800, 500),
    )

    webview.start(debug=False)


if __name__ == '__main__':
    main()
