'use strict';
(()=>{
 const ui=document.body.dataset;
 // Progressive enhancement only. No fetch, storage, telemetry or command execution.
 document.querySelectorAll('.planner-controls,.search-controls,.print-guide').forEach(x=>x.hidden=false);
 const select=document.querySelector('#situation');
 select?.addEventListener('change',()=>{document.querySelectorAll('[data-plan]').forEach(p=>p.hidden=select.value!=='all'&&p.id!==select.value);});
 for(const field of document.querySelectorAll('.checklist')){
  const checks=[...field.querySelectorAll('input[type=checkbox]')],status=field.querySelector('.check-status');
  const update=()=>{status.textContent=checks.filter(x=>x.checked).length+' / '+checks.length+' · '+ui.checkProgress;};
  field.addEventListener('change',update);update();
 }
 for(const pre of document.querySelectorAll('pre')){
  const code=pre.querySelector('code');if(!code)continue;
  const button=document.createElement('button');button.type='button';button.textContent=ui.copy;button.className='copy-text';
  const status=document.createElement('span');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  button.addEventListener('click',async()=>{try{if(!navigator.clipboard?.writeText)throw Error();await navigator.clipboard.writeText(code.textContent);status.textContent=' '+ui.copied;}catch{const range=document.createRange();range.selectNodeContents(code);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);status.textContent=' '+ui.copyFallback;}});
  pre.append(button,status);
 }
 const input=document.querySelector('#doc-search'),links=[...document.querySelectorAll('[data-doc-link]')];
 const normalize=x=>x.normalize('NFD').replace(/[̀-ͯ]/g,'').toLocaleLowerCase(document.documentElement.lang);
 function search(){const terms=normalize(input.value.trim()).split(/\s+/).filter(Boolean);let count=0;for(const a of links){const section=document.getElementById(a.hash.slice(1));const match=terms.every(t=>normalize(section.textContent).includes(t));a.hidden=!match;section.classList.toggle('search-match',terms.length>0&&match);if(match)count++;}document.querySelector('#search-status').textContent=count?count+' '+ui.searchMatches:ui.noMatches;}
 input?.addEventListener('input',search);input?.addEventListener('keydown',e=>{if(e.key==='Escape'){input.value='';search();}if(e.key==='Enter'){const a=links.find(a=>!a.hidden);if(a)a.click();}});
 for(const a of links)a.addEventListener('click',()=>{const h=document.getElementById(a.hash.slice(1))?.querySelector('h2');if(h){h.tabIndex=-1;h.focus({preventScroll:true});}});
 for(const a of document.querySelectorAll('.language-nav a'))a.addEventListener('click',()=>{if(location.hash)a.hash=location.hash;});
 if(document.querySelector('.zoom-image')&&typeof HTMLDialogElement!=='undefined'){
  const dialog=document.createElement('dialog');dialog.setAttribute('aria-label',ui.zoom);
  const close=document.createElement('button');close.type='button';close.textContent=ui.close;
  const image=document.createElement('img'),caption=document.createElement('p');caption.id='zoom-caption';dialog.setAttribute('aria-describedby',caption.id);dialog.append(close,caption);document.body.append(dialog);let opener;
  close.addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>opener?.focus());
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
  for(const a of document.querySelectorAll('.zoom-image'))a.addEventListener('click',e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();opener=a;image.src=a.href;dialog.insertBefore(image,caption);image.alt=a.querySelector('img').alt;caption.textContent=a.closest('figure').querySelector('figcaption').textContent;dialog.showModal();close.focus();});
 }
 document.querySelector('.print-guide')?.addEventListener('click',()=>print());
 let printed=[];addEventListener('beforeprint',()=>{printed=[...document.querySelectorAll('details')].map(node=>({node,open:node.open}));for(const x of printed)x.node.open=true;});addEventListener('afterprint',()=>{for(const x of printed)x.node.open=x.open;printed=[];});
})();
