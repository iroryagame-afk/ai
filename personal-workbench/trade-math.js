(function(root){
'use strict';
function targetReturn(entry,target,bps=0){if(!Number.isFinite(entry)||entry<=0||!Number.isFinite(target)||target<=0||!Number.isFinite(bps)||bps<0||bps>=10000)return null;return (target*(1-bps/10000)/(entry*(1+bps/10000))-1)*100}
function signalDay(timestamp,timezone){if(!timestamp)return null;const d=new Date(timestamp);return Number.isNaN(d.getTime())?null:new Intl.DateTimeFormat('sv-SE',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).format(d)}
const api={targetReturn,signalDay};if(typeof module==='object'&&module.exports)module.exports=api;else root.TradeMath=api;
})(typeof window==='object'?window:globalThis);
