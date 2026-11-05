
(function(){
var box=document.getElementById('q'),out=document.getElementById('qr');if(!box)return;var sel=0,hits=[];
var empty=false;
function norm(s){return s.toLowerCase().replace(/ё/g,'е').replace(/[\s\-]+/g,' ')}
function rank(e,q,ws){var t=norm(e[0]),x=t+' '+norm(e[3]||'');
for(var i=0;i<ws.length;i++)if(x.indexOf(ws[i])<0)return -1;
return t===q?0:t.indexOf(q+' ')===0?1:t.indexOf(q)===0?2:(' '+t).indexOf(' '+q)>=0?3:t.indexOf(q)>=0?4:5}
function draw(){out.innerHTML='';hits.forEach(function(h,i){var a=document.createElement('a');a.href=h[2];
if(i===sel)a.className='sel';var s=document.createElement('span');s.textContent=h[0];var m=document.createElement('small');
m.textContent=h[1];a.appendChild(s);a.appendChild(m);a.addEventListener('mouseenter',function(){sel=i;out.querySelectorAll('a').forEach(function(o,j){o.classList.toggle('sel',j===i)})});
out.appendChild(a);if(i===sel)a.scrollIntoView({block:'nearest'})});
if(empty){var n=document.createElement('div');n.className='empty';n.textContent='Ничего не найдено';out.appendChild(n)}
out.hidden=!hits.length&&!empty}
function close(){hits=[];empty=false;draw()}
box.addEventListener('input',function(){var q=norm(box.value.trim()),ws=q.split(' ');sel=0;
hits=q?WIKI_INDEX.map(function(e){return[rank(e,q,ws),e]}).filter(function(p){return p[0]>=0})
.sort(function(a,b){return a[0]-b[0]||a[1][0].length-b[1][0].length}).slice(0,14).map(function(p){return p[1]}):[];
empty=!!q&&!hits.length;draw()});
box.addEventListener('focus',function(){if(box.value.trim())box.dispatchEvent(new Event('input'))});
box.addEventListener('keydown',function(e){if(e.key==='Escape'){if(hits.length||empty)close();else{box.value='';box.blur()}return}
if(!hits.length)return;if(e.key==='ArrowDown'){sel=Math.min(sel+1,hits.length-1);draw();e.preventDefault()}
else if(e.key==='ArrowUp'){sel=Math.max(sel-1,0);draw();e.preventDefault()}else if(e.key==='Enter'){location.href=hits[sel][2]}});
document.addEventListener('click',function(e){if(!e.target.closest('.search'))close()});
document.addEventListener('keydown',function(e){if(e.key==='/'&&document.activeElement!==box&&!/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)){box.focus();e.preventDefault()}});
document.querySelectorAll('[data-filter]').forEach(function(f){var rows=document.querySelectorAll(f.dataset.filter);
f.addEventListener('input',function(){var q=norm(f.value);rows.forEach(function(r){r.dataset.th=q&&norm(r.textContent).indexOf(q)<0?'1':'';r.hidden=!!(r.dataset.th||r.dataset.gh)})})});
document.querySelectorAll('.tagbar:not(.sortbar)').forEach(function(bar){var rows=document.querySelectorAll(bar.dataset.target+' tbody tr');bar.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){bar.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});var tag=b.dataset.tag;rows.forEach(function(r){r.dataset.gh=tag&&(' '+r.dataset.tags+' ').indexOf(' '+tag+' ')<0?'1':'';r.hidden=!!(r.dataset.th||r.dataset.gh)})})})});
function hcalc(c){var reqs=JSON.parse(c.dataset.reqs),cash=JSON.parse(c.dataset.cash),map=+c.querySelector('select').value,
pin=c.querySelector('.hc-round'),st=Math.max(0,+c.querySelector('.hc-start').value||0),m=curMult(),
K=c.querySelector('.hc-mk').checked?JSON.parse(c.dataset.mk):{xp:0,levels:0,discount:0},base=c.dataset.cost*(1-K.discount),
cost=Math.round(base*m/5)*5,have=st,ok=1;
while(have<cost&&ok<=cash.length){have+=cash[ok-1];ok++}if(!c._touched)pin.value=Math.min(ok,140);
var XR=JSON.parse(c.dataset.xp),n=XR.length,gx=function(r){return r<=n?XR[r-1]:XR[n-1]+(XR[n-1]-XR[n-2])*(r-n)},
start=Math.max(1,Math.min(140,+pin.value||1)),xp=K.levels?reqs[K.levels-1]:0,r=start-1,rs=[];
reqs.forEach(function(q){while(xp<q&&r<500){r++;xp+=Math.round(gx(r)*map*(1+K.xp))}rs.push(Math.max(r,start))});
var W=640,H=230,P=30,L=36,R=12,X=function(v){return (L+(W-L-R)*(v-1)/139).toFixed(1)},Y=function(l){return (H-P-(H-2*P)*(l-1)/19).toFixed(1)},
s='',pts=[X(start)+','+Y(1)],lv=1;
[5,10,15,20].forEach(function(l){s+='<line class="pgrid" x1="'+L+'" y1="'+Y(l)+'" x2="'+(W-R)+'" y2="'+Y(l)+'"/>'});
[1,5,10,15,20].forEach(function(l){s+='<text x="'+(L-6)+'" y="'+(+Y(l)+4)+'" text-anchor="end">'+l+'</text>'});
[1,20,40,60,80,100,120,140].forEach(function(v){s+='<text x="'+X(v)+'" y="'+(H-P+16)+'" text-anchor="middle">'+v+'</text>'});
s+='<line class="paxis" x1="'+L+'" y1="'+(H-P)+'" x2="'+(W-R)+'" y2="'+(H-P)+'"/>';
if(ok>start)s+='<rect class="pna" x="'+X(start)+'" y="'+P+'" width="'+(X(Math.min(ok,140))-X(start))+'" height="'+(H-2*P)+'"><title>денег ещё не хватает</title></rect>';
var dots='';rs.forEach(function(v,i){if(v>140)return;pts.push(X(v)+','+Y(lv));lv=i+2;pts.push(X(v)+','+Y(lv));
dots+='<circle class="pdot" cx="'+X(v)+'" cy="'+Y(lv)+'" r="3.5"><title>ур. '+lv+': раунд '+v+'</title></circle>'});
pts.push(X(140)+','+Y(lv));s+='<polyline class="pline" points="'+pts.join(' ')+'"/>'+dots;
for(var v=start,k=0;v<=140;v++){while(k<rs.length&&rs[k]<=v)k++;
s+='<rect class="phit" x="'+(X(v)-2)+'" y="'+P+'" width="4" height="'+(H-2*P)+'"><title>раунд '+v+': ур. '+(k+1)+'</title></rect>'}
var last=rs[rs.length-1];c.querySelector('.hcalc-out').innerHTML='<div class="wrap"><svg class="pchart" viewBox="0 0 '+W+' '+H+'" width="'+W+'" role="img" aria-label="Уровень героя по раундам">'+s+'</svg></div>'
+(last>140?'<p class="note">Ур. 20 на раунде '+last+'.</p>':'');
c.querySelector('.hcalc-cash').textContent=ok>cash.length?'Денег не хватит до 140 раунда.':
(start<ok?'Денег хватит только к началу раунда ':'Денег хватит к началу раунда ')+ok+' ($'+cost+', старт $'+st+', без других трат).'
+(start<ok?' Раньше можно на кастомной карте: укажите её стартовые деньги.':'')}
document.querySelectorAll('.hcalc').forEach(function(c){var go=function(){hcalc(c)};c.querySelector('select').addEventListener('change',go);
c.querySelector('.hc-start').addEventListener('input',go);c.querySelector('.hc-mk').addEventListener('change',go);
c.querySelector('.hc-round').addEventListener('input',function(){c._touched=true;go()});go()});
document.querySelectorAll('.sortbar').forEach(function(bar){var g=document.getElementById(bar.dataset.grid);bar.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){var k=b.dataset.sort;Array.prototype.slice.call(g.children).sort(function(x,y){return x.dataset[k]-y.dataset[k]}).forEach(function(c){g.appendChild(c)});g.classList.toggle('cols3',k==='order');bar.querySelectorAll('button').forEach(function(o){o.classList.toggle('on',o===b)})})})});
document.querySelectorAll('table').forEach(function(t){var tb=t.tBodies[0];if(!tb||!t.tHead||t.classList.contains('nosort')||tb.rows.length<3||t.querySelector('[rowspan]'))return;var ths=t.tHead.rows[0].cells;
Array.prototype.forEach.call(ths,function(th,ci){th.classList.add('sortable');th.tabIndex=0;var go=function(){var dir=th.dataset.dir==='1'?-1:1;Array.prototype.forEach.call(ths,function(x){delete x.dataset.dir;x.removeAttribute('aria-sort')});th.dataset.dir=dir===1?'1':'-1';th.setAttribute('aria-sort',dir===1?'ascending':'descending');
var val=function(r){var s=r.cells[ci]?r.cells[ci].textContent.trim():'';if(s===''||s==='–')return null;var n=parseFloat(s.replace(/[\s$×x%]/g,'').replace('−','-').replace(',','.'));return isNaN(n)?s:n};
Array.prototype.slice.call(tb.rows).sort(function(a,b){var x=val(a),y=val(b);if(x===null||y===null)return(x===null)-(y===null);return(typeof x==='number'&&typeof y==='number'?x-y:String(x).localeCompare(String(y)))*dir}).forEach(function(r){tb.appendChild(r)})};
th.addEventListener('click',go);th.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}})})});
document.querySelectorAll('.kgraph').forEach(function(g){var nodes={};g.querySelectorAll('.kn').forEach(function(n){nodes[n.dataset.id]=n});
function chain(id,acc){if(acc[id]||!nodes[id])return acc;acc[id]=1;(nodes[id].dataset.req||'').split(' ').filter(Boolean).forEach(function(p){chain(p,acc)});return acc}
function clear(){g.classList.remove('dim');g.querySelectorAll('.lit').forEach(function(e){e.classList.remove('lit')})}
function light(id){clear();var on=chain(id,{});g.classList.add('dim');Object.keys(on).forEach(function(k){nodes[k].classList.add('lit')});
g.querySelectorAll('.edge').forEach(function(e){if(on[e.dataset.from]&&on[e.dataset.to])e.classList.add('lit')})}
Object.keys(nodes).forEach(function(id){var n=nodes[id];n.addEventListener('mouseenter',function(){light(id)});
n.addEventListener('focus',function(){light(id)});n.addEventListener('mouseleave',clear);n.addEventListener('blur',clear)});var tip=g.querySelector('.ktip');if(tip)Object.keys(nodes).forEach(function(id){var n=nodes[id];n.addEventListener('mouseenter',function(){var b=n.getBoundingClientRect();tip.innerHTML='';var t=document.createElement('b');t.textContent=n.dataset.name;var c=document.createElement('small');c.textContent=n.dataset.cost+' MM';tip.appendChild(t);if(n.dataset.desc){var p=document.createElement('p');p.textContent=n.dataset.desc;tip.appendChild(p)}tip.appendChild(c);if(+n.dataset.ancPts>0||parseInt(n.dataset.ancMm)>0){var ch=document.createElement('small');ch.className='kchain';ch.textContent='Всего в ветке: '+n.dataset.ancPts+' знаний, '+n.dataset.ancMm+' MM';tip.appendChild(ch)}tip.hidden=false;var top=b.top-tip.offsetHeight-6;if(top<70)top=b.bottom+6;tip.style.left=Math.max(8,Math.min(innerWidth-tip.offsetWidth-8,b.left+b.width/2-tip.offsetWidth/2))+'px';tip.style.top=top+'px'});n.addEventListener('mouseleave',function(){tip.hidden=true})})});

var DIFF_KEY='btd6-diff';function curMult(){try{return +localStorage.getItem(DIFF_KEY)||1}catch(x){return 1}}
function applyDiff(){var m=curMult();document.querySelectorAll('.diff button').forEach(function(b){b.classList.toggle('on',+b.dataset.mult===m)});
document.querySelectorAll('.cost[data-parts]').forEach(function(el){var s=el.dataset.parts.split(',').reduce(function(a,p){return a+(m===1?+p:Math.round(p*m/5)*5)},0);
el.textContent='$'+s.toLocaleString('ru-RU')});document.querySelectorAll('.hcalc').forEach(hcalc);
document.querySelectorAll('.pcalc').forEach(function(c){if(c._update)c._update()})}
document.querySelectorAll('.diff button').forEach(function(b){b.addEventListener('click',function(){try{localStorage.setItem(DIFF_KEY,b.dataset.mult)}catch(x){}applyDiff()})});
function pcalc(c){var reqs=JSON.parse(c.dataset.reqs),paragons=JSON.parse(c.dataset.paragons);
var towerSel=c.querySelector('.pcalc-tower'),popsIn=c.querySelector('.pcalc-pops'),incIn=c.querySelector('.pcalc-inc'),
cashIn=c.querySelector('.pcalc-cash'),sliderIn=c.querySelector('.pcalc-slider'),t5In=c.querySelector('.pcalc-t5'),
tiersIn=c.querySelector('.pcalc-tiers'),totemsIn=c.querySelector('.pcalc-totems');
var degEl=c.querySelector('.pcalc-deg'),barEl=c.querySelector('.pcalc-bar'),powerEl=c.querySelector('.pcalc-power'),
nextEl=c.querySelector('.pcalc-next'),pbPops=c.querySelector('.pb-pops'),pbCash=c.querySelector('.pb-cash'),
pbT5=c.querySelector('.pb-t5'),pbTiers=c.querySelector('.pb-tiers'),pbTotems=c.querySelector('.pb-totems');
var C=JSON.parse(c.dataset.cfg),top=C.MaxInvestment,ru=function(v){return v.toLocaleString('ru-RU')},k=function(v){return v/1000+'k'};
function update(){var pInfo=paragons[towerSel.value]||{cost:300000};var m=curMult();
var cost=m===1?pInfo.cost:Math.round(pInfo.cost*m/5)*5;var costRatio=cost/C.moneySpentOverX;
var pops=+popsIn.value||0,inc=+incIn.value||0;
var p_pops=Math.min(Math.floor((pops+inc*C.cashEarnedContributionModifier)/C.popsOverX),C.maxPowerFromPops);
var p_t5=Math.min((+t5In.value||0)*C.tier5TowersMultByX,C.maxPowerFromTier5Count);
var p_tiers=tiersIn?Math.min((+tiersIn.value||0)*C.nonTier5TowersMultByX,C.maxPowerFromNonTier5Count):0;
var cashSpent=+cashIn.value||0,sliderCash=+sliderIn.value||0;
var p_cash=Math.min(Math.floor(cashSpent/costRatio)+Math.floor(sliderCash/(costRatio*(1+C.paidContributionPenalty))),C.maxPowerFromMoneySpent);
var p_totems=(+totemsIn.value||0)*2000;
var total=Math.min(p_pops+p_t5+p_tiers+p_cash+p_totems,top);
var deg=1;for(var i=0;i<reqs.length;i++){if(total>=reqs[i])deg=i+1;else break}
degEl.textContent=deg;powerEl.textContent=ru(total)+' / '+ru(top)+' силы';
barEl.style.width=(total/top*100)+'%';
if(deg<reqs.length){var rem=reqs[deg]-total;nextEl.textContent='Нужно '+ru(rem)+' силы до степени '+(deg+1)}
else{nextEl.textContent='Максимальная 100 степень!'}
pbPops.textContent=ru(p_pops)+' / '+k(C.maxPowerFromPops);pbCash.textContent=ru(p_cash)+' / '+k(C.maxPowerFromMoneySpent);
pbT5.textContent=ru(p_t5)+' / '+k(C.maxPowerFromTier5Count);if(pbTiers)pbTiers.textContent=ru(p_tiers)+' / '+k(C.maxPowerFromNonTier5Count);
pbTotems.textContent='+'+p_totems.toLocaleString('ru-RU')}
c._update=update;c.querySelectorAll('input,select').forEach(function(el){el.addEventListener('input',update);el.addEventListener('change',update)});
update()}
document.querySelectorAll('.pcalc').forEach(pcalc);
document.querySelectorAll('.mod-params').forEach(function(el){if(el.scrollHeight>68){el.classList.add('overflowing');el.title='Нажмите, чтобы показать все параметры';el.addEventListener('click',function(){el.classList.toggle('open')})}});
applyDiff();
(function(){var kn=document.querySelector('.knav');if(!kn)return;var links=kn.querySelectorAll('a'),secs=[];
links.forEach(function(a){var id=a.getAttribute('href').slice(1),el=document.getElementById(id);if(el)secs.push({el:el,a:a})});
function up(){var off=kn.offsetHeight+kn.getBoundingClientRect().top+20,cur=null;
secs.forEach(function(s){if(s.el.getBoundingClientRect().top<=off)cur=s});
links.forEach(function(a){a.classList.remove('on')});if(cur)cur.a.classList.add('on')}
window.addEventListener('scroll',up,{passive:true});up()})();
(function(){var top=document.querySelector('.top');if(!top)return;function h(){document.documentElement.style.setProperty('--top-h',top.offsetHeight+'px')}h();if(window.ResizeObserver)new ResizeObserver(h).observe(top)})();
document.querySelectorAll('.xp').forEach(function(xp){var data=JSON.parse(xp.parentNode.querySelector('.xp-data').textContent),
st=[0,0,0],variant=null,out=xp.querySelector('.xp-out');
function e(s){return String(s==null?'–':s).replace(/[&<>"']/g,function(c){return'&#'+c.charCodeAt(0)+';'})}
function f(v){if(v==null)return'–';if(typeof v==='number')return(Math.round(v*1e4)/1e4).toLocaleString('ru-RU');return e(v)}
function key(){return st.join('')}
function fix(changed){if(data[key()])return;for(var i=0;i<3;i++){if(i===changed)continue;while(st[i]>0&&!data[key()])st[i]--}
if(!data[key()]){for(var j=0;j<3;j++)if(j!==changed)st[j]=0}}
function draw(){var k=variant||key(),d=data[k];xp.querySelectorAll('.xp-row[data-path]').forEach(function(r){var p=+r.dataset.path;
r.querySelectorAll('button').forEach(function(b){b.classList.toggle('on',!variant&&+b.dataset.tier===st[p])})});
xp.querySelectorAll('[data-variant]').forEach(function(b){b.classList.toggle('on',b.dataset.variant===variant)});
if(!d){out.innerHTML='<p class="note">Нет данных для '+e(k)+'.</p>';return}
var h='<div class="stats"><div class="stat"><b class="cost" data-parts="'+d.parts.join(',')+'">$'+f(d.cost)+'</b><small>цена '+e(/^\d{3}$/.test(k)?k.split('').join('-'):k)+'</small></div><div class="stat"><b>'+f(d.range)+'</b><small>дальность</small></div></div>';
d.attacks.forEach(function(a,ai){h+='<h3>'+e(a.name)+' <span class="id">дальность '+f(a.range)+'</span></h3><div class="wrap"><table><thead><tr><th>Оружие</th><th>Перезарядка, с</th><th>Атак/с</th><th>Снаряд</th><th>Кол-во</th><th>Урон</th><th>Урон за выстрел</th><th>Пробив.</th><th>Примерный DPS</th><th>Модификаторы и эффекты</th><th>Не лопает</th></tr></thead><tbody>';
a.weapons.forEach(function(w,wi){var n=Math.max(1,w.proj.length);w.proj.forEach(function(p,pi){h+='<tr>'+(pi===0?'<td rowspan="'+n+'">'+(wi+1)+(w.emission?' <span class="id">'+e(w.emission)+'</span>':'')+'</td><td class="n" rowspan="'+n+'">'+f(p.rate)+'</td><td class="n" rowspan="'+n+'">'+(p.rate?f(1/p.rate):'–')+'</td>':'')
+'<td style="padding-left:'+(10+p.depth*16)+'px">'+(p.depth?'↳ ':'')+e(p.projectile)+'</td><td class="n">'+f(p.count)+'</td><td class="n">'+f(p.damage)+'</td><td class="n">'+f(p.shotDamage)+'</td><td class="n">'+f(p.pierce)+'</td><td class="n">'+f(p.dps)+'</td><td>'
 +p.mods.concat(p.effects).map(function(m){return'<span class="chip">'+e(m)+'</span>'}).join(' ')+'</td><td>'+((p.immune||[]).length?p.immune.map(function(x){return'<a class="chip no" href="bloons.html#prop-'+x[0]+'">'+e(x[1])+'</a>'}).join(' '):'–')+'</td></tr>'});
if(!w.proj.length)h+='<tr><td>'+(wi+1)+'</td><td class="n">'+f(w.rate)+'</td><td class="n">'+(w.rate?f(1/w.rate):'–')+'</td><td colspan="8">–</td></tr>'});
h+='</tbody></table></div>'});if(d.attacks.length)h+='<p class="note">Примерный DPS: урон за выстрел / перезарядка. Без учёта баффов, пробивания и множителей режима.</p>';
if(d.abilities.length)h+='<h3>Способности</h3><div class="chips">'+d.abilities.map(function(a){return'<a class="chip" href="#abilities">'+e(a.name)+', перезарядка '+f(a.cooldown)+' с</a>'}).join('')+'</div>';
if(d.other.length)h+='<h3>Прочие поведения</h3><div class="chips">'+d.other.map(function(o){return'<span class="chip">'+e(o)+'</span>'}).join('')+'</div>';
out.innerHTML=h;applyDiff()}
xp.querySelectorAll('.xp-row[data-path] button').forEach(function(b){b.addEventListener('click',function(){var p=+b.parentNode.dataset.path;variant=null;st[p]=+b.dataset.tier;fix(p);draw()})});
xp.querySelectorAll('[data-variant]').forEach(function(b){b.addEventListener('click',function(){variant=b.dataset.variant;draw()})});
draw()});
function openTarget(){var id=decodeURIComponent(location.hash.slice(1));if(!id)return;var el=document.getElementById(id);if(!el)return;var d=el.closest('details');if(d&&!d.open){d.open=true;el.scrollIntoView()}}
window.addEventListener('hashchange',openTarget);openTarget();
})();
// achievements: a hidden row stays a blurred spoiler until clicked; the checkbox opens all; a link to one (#a12) opens it
(function(){document.querySelectorAll('tr.spoiler').forEach(function(r){r.addEventListener('click',function(){r.classList.add('open')})});
document.querySelectorAll('[data-reveal]').forEach(function(c){c.addEventListener('change',function(){document.querySelector(c.dataset.reveal).classList.toggle('revealed',c.checked)})});
function fromHash(){var el=document.getElementById(decodeURIComponent(location.hash.slice(1)));var r=el&&el.closest('tr.spoiler');if(r)r.classList.add('open')}
window.addEventListener('hashchange',fromHash);fromHash()})();
(function(){document.querySelectorAll('.mapview').forEach(function(v){var svg=v.querySelector('svg'),xy=v.querySelector('.map-xy');
v.querySelectorAll('[data-layer]').forEach(function(c){c.addEventListener('change',function(){svg.classList.toggle('no-'+c.dataset.layer,!c.checked)})});
var rms=svg.querySelectorAll('.rm');var eff=function(g,gone){var ids=function(k){return (g.dataset[k]||'').split(' ').filter(Boolean)};ids('off').forEach(function(i){svg.querySelectorAll('[data-a="'+i+'"]').forEach(function(el){el.classList.toggle('gone-a',gone)})});ids('on').forEach(function(i){svg.querySelectorAll('[data-a="'+i+'"]').forEach(function(el){el.classList.toggle('dis',!gone)})});var path=function(id,on){svg.querySelectorAll('.path').forEach(function(p){if((' '+p.dataset.p+' ').indexOf(' '+id+' ')>=0)p.classList.toggle('idle',!on)})};ids('pon').forEach(function(id){path(id,gone)});ids('poff').forEach(function(id){path(id,!gone)})};svg.mapFx=eff;rms.forEach(function(g){var go=function(){eff(g,g.classList.toggle('gone'))};g.addEventListener('click',go);g.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}})});
var full=v.querySelector('.map-full'),big=function(on){v.classList.toggle('big',on);document.body.classList.toggle('map-open',on);full.textContent=on?'Свернуть':'На весь экран'};full.addEventListener('click',function(){big(!v.classList.contains('big'))});document.addEventListener('keydown',function(e){if(e.key==='Escape'&&v.classList.contains('big'))big(false)});var all=v.querySelector('.rm-all');if(all)all.addEventListener('click',function(){var on=!Array.prototype.every.call(rms,function(g){return g.classList.contains('gone')});rms.forEach(function(g){g.classList.toggle('gone',on);eff(g,on)});all.textContent=on?'Вернуть все препятствия':'Убрать все препятствия'});
svg.addEventListener('mousemove',function(e){var p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;var q=p.matrixTransform(svg.getScreenCTM().inverse());xy.textContent='x '+q.x.toFixed(1)+', y '+q.y.toFixed(1)});
svg.addEventListener('mouseleave',function(){xy.textContent=''})})})();
(function(){var svg=document.querySelector('.mapsvg');if(!svg)return;var pinned=null;
function show(i){svg.querySelectorAll('.ev').forEach(function(g){g.classList.toggle('on',g.dataset.ev===i);g.classList.toggle('res',g.dataset.ev===pinned)})}var rowOf=function(i){return document.querySelector('.ev-row[data-ev="'+i+'"]')};
document.querySelectorAll('.ev-row').forEach(function(r){var i=r.dataset.ev;
r.addEventListener('mouseenter',function(){show(i)});r.addEventListener('mouseleave',function(){show(pinned)});
var go=function(){if(pinned!==null&&svg.mapFx)svg.mapFx(rowOf(pinned),false);pinned=pinned===i?null:i;if(pinned!==null&&svg.mapFx)svg.mapFx(r,true);document.querySelectorAll('.ev-row').forEach(function(x){x.classList.toggle('on',x.dataset.ev===pinned)});show(pinned);if(pinned)svg.scrollIntoView({block:'nearest',behavior:'smooth'})};
r.addEventListener('click',go);r.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}})})})();
