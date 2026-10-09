"""Theme-matched, isolated question audio player."""
import json


def player_html(audio_base64, identity):
    source = json.dumps("data:audio/mpeg;base64," + audio_base64)
    token = json.dumps(identity)
    return '''<!doctype html><html><head><style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;color:#e9e9f5}
.player{display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:12px;
background:linear-gradient(120deg,rgba(139,92,246,.16),rgba(6,182,212,.08));border:1px solid rgba(139,92,246,.3)}
button{display:flex;align-items:center;justify-content:center;padding:0;line-height:1;height:34px;width:34px;flex-shrink:0;border:1px solid #8b5cf6;border-radius:50%;
background:#6366f1;color:white;cursor:pointer;font-size:14px;transition:background .15s,transform .15s}
button:hover{background:#8b5cf6;transform:scale(1.05)}button:focus-visible{outline:2px solid #c4b5fd;outline-offset:3px}
button svg{display:block;width:16px;height:16px;fill:currentColor}
.details{flex:1;min-width:0}.label{font-size:11px;color:#fff;margin-bottom:6px}
input{display:block;width:100%;height:4px;margin:0;accent-color:#a78bfa;cursor:pointer}
.time{font-size:11px;color:#a5a5c0;white-space:nowrap;font-variant-numeric:tabular-nums}
</style></head><body><div class="player">
<button id="play" aria-label="Play question" title="Play / pause question"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l12-7z"/></svg></button>
<div class="details"><div class="label" id="label">Question voice</div>
<input id="seek" type="range" min="0" max="100" value="0" aria-label="Question audio position"></div>
<span id="time" class="time">0:00 / 0:00</span></div>
<script>
const identity=TOKEN;
const audio=new Audio(SOURCE);
const button=document.getElementById('play'),seek=document.getElementById('seek');
const label=document.getElementById('label'),time=document.getElementById('time');
function clock(seconds){seconds=Number.isFinite(seconds)?Math.floor(seconds):0;return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0')}
function update(){const playing=!audio.paused;button.innerHTML=playing?'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>':'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l12-7z"/></svg>';button.setAttribute('aria-label',playing?'Pause question':'Play question');
seek.value=audio.duration?audio.currentTime/audio.duration*100:0;time.textContent=clock(audio.currentTime)+' / '+clock(audio.duration)}
button.onclick=()=>{if(audio.paused){if(audio.ended)audio.currentTime=0;audio.play().catch(()=>{label.textContent='Tap play to hear question'})}else audio.pause()};
seek.oninput=()=>{if(Number.isFinite(audio.duration))audio.currentTime=audio.duration*seek.value/100};
['timeupdate','loadedmetadata','play','pause','ended'].forEach(event=>audio.addEventListener(event,update));
audio.addEventListener('error',()=>{label.textContent='Audio unavailable; retry question audio'});
// Each question gets a new iframe/source; teardown also stops audio.
window.addEventListener('pagehide',()=>{audio.pause();audio.src=''});
audio.load();audio.play().catch(()=>{label.textContent='Question voice \u00b7 tap play'});
</script></body></html>'''.replace('TOKEN', token).replace('SOURCE', source)
