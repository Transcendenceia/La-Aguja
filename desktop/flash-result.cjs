'use strict';
// Consume only the public IPC receipt, never raw writer output or profile data.
function flashResultDialog(result, t = value => value) {
 if (result?.canceled) return null;
 const verified = result?.ok === true && result.verified === true;
 const detail = verified
  ? [t('La grabación y la lectura de comprobación terminaron correctamente.'),
     result.backupVerified === true ? t('El respaldo anterior quedó guardado y verificado.') : '',
     t('Expulsa el USB desde tu sistema antes de desconectarlo.')].filter(Boolean).join('\n\n')
  : [result?.error || t('La grabación no devolvió una lectura verificada.'),
     t('El USB no está listo. No lo uses para arrancar hasta completar una nueva grabación verificada.')].join('\n\n');
 return {type: verified ? 'info' : 'error',
  title: t(verified ? 'USB listo' : 'No se pudo completar la grabación'),
  message: t(verified ? 'Tu pendrive está listo.' : 'No se ha completado la preparación del USB.'),
  detail, buttons: [t('Aceptar')], defaultId: 0, cancelId: 0, noLink: true};
}
module.exports = {flashResultDialog};
