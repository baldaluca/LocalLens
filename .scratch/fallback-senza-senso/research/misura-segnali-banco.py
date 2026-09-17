import json, re, zlib
from collections import Counter
import sys
sys.path.insert(0, 'src')
from locallens.core.pipeline import _motivo_anomalia

STOP_IT = {'di','e','che','la','il','lo','i','gli','le','un','uno','una','in','con',
           'su','per','tra','fra','non','si','come','anche','dal','dei','delle',
           'alla','questo','questa','sono','molto','tutto','quando','sempre'}
STOP_EN = {'the','and','of','to','in','is','that','for','with','as','on','are',
           'was','were','be','by','from','this','have','has','not','but','they',
           'their','you','your','can','will','would','all','more','than'}
FORTI = ['in sintesi', 'in conclusione', 'riassunto', 'il documento tratta di',
         'the document shows', 'as an ai', 'as a language model', "i can't",
         'mi dispiace', 'non riesco a leggere', 'ecco la trascrizione']
DEBOLI = ['il documento', 'mostra', 'conclusione']
CHIUSURA = set('.:;!?"»)\'’”')


def segnali(t):
    n = len(t)
    out = {}
    out['zlib'] = round(len(zlib.compress(t.encode())) / n, 3) if n >= 200 else None
    parole = re.findall(r'[a-zà-ÿ]+', t.lower())
    np_ = len(parole)
    out['nparole'] = np_
    out['top1'] = round(Counter(parole).most_common(1)[0][1] / np_, 3) if np_ >= 50 and parole else None
    tri = [' '.join(parole[i:i + 3]) for i in range(len(parole) - 2)]
    out['ttr3'] = round(len(set(tri)) / len(tri), 3) if len(tri) >= 100 else None
    qit = sum(1 for w in parole if w in STOP_IT) / max(np_, 1)
    qen = sum(1 for w in parole if w in STOP_EN) / max(np_, 1)
    out['lingua'] = round(qen - qit, 3) if np_ >= 30 else None
    low = t.lower()
    out['forte'] = next((m for m in FORTI if m in low), None)
    out['deboli'] = [m for m in DEBOLI if m in low]
    s = t.strip()
    out['monco'] = bool(s) and (s[-1] not in CHIUSURA)
    return out


recs = [json.loads(line) for line in
        open('.scratch/fallback-senza-senso/banco/pagine.jsonl', encoding='utf-8')]
for r in recs:
    t = r['testo']
    base = _motivo_anomalia(t)
    s = segnali(t)
    flag = 'OK' if base is None else ('FLAG:' + base)
    print(r['id'], '| etichetta=' + str(r['etichetta']), '| BASE=' + flag)
    print('   zlib=' + str(s['zlib']), 'top1=' + str(s['top1']),
          'ttr3=' + str(s['ttr3']), 'lingua=' + str(s['lingua']),
          'forte=' + str(s['forte']), 'deboli=' + str(s['deboli']),
          'monco=' + str(s['monco']))
