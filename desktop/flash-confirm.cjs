'use strict';
function flashConfirmDialog(disk,{backup=false,ready=false,windows=false}={},t=s=>s){
 const identity=[t('Modelo:')+' '+disk.model,t('Capacidad:')+' '+(disk.size/1024**3).toFixed(2)+' GiB',t('Dispositivo:')+' '+disk.device,t('Serie:')+' '+disk.serial].join('\n');
 const notes=[t(ready?'Tu imagen privada está lista.':'Prepararemos tu imagen privada automáticamente.'),t(backup?'Se hará y verificará un respaldo antes de borrar.':'Se borrará el contenido anterior SIN RESPALDO.'),...(windows?[t('Se cerrarán ordenadamente las aplicaciones que usan este USB y se desmontarán sus volúmenes para uso exclusivo.')]:[]),t('Después se verificará la grabación. Ningún disco interno es elegible.')];
 return {type:'warning',title:t('Grabar {model}').replace('{model}',disk.model),message:t('¿Borrar y grabar este USB?'),detail:identity+'\n\n'+notes.join(' '),buttons:[t('Cancelar'),t(backup?'Respaldar y grabar este USB':'Borrar y grabar este USB')],defaultId:0,cancelId:0};
}
module.exports={flashConfirmDialog};
