import os
import shutil
import copy
import acd
from flask import Blueprint, request, jsonify

api = Blueprint('api', __name__)

_state = {
    'path': None,
    'data': None,
    'original': None,
    'diff_path': None,
    'diff_data': None,
    'changed_files': set(),
}


def _get_car_name(data):
    for key, content in data.items():
        if key.endswith('.ini'):
            for line in content.split('\n'):
                if 'SCREEN_NAME=' in line:
                    return line.split('=', 1)[1].strip()
                if 'SHORT_NAME=' in line and 'SCREEN_NAME=' not in content:
                    return line.split('=', 1)[1].strip()
    return os.path.basename(_state.get('path', 'Unknown'))


def _strip_comment(value):
    return value.split(';', 1)[0].strip()


def _get_quick_info(data):
    info = {'mass': None, 'limiter': None, 'power_peak': None}
    if 'car.ini' in data:
        for line in data['car.ini'].split('\n'):
            if line.startswith('TOTALMASS='):
                try:
                    info['mass'] = float(_strip_comment(line.split('=', 1)[1]))
                except ValueError:
                    pass
    if 'engine.ini' in data:
        for line in data['engine.ini'].split('\n'):
            if line.startswith('LIMITER='):
                try:
                    info['limiter'] = int(float(_strip_comment(line.split('=', 1)[1])))
                except ValueError:
                    pass

    boost = 0.0
    if 'engine.ini' in data:
        in_turbo = False
        for line in data['engine.ini'].split('\n'):
            trimmed = line.strip()
            if trimmed.startswith('[TURBO'):
                in_turbo = True
                continue
            if in_turbo and trimmed.startswith('[') and trimmed.endswith(']'):
                in_turbo = False
                continue
            if in_turbo and trimmed.startswith('WASTEGATE='):
                try:
                    v = float(_strip_comment(trimmed.split('=', 1)[1]))
                    if v > boost:
                        boost = v
                except ValueError:
                    pass

    if 'power.lut' in data:
        lines = data['power.lut'].strip().split('\n')
        max_power = 0
        for line in lines:
            line = _strip_comment(line)
            if '|' in line:
                try:
                    _, power = line.split('|', 1)
                    p = float(power.strip())
                    if p > max_power:
                        max_power = p
                except ValueError:
                    pass
        if max_power > 0:
            info['power_peak'] = int(max_power * (1 + boost))
    return info


@api.route('/open', methods=['POST'])
def open_file():
    req = request.get_json()
    path = req.get('path', '')

    if not os.path.isfile(path):
        return jsonify({'error': f'File not found: {path}'}), 404

    try:
        data = acd.read_file(path)
        _state['path'] = path
        _state['data'] = data
        _state['original'] = copy.deepcopy(data)
        _state['diff_path'] = None
        _state['diff_data'] = None
        _state['changed_files'] = set()

        files = sorted(data.keys())
        info = _get_quick_info(data)
        car_name = _get_car_name(data)

        return jsonify({
            'path': path,
            'car_name': car_name,
            'files': files,
            'info': info,
        })
    except Exception as e:
        return jsonify({'error': f'Failed to read ACD: {str(e)}'}), 500


@api.route('/file', methods=['GET'])
def get_file():
    name = request.args.get('name', '')
    if _state['data'] is None:
        return jsonify({'error': 'No ACD file opened'}), 400

    if name not in _state['data']:
        return jsonify({'error': f'File not found in ACD: {name}'}), 404

    is_changed = name in _state['changed_files']
    is_lut = name.endswith('.lut')

    return jsonify({
        'name': name,
        'content': _state['data'][name],
        'changed': is_changed,
        'is_lut': is_lut,
    })


@api.route('/save', methods=['POST'])
def save_file():
    req = request.get_json() or {}
    action = req.get('action', 'save')  # 'save' or 'save_as'
    new_path = req.get('new_path', _state['path'])

    if _state['data'] is None:
        return jsonify({'error': 'No ACD file opened'}), 400

    try:
        # Backup original if saving to same path
        if action == 'save' and _state['path'] == new_path:
            bak = _state['path'] + '.bak'
            if not os.path.exists(bak):
                shutil.copy2(_state['path'], bak)

        acd.write_file(_state['data'], new_path)
        _state['path'] = new_path
        _state['original'] = copy.deepcopy(_state['data'])
        _state['changed_files'] = set()

        return jsonify({
            'success': True,
            'path': new_path,
            'backup': _state['path'] + '.bak' if action == 'save' else None,
        })
    except Exception as e:
        return jsonify({'error': f'Failed to save ACD: {str(e)}'}), 500


@api.route('/edit', methods=['POST'])
def edit_file():
    req = request.get_json()
    name = req.get('name', '')
    content = req.get('content', '')

    if _state['data'] is None:
        return jsonify({'error': 'No ACD file opened'}), 400

    if name not in _state['data']:
        return jsonify({'error': f'File not found: {name}'}), 404

    _state['data'][name] = content
    _state['changed_files'].add(name)

    return jsonify({'success': True, 'name': name})


@api.route('/edit_param', methods=['POST'])
def edit_param():
    req = request.get_json()
    name = req.get('name', '')
    param = req.get('param', '')
    value = req.get('value', '')

    if _state['data'] is None:
        return jsonify({'error': 'No ACD file opened'}), 400

    if name not in _state['data']:
        return jsonify({'error': f'File not found: {name}'}), 404

    section = None
    real_param = param
    if '::' in param:
        section, real_param = param.rsplit('::', 1)

    content = _state['data'][name]
    lines = content.split('\n')
    found = False
    in_section = section is None

    for i, line in enumerate(lines):
        trimmed = line.strip()
        if section and trimmed == section:
            in_section = True
            continue
        if section and trimmed.startswith('[') and trimmed.endswith(']'):
            in_section = False
            continue
        if in_section and line.startswith(f'{real_param}='):
            lines[i] = f'{real_param}={value}'
            found = True
            break

    if not found:
        return jsonify({'error': f'Parameter not found: {param}'}), 404

    new_content = '\n'.join(lines)
    _state['data'][name] = new_content
    _state['changed_files'].add(name)

    return jsonify({'success': True, 'name': name, 'param': param, 'value': value})


@api.route('/summary', methods=['GET'])
def summary():
    if _state['data'] is None:
        return jsonify({'error': 'No ACD file opened'}), 400

    info = _get_quick_info(_state['data'])
    orig_info = _get_quick_info(_state['original']) if _state['original'] else info

    info['car_name'] = _get_car_name(_state['data'])
    info['path'] = _state['path']
    info['changed_files'] = sorted(_state['changed_files'])
    info['changed_count'] = len(_state['changed_files'])

    changes = []
    for key in ['mass', 'limiter', 'power_peak']:
        if info.get(key) != orig_info.get(key) and orig_info.get(key) is not None:
            changes.append({'param': key, 'from': orig_info[key], 'to': info[key]})
    info['changes'] = changes

    return jsonify(info)


@api.route('/diff', methods=['POST'])
def diff():
    req = request.get_json()
    path = req.get('path', '')

    if not os.path.isfile(path):
        return jsonify({'error': f'File not found: {path}'}), 404

    try:
        diff_data = acd.read_file(path)
        _state['diff_path'] = path
        _state['diff_data'] = diff_data

        current_files = set(_state['data'].keys()) if _state['data'] else set()
        diff_files = set(diff_data.keys())
        all_files = sorted(current_files | diff_files)

        diff_result = []
        for f in all_files:
            cur = _state['data'].get(f, '')
            other = diff_data.get(f, '')
            status = 'same'
            if f not in current_files:
                status = 'added'
            elif f not in diff_files:
                status = 'removed'
            elif cur != other:
                status = 'modified'
            diff_result.append({
                'name': f,
                'status': status,
                'current': cur if status in ('modified', 'removed') else None,
                'other': other if status in ('modified', 'added') else None,
            })

        return jsonify({
            'current_path': _state['path'],
            'diff_path': path,
            'files': diff_result,
        })
    except Exception as e:
        return jsonify({'error': f'Failed to diff ACD: {str(e)}'}), 500


@api.route('/undo', methods=['POST'])
def undo():
    if _state['original'] is None:
        return jsonify({'error': 'Nothing to undo'}), 400

    _state['data'] = copy.deepcopy(_state['original'])
    _state['changed_files'] = set()

    return jsonify({'success': True})


@api.route('/reset', methods=['POST'])
def reset():
    req = request.get_json() or {}
    restore_original = req.get('restore_original', False)

    if _state['path'] is None:
        return jsonify({'error': 'No file opened'}), 400

    bak_path = _state['path'] + '.bak'

    if restore_original and os.path.isfile(bak_path):
        shutil.copy2(bak_path, _state['path'])

    try:
        data = acd.read_file(_state['path'])
        _state['data'] = data
        _state['original'] = copy.deepcopy(data)
        _state['changed_files'] = set()
        _state['diff_path'] = None
        _state['diff_data'] = None

        info = _get_quick_info(data)
        car_name = _get_car_name(data)
        files = sorted(data.keys())

        return jsonify({
            'path': _state['path'],
            'car_name': car_name,
            'files': files,
            'info': info,
            'has_backup': os.path.isfile(bak_path),
        })
    except Exception as e:
        return jsonify({'error': f'Failed to reset: {str(e)}'}), 500


@api.route('/state', methods=['GET'])
def get_state():
    return jsonify({
        'path': _state['path'],
        'opened': _state['data'] is not None,
        'changed_count': len(_state['changed_files']),
        'diff_path': _state['diff_path'],
    })
