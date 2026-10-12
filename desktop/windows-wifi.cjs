'use strict';
const fs=require('node:fs'),path=require('node:path');
const {runPowerShell}=require('./windows-privileged.cjs');
const {validateCapsule}=require('./core.cjs');
const SCRIPT=fs.readFileSync(path.join(__dirname,'windows-wifi.ps1'),'utf8');
const errors={
 'no-network':'No se detectó ninguna red Wi-Fi activa.',
 'key-unavailable':'No se pudo leer la contraseña Wi-Fi. Autoriza los permisos de Windows o escribe la red manualmente.',
 'unavailable':'No se pudo importar la red Wi-Fi activa. Comprueba los permisos de Windows; las redes empresariales no se importan automáticamente.'
};
async function importActiveWifi({platform=process.platform,query=runPowerShell}={}){
 if(platform!=='win32')throw Error('La importación Wi-Fi de Windows solo está disponible en Windows.');
 let result;
 try{result=JSON.parse(await query(SCRIPT,{elevated:true,operation:'wifi'}));}catch{throw Error(errors.unavailable);}
 if(result?.canceled)throw Error('No se autorizó la importación Wi-Fi. Acepta el diálogo de permisos de Windows o vuelve a intentarlo.');
 if(result?.ok!==true)throw Error(errors[result?.code]||errors.unavailable);
 try{
  // Project a validated network only; never forward native exceptions/XML.
  const w=result.wifi;
  const wifi={ssid:w.ssid,password:w.password,security:w.security,country:w.country,hidden:w.hidden};
  validateCapsule({schema:1,hostname:'aguja',network:{wifi,ethernet:{method:'auto'}},providers:{},ssh:{port:22,password:'aguja',public_key:''}});
  return {wifi};
 }catch{throw Error(errors.unavailable);}
}
module.exports={importActiveWifi};
