"""Construit la version publique (GitHub Pages) du Carnet du Japon, chiffrée par mot de passe.

Usage : CARNET_MDP=<mot de passe> python3 build.py <carnet.html> <dossier_jours_json> <dossier_photos> <sortie>
- carnet.html : la page de l'artifact, seulement le contenu entre <body> et </body>
- dossier_jours_json : un fichier JSON par jour (export ArtifactData de la collection "days")
- dossier_photos : les photos en clair, nommées <id_asset>.jpg (seules celles qui manquent dans
  <sortie>/photos/ sont nécessaires ; les autres sont déjà chiffrées)

Chiffrement : AES-256-GCM, clé = PBKDF2-SHA256(mot de passe en minuscules, sel, 300 000 itérations).
Le sel est fixe (sel.txt) pour que les appareils déjà connectés le restent après chaque mise à jour.
Fichiers publiés : index.html (écran de mot de passe + page chiffrée), sw.js (déchiffre data.json et
les photos à la volée), data.bin, photos/<id>.bin. Aucun texte ni photo n'est publié en clair.
"""
import base64, glob, json, os, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 300_000
src, days_dir, photos_dir, out = sys.argv[1:5]
pwd = os.environ.get('CARNET_MDP', '').strip().lower()
if not pwd:
    sys.exit('Mot de passe manquant : lancer avec CARNET_MDP=<mot de passe>')

sel_path = os.path.join(out, 'sel.txt')
if not os.path.exists(sel_path):
    open(sel_path, 'w').write(base64.b64encode(os.urandom(16)).decode() + '\n')
salt = base64.b64decode(open(sel_path).read().strip())
key = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(pwd.encode())
aes = AESGCM(key)

def enc(data: bytes) -> bytes:
    iv = os.urandom(12)
    return iv + aes.encrypt(iv, data, None)

# ---- page de l'artifact, chiffrée ----
page = open(src, encoding='utf-8').read()
inner = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
         '<meta name="robots" content="noindex,nofollow"><title>Carnet du Japon</title>'
         '<style>:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
         'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>\n'
         + page + '\n</body></html>')
page_b64 = base64.b64encode(enc(inner.encode('utf-8'))).decode()

GATE = r'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><title>Carnet du Japon</title>
<style>
:root{--bg:#f6f1e7;--fg:#2b2622;--mute:#7a6f64;--line:#d9cfbf;--accent:#b8332a;--field:#fffdf8}
@media (prefers-color-scheme:dark){:root{--bg:#1c1917;--fg:#ede6da;--mute:#a39888;--line:#3d3631;--accent:#e0655a;--field:#26221f}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;min-height:100dvh;display:grid;place-items:center;background:var(--bg);color:var(--fg);
 font:17px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;padding:24px 16px}
#gate{width:100%;max-width:340px;text-align:center}
.jp{font-size:44px;line-height:1;color:var(--accent);letter-spacing:.08em;font-family:"Hiragino Mincho ProN","Yu Mincho",serif}
h1{font-size:22px;font-weight:600;margin:14px 0 6px}
p{margin:0 0 22px;color:var(--mute);font-size:15px}
input{width:100%;font:inherit;font-size:22px;text-align:center;padding:14px 12px;border:1.5px solid var(--line);
 border-radius:12px;background:var(--field);color:var(--fg);outline:none}
input:focus{border-color:var(--accent)}
button{width:100%;margin-top:12px;font:inherit;font-weight:600;padding:14px;border:0;border-radius:12px;
 background:var(--accent);color:#fff;cursor:pointer}
button:disabled{opacity:.6}
#err{min-height:1.4em;margin:12px 0 0;color:var(--accent);font-size:15px}
#gate[hidden]{display:none}
</style></head><body>
<form id="gate" hidden autocomplete="off">
 <div class="jp">日本</div>
 <h1>Carnet du Japon</h1>
 <p>Entre le mot de passe une seule fois : cet appareil s'en souviendra.</p>
 <input id="pw" type="text" inputmode="text" autocapitalize="none" autocorrect="off" spellcheck="false"
  autocomplete="off" enterkeyhint="go" placeholder="Mot de passe" aria-label="Mot de passe">
 <button id="go" type="submit">Ouvrir le carnet</button>
 <div id="err" role="alert"></div>
</form>
<script>
(function(){
const SALT="__SALT__", ITER=__ITER__, PAGE="__PAGE__";
const b64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const $=id=>document.getElementById(id);
function db(){ return new Promise((ok,ko)=>{ const r=indexedDB.open('carnet-japon',1);
  r.onupgradeneeded=()=>r.result.createObjectStore('k'); r.onsuccess=()=>ok(r.result); r.onerror=()=>ko(r.error); }); }
async function getKey(){ try{ const d=await db(); return await new Promise(ok=>{ const q=d.transaction('k').objectStore('k').get('key');
  q.onsuccess=()=>ok(q.result||null); q.onerror=()=>ok(null); }); }catch(_){ return null; } }
async function putKey(raw){ const d=await db(); await new Promise((ok,ko)=>{ const t=d.transaction('k','readwrite');
  t.objectStore('k').put(raw,'key'); t.oncomplete=ok; t.onerror=()=>ko(t.error); }); }
async function delKey(){ try{ const d=await db(); d.transaction('k','readwrite').objectStore('k').delete('key'); }catch(_){} }
async function derive(pw){
  const base=await crypto.subtle.importKey('raw',new TextEncoder().encode(pw.trim().toLowerCase()),'PBKDF2',false,['deriveBits']);
  return new Uint8Array(await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',salt:b64(SALT),iterations:ITER},base,256)); }
async function openPage(raw){
  const k=await crypto.subtle.importKey('raw',raw,'AES-GCM',false,['decrypt']);
  const b=b64(PAGE);
  return new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:b.slice(0,12)},k,b.slice(12))); }
async function worker(){
  if(!('serviceWorker' in navigator)) throw new Error('nosw');
  await navigator.serviceWorker.register('sw.js');
  await navigator.serviceWorker.ready;
  if(!navigator.serviceWorker.controller) await new Promise(ok=>{
    navigator.serviceWorker.addEventListener('controllerchange',ok,{once:true}); setTimeout(ok,3000); });
  if(!navigator.serviceWorker.controller) throw new Error('nosw'); }
function show(html){ document.open(); document.write(html); document.close(); }
function ask(msg){ $('gate').hidden=false; $('err').textContent=msg||''; setTimeout(()=>$('pw').focus(),50); }
(async function start(){
  const raw=await getKey();
  if(raw){ try{ const html=await openPage(raw); await worker(); return show(html); }
    catch(e){ if(e.message==='nosw') return ask("Ce navigateur ne peut pas afficher le carnet. Essaie avec Safari ou Chrome à jour."); await delKey(); } }
  ask('');
})();
$('gate').addEventListener('submit',async ev=>{ ev.preventDefault();
  const pw=$('pw').value; if(!pw.trim()) return;
  $('go').disabled=true; $('err').textContent='';
  let raw, html;
  try{ raw=await derive(pw); html=await openPage(raw); }
  catch(_){ $('go').disabled=false; $('err').textContent='Ce n’est pas le bon mot de passe.'; $('pw').select(); return; }
  try{ await putKey(raw); await worker(); show(html); }
  catch(_){ $('go').disabled=false; $('err').textContent="Ce navigateur ne peut pas afficher le carnet. Essaie avec Safari ou Chrome à jour."; }
});
})();
</script></body></html>
'''

SW = r'''/* Déchiffre data.json et les photos du carnet avec la clé gardée sur l'appareil. */
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
let keyP=null;
function getKey(){ if(keyP) return keyP;
  keyP=new Promise((ok,ko)=>{ const r=indexedDB.open('carnet-japon',1);
    r.onupgradeneeded=()=>r.result.createObjectStore('k');
    r.onsuccess=()=>{ const q=r.result.transaction('k').objectStore('k').get('key');
      q.onsuccess=()=>q.result?ok(crypto.subtle.importKey('raw',q.result,'AES-GCM',false,['decrypt'])):ko(new Error('nokey'));
      q.onerror=()=>ko(q.error); };
    r.onerror=()=>ko(r.error); });
  keyP.catch(()=>{ keyP=null; });
  return keyP; }
async function serve(binUrl,type,cache){
  const r=await fetch(binUrl,{cache});
  if(!r.ok) return new Response('',{status:r.status});
  const b=new Uint8Array(await r.arrayBuffer());
  const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:b.slice(0,12)},await getKey(),b.slice(12));
  return new Response(plain,{headers:{'Content-Type':type}}); }
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.origin!==location.origin) return;
  const base=new URL('./',self.registration.scope).pathname;
  if(!u.pathname.startsWith(base)) return;
  const rel=u.pathname.slice(base.length);
  if(rel==='data.json') return e.respondWith(serve(base+'data.bin','application/json','no-store'));
  const m=rel.match(/^photos\/([0-9a-f]+)\.jpg$/);
  if(m) return e.respondWith(serve(base+'photos/'+m[1]+'.bin','image/jpeg','default'));
});
'''

os.makedirs(os.path.join(out, 'photos'), exist_ok=True)
gate = (GATE.replace('__SALT__', base64.b64encode(salt).decode())
            .replace('__ITER__', str(ITER)).replace('__PAGE__', page_b64))
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(gate)
open(os.path.join(out, 'sw.js'), 'w', encoding='utf-8').write(SW)
open(os.path.join(out, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
open(os.path.join(out, '.nojekyll'), 'w').write('')

# ---- jours ----
days, wanted = [], set()
for f in sorted(glob.glob(os.path.join(days_dir, '**', '*.json'), recursive=True)):
    d = json.load(open(f, encoding='utf-8'))
    d = d.get('data', d)  # accepte {data:{...}} ou le document brut
    if not d.get('date'):
        continue
    keep = {k: d.get(k) for k in ('date', 'place', 'placeJp', 'region', 'lat', 'lng', 'title', 'text')}
    keep['photos'] = [{'id': p['id'], 'w': p.get('w'), 'h': p.get('h')} for p in d.get('photos') or []]
    wanted.update(p['id'] for p in keep['photos'])
    days.append(keep)
data = json.dumps({'days': days}, ensure_ascii=False).encode('utf-8')
open(os.path.join(out, 'data.bin'), 'wb').write(enc(data))
plain_data = os.path.join(out, 'data.json')
if os.path.exists(plain_data):
    os.remove(plain_data)

# ---- photos ----
done, missing = 0, []
for pid in sorted(wanted):
    dst = os.path.join(out, 'photos', pid + '.bin')
    hits = [h for h in glob.glob(os.path.join(photos_dir, pid + '.*')) if not h.endswith('.bin')]
    if os.path.exists(dst):  # déjà chiffrée : on ne la réécrit pas
        done += 1
        continue
    if hits:
        open(dst, 'wb').write(enc(open(hits[0], 'rb').read()))
        done += 1
    else:
        missing.append(pid)
for f in glob.glob(os.path.join(out, 'photos', '*.jpg')):  # plus aucune photo en clair
    os.remove(f)
print(f'{len(days)} jours, {done} photos chiffrées, {len(missing)} manquantes')
