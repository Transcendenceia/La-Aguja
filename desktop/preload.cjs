'use strict';
const {contextBridge,ipcRenderer}=require('electron');
const invoke=(channel)=>(...args)=>ipcRenderer.invoke(channel,...args);
contextBridge.exposeInMainWorld('aguja',Object.freeze({
 info:invoke('info'),i18nCatalog:invoke('i18n-catalog'),i18nLanguage:invoke('i18n-language'),catalog:invoke('catalog'),download:invoke('download'),importImage:invoke('import-image'),
 generatePassword:invoke('generate-password'),importWifi:invoke('import-wifi'),importLocale:invoke('import-locale'),providerStatus:invoke('provider-status'),providerInstall:invoke('provider-install'),providerDocs:invoke('provider-docs'),providerLogin:invoke('provider-login'),
 importProvider:invoke('import-provider'),prepare:invoke('prepare'),invalidatePrepared:invoke('invalidate-prepared'),exportProfile:invoke('export-profile'),importProfile:invoke('import-profile'),
 disks:invoke('disks'),flash:invoke('flash'),
 bitlockerStatus:invoke('bitlocker-status'),bitlockerSuspend:invoke('bitlocker-suspend'),bitlockerResume:invoke('bitlocker-resume'),bitlockerKey:invoke('bitlocker-key'),bitlockerExportText:invoke('bitlocker-export-text'),
 onProgress:(callback)=>{const listener=(_,value)=>callback(value);ipcRenderer.on('progress',listener);return()=>ipcRenderer.removeListener('progress',listener);}
}));
