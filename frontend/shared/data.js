// Replace this adapter with fetch('/api/v1/...') when the Python service is ready.
const workers=[
 {id:1048,job:'Timmerman',region:'Utrecht',years:12,rate:38,radius:60,rating:'4.9',available:'Direct beschikbaar',cert:['VCA VOL','Hoogwerker'],icon:'⌂'},
 {id:1052,job:'Elektricien',region:'Rotterdam',years:8,rate:42,radius:80,rating:'4.8',available:'Vanaf 19 oktober',cert:['VCA','NEN 3140'],icon:'ϟ'},
 {id:1063,job:'Schilder',region:'Amsterdam',years:10,rate:34,radius:50,rating:'4.9',available:'Direct beschikbaar',cert:['VCA'],icon:'▥'},
 {id:1071,job:'Lasser',region:'Eindhoven',years:15,rate:45,radius:100,rating:'4.7',available:'Direct beschikbaar',cert:['VCA','EN ISO 9606'],icon:'⚒'},
 {id:1084,job:'Tegelzetter',region:'Den Haag',years:7,rate:36,radius:70,rating:'4.8',available:'Vanaf 26 oktober',cert:['VCA'],icon:'▦'},
 {id:1090,job:'Loodgieter',region:'Utrecht',years:9,rate:40,radius:60,rating:'4.9',available:'Direct beschikbaar',cert:['VCA'],icon:'◉'}];
const requests=[{id:'A-2041',worker:1048,project:'Renovatie Parkzicht',job:'Timmerman',date:'12-10-2026',status:'In behandeling'},{id:'A-2038',worker:1052,project:'Nieuwbouw West',job:'Elektricien',date:'19-10-2026',status:'Bevestigd'},{id:'A-2027',worker:1063,project:'Kantoor Centrum',job:'Schilder',date:'05-10-2026',status:'Afgerond'}];
// Illustrative catalog coverage; totals and filters share the same dataset.
for(const [job,total,rate] of [['Schilder',8,34],['Elektricien',6,42],['Lasser',4,45],['Timmerman',9,38],['Tegelzetter',5,36],['Loodgieter',4,40],['Grondwerker',3,33],['Kabelmonteur',3,39],['Betonwerker',4,37],['Allround vakman',2,35]]){
 const existing=workers.filter(w=>w.job===job).length;
 for(let i=existing;i<total;i++)workers.push({id:1100+workers.length,job,region:['Utrecht','Rotterdam','Amsterdam','Eindhoven','Den Haag'][i%5],years:5+i,rate:rate+i%3,radius:50+(i%4)*10,rating:['4.7','4.8','4.9'][i%3],available:i%3===0?'Vanaf 19 oktober':'Direct beschikbaar',cert:job==='Elektricien'?['VCA','NEN 3140']:['VCA']});
}
workers.forEach((worker,index)=>{
 worker.providerType=index%4===1?'company':'individual';
 worker.avatar=worker.providerType==='company'?`company-${['a','b','c'][Math.floor(index/4)%3]}.svg`:`portrait-${index%2===0?'a':'b'}.png`;
});
export const api={async workers(){return structuredClone(workers)},async requests(){return structuredClone(requests)}};
export const jobs=['Schilder','Elektricien','Lasser','Timmerman','Tegelzetter','Loodgieter','Grondwerker','Kabelmonteur','Betonwerker','Allround vakman'];
