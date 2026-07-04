from flask import Flask, request, jsonify, render_template
import time, base64, hashlib, hmac, requests, re
import syncedlyrics

app = Flask(__name__)

ACRCLOUD_HOST   = "identify-us-west-2.acrcloud.com"
ACRCLOUD_KEY    = "9d2783df08089136cbdd79de1db53d44"
ACRCLOUD_SECRET = "McldJ8GLQiDuktmkqJC6SM3dAHauextPePAU8dqF"

def sign(secret, message):
    return base64.b64encode(
        hmac.new(secret.encode('ascii'), message.encode('ascii'), hashlib.sha1).digest()
    ).decode('ascii')

def recognize(audio_bytes):
    timestamp = str(int(time.time()))
    string_to_sign = "\n".join([
        "POST", "/v1/identify", ACRCLOUD_KEY, "audio", "1", timestamp
    ])
    try:
        r = requests.post(
            f"https://{ACRCLOUD_HOST}/v1/identify",
            files={'sample': ('audio.wav', audio_bytes, 'audio/wav')},
            data={
                'access_key':        ACRCLOUD_KEY,
                'data_type':         'audio',
                'signature_version': '1',
                'signature':         sign(ACRCLOUD_SECRET, string_to_sign),
                'sample_bytes':      str(len(audio_bytes)),
                'timestamp':         timestamp
            },
            timeout=15
        )
        result = r.json()
        if result.get('status', {}).get('code') == 0:
            music = result['metadata']['music'][0]
            return {
                'title':  music.get('title', ''),
                'artist': music.get('artists', [{}])[0].get('name', ''),
                'album':  music.get('album', {}).get('name', '')
            }
    except Exception:
        pass
    return None

def fetch_lyrics(title, artist):
    try:
        lyrics = syncedlyrics.search(f"{title} {artist}")
        if not lyrics:
            lyrics = syncedlyrics.search(title)
        if lyrics:
            clean = re.sub(r'|$$\d+:\d+\.\d+$$|', '', lyrics)
            clean = '\n'.join(line.strip() for line in clean.splitlines() if line.strip())
            return clean
        return 'Letra não encontrada. Busque manualmente no Holyrics.'
    except Exception as e:
        return f'Erro ao buscar letra: {str(e)}'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/identify', methods=['POST'])
def identify():
    audio_bytes = request.data
    if not audio_bytes:
        return jsonify({'error': 'Nenhum áudio recebido'}), 400

    result = recognize(audio_bytes)
    if not result:
        return jsonify({'error': 'Música não identificada'}), 404

    result['lyrics'] = fetch_lyrics(result['title'], result['artist'])
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)