#!/usr/bin/env python3
import os, json, re, unicodedata
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote

MUSIC_DIR = os.path.join(os.path.dirname(__file__), 'music')

def n(s):
    """Normalize to NFC for consistent Korean string comparison on macOS."""
    return unicodedata.normalize('NFC', s)

FOLDER_RULES = [
    ('Aimyon',       lambda f: re.match(r'Aimyon\d*\s', n(f))),
    ('J Rabbit',     lambda f: n(f).startswith('J Rabbit') or n(f).startswith('[슬의OST')),
    ('잔나비',        lambda f: n(f).startswith('잔나비')),
    ('박효신',        lambda f: n(f).startswith('박효신')),
    ('성시경',        lambda f: n(f).startswith('성시경')),
    ('Hyeli Park',   lambda f: n(f).startswith('Hyeli Park')),
    ('OOHYO',        lambda f: n(f).startswith('OOHYO')),
    ('Lisa lovbrand',lambda f: n(f).startswith('Lisa lovbrand')),
    ('Tender',       lambda f: n(f).startswith('Tender')),
    ('내생에 봄날',   lambda f: n(f).startswith('내생에 봄날')),
    ('연애시대',      lambda f: n(f).startswith('연애시대')),
    ('신해철',        lambda f: n(f).startswith('신해철')),
    ('시와 (소요)',   lambda f: n(f).startswith('시와')),
    ('이문세',        lambda f: n(f).startswith('이문세')),
    ('심규선',        lambda f: n(f).startswith('심규선')),
    ('[DJ티비씨]',    lambda f: n(f).startswith('[DJ티비씨]')),
    ('이해리 (다비치)', lambda f: n(f).startswith('이해리') or n(f).startswith('다비치')),
    ('Siwa',         lambda f: f.startswith('Siwa')),
    ('Dave Brubeck', lambda f: f.startswith('Dave Brubeck')),
    ('Dua Lipa',     lambda f: f.startswith('Dua Lipa')),
    ('Ed Sheeran',   lambda f: f.startswith('Ed Sheeran')),
    ('Ariana Grande',lambda f: f.startswith('Ariana Grande')),
    ('Maroon 5',     lambda f: f.startswith('Maroon 5')),
    ('Lukas Graham', lambda f: f.startswith('Lukas Graham')),
    ('Adele',        lambda f: f.startswith('Adele')),
    ('Zara Larsson', lambda f: f.startswith('Zara Larsson')),
    ('Taylor Swift', lambda f: f.startswith('Taylor Swift')),
    ('Lenka',        lambda f: f.startswith('Lenka')),
    ('John Legend',  lambda f: f.startswith('John Legend')),
    ('La La Land',   lambda f: any(k in n(f) for k in ['La La Land','City of Stars','Mia &','Audition','Another Day of Sun','Someone in the Crowd','Start a Fire','Epilogue','A Lovely Night'])),
    ('[B] Beatles',  lambda f: n(f).startswith('[B]')),
    ('Jazz',         lambda f: any(n(f).startswith(a) for a in [
        'Miles Davis','John Coltrane','Charlie Parker','Charlie \'Bird\'','Bill Evans',
        'Keith Jarrett','Cannonball Adderley','Coleman Hawkins','Dizzy Gillespie',
        'Duke Ellington','Ella Fitzgerald','Louis Armstrong','Fats Waller','Artie Shaw',
        'Blossom Dearie','Sarah Vaughan','Nina Simone','Norah Jones','Stan Getz',
        'Lee Morgan','Thelonious Monk','Sonny Rollins','Sonny Clark','Ramsey Lewis',
        'Ahmad Jamal','Erroll Garner','Clifford Brown','Vince Guaraldi','Peggy Lee',
        'Glenn Miller','Frank Sinatra','Don Shirley',
    ]) or any(k in n(f) for k in [
        'Blue Monk','Blue Train','Autumn Leaves','Somethin\' Else','Mercy, Mercy',
        'Moanin\'','Cool Struttin\'','Joy Spring','Manteca','Concierto de Aranjuez',
        'My Favorite Things','Idle Moments','Poinciana','Sidewinder','Take Five',
        'Blue Rondo','Strange Meadowlark','Waltz for Debby','My Song 1978',
        'Moonlight in Vermont','Potato head','St. Louis Blues','Body and Soul',
        'It Don\'t Mean','In The Mood','Yardbird','Ko Ko','April in Paris',
        'Fly Me To The Moon','Georgia on My Mind','Someday My Prince',
        'Just In Time','Just One Of Those','But Not For Me','Blue Moon',
        'Blue Orchids','Straighten Up','Struttin\'','One O\'Clock Jump',
        'Compared to What','Confirmation','Song For My Father','Lover man',
        'My Old Flame','Cast Your Fate','Flight to Denmark','Quizas',
        'O Grande Amor','Para Machuchar','Herman\'s Habit','Eddie Harris',
        'Gilles Blandin','Killing me softly','Midnight Blue',
    ])),
]

FOLDER_ICONS = {
    'Aimyon': '🎵', 'J Rabbit': '🐰', '잔나비': '🌙', '박효신': '🌿', '성시경': '💫',
    'Hyeli Park': '🌊', 'OOHYO': '🌸', 'Lisa lovbrand': '🎀', 'Tender': '🌹',
    '내생에 봄날': '🌼', '연애시대': '💌', '신해철': '⚡', '시와 (소요)': '🍃',
    '이문세': '🌛', '심규선': '✨', '[DJ티비씨]': '📺',
    '이해리 (다비치)': '🌷', 'Siwa': '🌱',
    'Dave Brubeck': '🎹', 'Dua Lipa': '💃', 'Ed Sheeran': '🎸',
    'Ariana Grande': '🎤', 'Maroon 5': '🎶', 'Lukas Graham': '🏡',
    'Adele': '🎙️', 'Zara Larsson': '⭐', 'Taylor Swift': '💖',
    'Lenka': '🎈', 'John Legend': '🎼',
    'La La Land': '🌆', '[B] Beatles': '🍎', 'Jazz': '🎷', '기타': '📂',
}

def get_playlist():
    files = sorted(os.listdir(MUSIC_DIR))
    audio_ext = {'.mp3', '.m4a', '.wav', '.ogg', '.flac', '.wmv'}
    files = [f for f in files if os.path.splitext(f)[1].lower() in audio_ext]

    folders = {name: [] for name, _ in FOLDER_RULES}
    folders['기타'] = []

    for f in files:
        matched = False
        for name, rule in FOLDER_RULES:
            if rule(f):
                folders[name].append(f)
                matched = True
                break
        if not matched:
            folders['기타'].append(f)

    result = []
    for name, _ in FOLDER_RULES:
        if folders[name]:
            result.append({
                'folder': name,
                'icon': FOLDER_ICONS.get(name, '🎵'),
                'songs': folders[name],
            })
    if folders['기타']:
        result.append({
            'folder': '기타',
            'icon': FOLDER_ICONS.get('기타', '🎼'),
            'songs': folders['기타'],
        })
    return result


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = unquote(self.path)
        if path == '/api/playlist':
            data = json.dumps(get_playlist(), ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()

    def log_message(self, fmt, *args):
        pass  # suppress access logs


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port = 8765
    print(f'Feelgram Music  →  http://localhost:{port}')
    HTTPServer(('', port), Handler).serve_forever()
