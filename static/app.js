const $=s=>document.querySelector(s), el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const api=async(p,b)=>{const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});const j=await r.json();if(!r.ok)throw new Error(j.error||'Request failed');return j};
const TABS=[['summary','📝 Summary'],['questions','❓ Questions'],['mcqs','✅ MCQs'],['chat','💬 Chat']];
TABS.forEach(([id,l],i)=>{const b=el('button','tab'+(i?'':' on'),l);b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));b.classList.add('on');document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));$('#p-'+id).classList.add('on');$('#err').textContent=''};$('#tabs').append(b)});
async function status(){try{const r=await(await fetch('/api/status')).json();$('#dot').className='dot'+(r.ollama?' on':'');$('#st').textContent=r.ollama?'Ollama online':'Ollama offline';
const m=$('#model');m.innerHTML='';(r.models.length?r.models:[r.model]).forEach(n=>{const o=el('option',null,n);o.value=n;if(n===r.model)o.selected=true;m.append(o)});}catch(e){}}
$('#model').onchange=e=>api('/api/model',{model:e.target.value});status();setInterval(status,8000);
const drop=$('#drop');drop.onclick=()=>$('#file').click();
drop.ondragover=e=>{e.preventDefault();drop.classList.add('over')};drop.ondragleave=()=>drop.classList.remove('over');
drop.ondrop=e=>{e.preventDefault();drop.classList.remove('over');up(e.dataTransfer.files[0])};$('#file').onchange=e=>up(e.target.files[0]);
async function up(f){if(!f)return;$('#uerr').textContent='';drop.innerHTML='<span class="spin"></span>Reading &amp; indexing '+f.name.replace(/[<>&]/g,'')+'…';
const fd=new FormData();fd.append('file',f);try{const r=await fetch('/api/upload',{method:'POST',body:fd});const j=await r.json();if(!r.ok)throw new Error(j.error);
drop.innerHTML='<b>✔ '+j.name.replace(/[<>&]/g,'')+'</b><div class="sub">Click to load another PDF</div>';const s=$('#stats');s.innerHTML='';
[['Pages',j.pages],['OCR pages',j.ocr_pages],['Words',j.words],['Chunks',j.chunks],['Embedder',j.embedder]].forEach(([k,v])=>{const d=el('div','stat');d.append(el('b',null,v),k);s.append(d)});
if(j.warning)$('#uerr').textContent=j.warning;['summary','questions','mcqs'].forEach(k=>{$('#o-'+k).className='empty';$('#o-'+k).textContent='Not generated yet.'});$('#log').innerHTML=''}
catch(e){$('#uerr').textContent=e.message;drop.innerHTML='<b>Drop a PDF here or click to browse</b>'}}
function busy(b,on,t){b.disabled=on;if(on){b._t=b.textContent;b.innerHTML='<span class="spin"></span>'+(t||'Working…')}else b.textContent=b._t}
const R={
summary:d=>{const o=$('#o-summary');o.className='';o.innerHTML='';const ul=el('ul');d.summary.split('\n').map(l=>l.replace(/^[-*•\d.\s]+/,'').trim()).filter(Boolean).forEach(l=>ul.append(el('li',null,l)));o.append(ul)},
questions:d=>{const o=$('#o-questions');o.className='';o.innerHTML='';if(!d.questions.length)return o.append('Model returned no questions. Try again.');d.questions.forEach((q,i)=>{const c=el('div','q');c.append(el('div','q-text',(i+1)+'. '+(q.question||q)));if(q.answer){const ans=el('div','q-answer');ans.textContent=q.answer;ans.style.display='none';const toggle=el('button','q-toggle','Show Answer');toggle.onclick=()=>{const showing=ans.style.display!=='none';ans.style.display=showing?'none':'block';toggle.textContent=showing?'Show Answer':'Hide Answer'};c.append(toggle,ans)}o.append(c)})},
mcqs:d=>{const o=$('#o-mcqs');o.className='';o.innerHTML='';if(!d.mcqs.length)return o.append('Model returned no valid MCQs. Try again.');
d.mcqs.forEach((m,i)=>{const c=el('div','mcq');c.append(el('b',null,(i+1)+'. '+m.question));const bs=m.options.map((t,k)=>{const b=el('button','opt',String.fromCharCode(65+k)+') '+t);
b.onclick=()=>{bs.forEach((x,j)=>{x.disabled=true;if(j===m.answer)x.classList.add('ok')});if(k!==m.answer)b.classList.add('bad')};c.append(b);return b});o.append(c)})}};
document.querySelectorAll('[data-run]').forEach(b=>b.onclick=async()=>{const k=b.dataset.run;$('#err').textContent='';busy(b,true,'Local model thinking…');
try{R[k](await api('/api/'+k,{n:+($('#n'+k[0])||{}).value}))}catch(e){$('#err').textContent=e.message}busy(b,false)});
async function send(){const q=$('#qin').value.trim();if(!q)return;$('#qin').value='';$('#err').textContent='';$('#log').append(el('div','msg me',q));
const w=el('div','msg bot','…');$('#log').append(w);$('#log').scrollTop=1e6;
try{const d=await api('/api/chat',{question:q});w.textContent=d.answer;const dt=el('details');dt.append(el('summary',null,'Source passages'));d.sources.forEach(s=>dt.append(el('p',null,s)));w.append(dt)}
catch(e){w.remove();$('#err').textContent=e.message}$('#log').scrollTop=1e6}
$('#send').onclick=send;$('#qin').onkeydown=e=>{if(e.key==='Enter')send()};