/* Déchiffre data.json et les photos du carnet avec la clé gardée sur l'appareil. */
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
