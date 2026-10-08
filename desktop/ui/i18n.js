'use strict';
// Literal dictionaries, never HTML translation or input/value mutation. Also used
// in the main process to translate app-owned errors without renderer authority.
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.AgujaI18n=factory();})(typeof window==='undefined'?globalThis:window,()=>{
 function language(catalog,value){const code=String(value||'en').replaceAll('_','-').split(/[.-]/)[0].toLowerCase();return code==='es'||Object.hasOwn(catalog.translations,code)?code:'en';}
 const patterns=new WeakMap();
 function templates(catalog){if(patterns.has(catalog))return patterns.get(catalog);const result=[];
  for(const source of Object.keys(catalog.translations.en||{})){if(!/\{\w+\}/.test(source))continue;const names=[];let pattern='',start=0;for(const match of source.matchAll(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g)){pattern+=source.slice(start,match.index).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'([\\s\\S]*?)';names.push(match[1]);start=match.index+match[0].length;}pattern+=source.slice(start).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');result.push({source,names,regex:new RegExp('^'+pattern+'$')});}
  patterns.set(catalog,result);return result;
 }
 function translation(catalog,locale,source){const code=language(catalog,locale);if(code==='es'||typeof source!=='string')return source;const entries=catalog.translations[code]||{};if(Object.hasOwn(entries,source))return entries[source];
  // Match only application-defined, anchored templates. Captured names/paths/
  // model/serial values are copied literally, never recursively translated.
  for(const template of templates(catalog)){const match=template.regex.exec(source);if(!match||!entries[template.source])continue;const values=Object.fromEntries(template.names.map((name,i)=>[name,match[i+1]]));return entries[template.source].replace(/\{(\w+)\}/g,(token,name)=>Object.hasOwn(values,name)?values[name]:token);}
  // Some local validation results combine several fixed warning sentences.
  const sentences=source.split(/(?<=\.) /);if(sentences.length>1&&sentences.every(sentence=>Object.hasOwn(entries,sentence)))return sentences.map(sentence=>entries[sentence]).join(' ');
  return source;
 }
 function create(catalog,locale){let current=language(catalog,locale);const originals=new WeakMap(),attributes=new WeakMap(),textNodes=[],attributeNodes=[];
  const t=(source,values={})=>translation(catalog,current,source).replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g,(placeholder,key)=>Object.hasOwn(values,key)?String(values[key]):placeholder);
  function translateTree(element){
   // Call only on application-created UI: never provider data, transcripts, input
   // values, account names, tunnel labels, paths or secret-bearing status nodes.
   const visit=document.createTreeWalker(element,NodeFilter.SHOW_TEXT);let node;
   while((node=visit.nextNode())){if(['SCRIPT','STYLE','TEXTAREA'].includes(node.parentElement?.tagName))continue;const source=originals.get(node)??node.textContent;if(!originals.has(node)){originals.set(node,source);textNodes.push(node);}const literal=source.trim();if(literal)node.textContent=source.replace(literal,t(literal));}
   for(const target of [element,...element.querySelectorAll('[aria-label],[placeholder],[alt]')])for(const attr of ['aria-label','placeholder','alt'])if(target.hasAttribute?.(attr)){let record=attributes.get(target);if(!record){record={};attributes.set(target,record);attributeNodes.push(target);}record[attr]??=target.getAttribute(attr);target.setAttribute(attr,t(record[attr]));}
  }
  function refresh(){for(const node of textNodes){if(!node.isConnected)continue;const source=originals.get(node),literal=source.trim();if(literal)node.textContent=source.replace(literal,t(literal));}for(const target of attributeNodes){if(!target.isConnected)continue;for(const [attr,source]of Object.entries(attributes.get(target)))target.setAttribute(attr,t(source));}}
  return {t,translateTree,refresh,setLanguage(value){current=language(catalog,value);},get language(){return current;}};
 }
 return {language,translation,create};
});
