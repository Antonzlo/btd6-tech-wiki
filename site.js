
(function(){
var box=document.getElementById('q'),out=document.getElementById('qr'),status=document.getElementById('q-status');if(!box)return;var sel=0,hits=[];
var empty=false;
function norm(s){return s.toLowerCase().replace(/ё/g,'е').replace(/[\s\-]+/g,' ')}
function rank(e,q,ws){var t=norm(e[0]),x=t+' '+norm(e[3]||'');
for(var i=0;i<ws.length;i++)if(x.indexOf(ws[i])<0)return -1;
return t===q?0:t.indexOf(q+' ')===0?1:t.indexOf(q)===0?2:(' '+t).indexOf(' '+q)>=0?3:t.indexOf(q)>=0?4:5}
function select(i,scroll){sel=i;Array.prototype.forEach.call(out.children,function(a,j){
var active=j===i;a.classList.toggle('sel',active);a.setAttribute('aria-selected',active)});
var active=out.children[i];if(active){box.setAttribute('aria-activedescendant',active.id);if(scroll)active.scrollIntoView({block:'nearest'})}
else box.removeAttribute('aria-activedescendant')}
function draw(){out.innerHTML='';hits.forEach(function(h,i){var a=document.createElement('a');a.href=h[2];
a.id='q-option-'+i;a.tabIndex=-1;a.setAttribute('role','option');
var s=document.createElement('span');s.textContent=h[0];var m=document.createElement('small');
m.textContent=h[1];a.appendChild(s);a.appendChild(m);a.addEventListener('mouseenter',function(){select(i,false)});
out.appendChild(a)});
out.hidden=!hits.length;box.setAttribute('aria-expanded',!out.hidden);select(sel,false);
status.textContent=empty?'Ничего не найдено':''}
function close(){hits=[];empty=false;draw()}
box.addEventListener('input',function(){var q=norm(box.value.trim()),ws=q.split(' ');sel=0;
hits=q?WIKI_INDEX.map(function(e){return[rank(e,q,ws),e]}).filter(function(p){return p[0]>=0})
.sort(function(a,b){return a[0]-b[0]||a[1][0].length-b[1][0].length}).slice(0,14).map(function(p){return p[1]}):[];
empty=!!q&&!hits.length;draw()});
box.addEventListener('focus',function(){if(box.value.trim())box.dispatchEvent(new Event('input'))});
box.addEventListener('keydown',function(e){if(e.key==='Escape'){if(hits.length||empty)close();else{box.value='';box.blur()}return}
if(!hits.length)return;if(e.key==='ArrowDown'){select(Math.min(sel+1,hits.length-1),true);e.preventDefault()}
else if(e.key==='ArrowUp'){select(Math.max(sel-1,0),true);e.preventDefault()}else if(e.key==='Enter'){location.href=hits[sel][2]}});
box.addEventListener('blur',function(e){if(!out.contains(e.relatedTarget))close()});
out.addEventListener('mousedown',function(e){if(e.button===0)e.preventDefault()});
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
var full=v.querySelector('.map-full'),dialog=document.createElement('dialog'),marker=document.createComment('mapview');
dialog.className='map-dialog';dialog.setAttribute('aria-label','Схема карты');
full.addEventListener('click',function(){
if(dialog.open){dialog.close();return}
if(dialog.isConnected)return;
v.before(marker);dialog.appendChild(v);document.body.appendChild(dialog);
full.textContent='Свернуть';dialog.showModal();document.body.classList.add('map-open');full.focus()});
dialog.addEventListener('close',function(){
marker.replaceWith(v);dialog.remove();document.body.classList.remove('map-open');full.textContent='На весь экран';full.focus()});
var all=v.querySelector('.rm-all');if(all)all.addEventListener('click',function(){var on=!Array.prototype.every.call(rms,function(g){return g.classList.contains('gone')});rms.forEach(function(g){g.classList.toggle('gone',on);eff(g,on)});all.textContent=on?'Вернуть все препятствия':'Убрать все препятствия'});
svg.addEventListener('mousemove',function(e){var p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;var q=p.matrixTransform(svg.getScreenCTM().inverse());xy.textContent='x '+q.x.toFixed(1)+', y '+q.y.toFixed(1)});
svg.addEventListener('mouseleave',function(){xy.textContent=''})})})();
(function(){var svg=document.querySelector('.mapsvg');if(!svg)return;var pinned=null;
function show(i){svg.querySelectorAll('.ev').forEach(function(g){g.classList.toggle('on',g.dataset.ev===i);g.classList.toggle('res',g.dataset.ev===pinned)})}var rowOf=function(i){return document.querySelector('.ev-row[data-ev="'+i+'"]')};
document.querySelectorAll('.ev-row').forEach(function(r){var i=r.dataset.ev;
r.addEventListener('mouseenter',function(){show(i)});r.addEventListener('mouseleave',function(){show(pinned)});
var go=function(){if(pinned!==null&&svg.mapFx)svg.mapFx(rowOf(pinned),false);pinned=pinned===i?null:i;if(pinned!==null&&svg.mapFx)svg.mapFx(r,true);document.querySelectorAll('.ev-row').forEach(function(x){x.classList.toggle('on',x.dataset.ev===pinned)});show(pinned);if(pinned)svg.scrollIntoView({block:'nearest',behavior:'smooth'})};
r.addEventListener('click',go);r.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}})})})();
// tower placement on the map: footprint from the dump (circle or rectangle), checked against the areas drawn on the map
// (removed obstacles and map events included) and towers already placed
(function(){document.querySelectorAll('.mapview').forEach(function(v){
var svg=v.querySelector('.mapsvg'),pick=v.querySelector('.place'),clear=v.querySelector('.place-clear'),layer=svg&&svg.querySelector('.L-tw');if(!pick||!layer)return;
var NS='http://www.w3.org/2000/svg',ghost=null,placed=[];
// rings from the path data "Mx,yLx,y...Z" per ring; even-odd over all rings handles holes
var areas=Array.prototype.map.call(svg.querySelectorAll('path.a'),function(p){var c=p.classList;
return{el:p,kind:c.contains('blk')?'blocker':c.contains('track')?'track':c.contains('unplaceable')?'unplaceable':c.contains('water')?'water':'land',
rings:p.getAttribute('d').split('M').filter(Boolean).map(function(r){return r.replace('Z','').split('L').map(function(q){return q.split(',').map(Number)})})}});
function live(a){return!a.el.classList.contains('dis')&&!a.el.classList.contains('gone-a')&&!a.el.closest('.rm.gone')}
function inPoly(x,y,rings){var hit=false;rings.forEach(function(r){for(var i=0,j=r.length-1;i<r.length;j=i++){var a=r[i],b=r[j];
if((a[1]>y)!==(b[1]>y)&&x<a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))hit=!hit}});return hit}
function segDist(x,y,a,b){var dx=b[0]-a[0],dy=b[1]-a[1],l=dx*dx+dy*dy,t=l?Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/l)):0;
return Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)}
// points of the footprint: centre, two rings for a circle, a 2-unit grid for a rectangle
function samples(f,x,y){var s=[[x,y]],i,j;if(f.r){[f.r,f.r/2].forEach(function(r){for(i=0;i<24;i++)s.push([x+r*Math.cos(i*Math.PI/12),y+r*Math.sin(i*Math.PI/12)])})}
else{var nx=Math.ceil(f.w/2),ny=Math.ceil(f.h/2);for(i=0;i<=nx;i++)for(j=0;j<=ny;j++)s.push([x-f.w/2+f.w*i/nx,y-f.h/2+f.h*j/ny])}return s}
function touches(a,f,x,y){if(f.r)return inPoly(x,y,a.rings)||a.rings.some(function(r){return r.some(function(p,i){return segDist(x,y,p,r[(i+1)%r.length])<f.r-1e-6})});
// ponytail: rectangle vs polygon by samples plus polygon corners inside, a sliver thinner than 2 units can slip through
return samples(f,x,y).some(function(p){return inPoly(p[0],p[1],a.rings)})||a.rings.some(function(r){return r.some(function(p){return Math.abs(p[0]-x)<f.w/2&&Math.abs(p[1]-y)<f.h/2})})}
function overlap(f,x,y,p){var g=p.f,dx=Math.abs(x-p.x),dy=Math.abs(y-p.y);
if(f.r&&g.r)return Math.hypot(dx,dy)<f.r+g.r-1e-6;
if(!f.r&&!g.r)return dx<(f.w+g.w)/2-1e-6&&dy<(f.h+g.h)/2-1e-6;
var c=f.r?f:g,b=f.r?g:f;return Math.hypot(Math.max(0,dx-b.w/2),Math.max(0,dy-b.h/2))<c.r-1e-6}
// ponytail: rule guessed, not from game code: no track or no-placing area under any part of the footprint, every
// sampled point on ground the tower allows (topmost area in map order; off-screen points pass, the game lets a
// footprint hang over the screen edge), centre on screen, line of sight blockers ignored; check against the game
function ok(f,x,y){var vb=svg.viewBox.baseVal;if(x<vb.x||y<vb.y||x>vb.x+vb.width||y>vb.y+vb.height)return false;
var on=areas.filter(live);
// the game lets a footprint overlap track and no-placing areas by about 1.5 units: Pat's Pond dump, Dart Monkeys (r 6)
// with centres 4.5 to 5.1 from the track; towers among themselves touch at the full radius (12 apart)
// ponytail: one fixed slack fitted on r 6 only, could be a share of the radius; dump big towers by the track to tell
var s=1.5,g={r:f.r&&f.r-s,w:f.w&&f.w-2*s,h:f.h&&f.h-2*s};
if(on.some(function(a){return(a.kind==='track'||a.kind==='unplaceable')&&touches(a,g,x,y)}))return false;
if(!samples(f,x,y).every(function(s){var top=null;on.forEach(function(a){if((a.kind==='land'||a.kind==='water')&&inPoly(s[0],s[1],a.rings))top=a.kind});return!top||f.on.indexOf(top)>=0}))return false;
return!placed.some(function(p){return overlap(f,x,y,p)})}
function fp(){var o=pick.selectedOptions[0];if(!o||!o.value)return null;var d=o.dataset;
return{id:o.value,name:o.textContent,r:+d.r||0,w:+d.w||0,h:+d.h||0,on:d.on.split(' ')}}
function shape(f,x,y,cls){var el=document.createElementNS(NS,f.r?'circle':'rect');
if(f.r){el.setAttribute('cx',x);el.setAttribute('cy',y);el.setAttribute('r',f.r)}
else{el.setAttribute('x',x-f.w/2);el.setAttribute('y',y-f.h/2);el.setAttribute('width',f.w);el.setAttribute('height',f.h)}
el.setAttribute('class',cls);return el}
function at(e){var p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform(svg.getScreenCTM().inverse())}
function add(f,x,y){var el=shape(f,x,y,'tw'),t=document.createElementNS(NS,'title');t.textContent=f.name+': x '+x.toFixed(1)+', y '+y.toFixed(1)+' (нажмите, чтобы убрать)';
el.appendChild(t);layer.appendChild(el);placed.push({f:f,x:x,y:y,el:el});clear.hidden=false}
svg.addEventListener('mousemove',function(e){var f=fp();if(ghost){ghost.remove();ghost=null}if(!f)return;var q=at(e);
ghost=shape(f,q.x,q.y,'tw-ghost '+(ok(f,q.x,q.y)?'fit':'nofit'));layer.appendChild(ghost)});
svg.addEventListener('mouseleave',function(){if(ghost){ghost.remove();ghost=null}});
// capture: while a tower is picked, clicks place it instead of removing obstacles; a click on a placed tower removes it
svg.addEventListener('click',function(e){var hit=placed.filter(function(p){return p.el===e.target})[0];
if(hit){hit.el.remove();placed.splice(placed.indexOf(hit),1);clear.hidden=!placed.length;e.stopPropagation();return}
var f=fp();if(!f)return;e.stopPropagation();var q=at(e);if(ok(f,q.x,q.y))add(f,q.x,q.y)},true);
clear.addEventListener('click',function(){placed.forEach(function(p){p.el.remove()});placed=[];clear.hidden=true});
// towers placed in game (from the dump) block like placed ones; one the rule would refuse is a rule bug, marked red
layer.querySelectorAll('.tw.game').forEach(function(el){var o=pick.querySelector('option[value="'+el.dataset.id+'"]');if(!o)return;
var d=o.dataset;placed.push({f:{id:o.value,name:o.textContent,r:+d.r||0,w:+d.w||0,h:+d.h||0,on:d.on.split(' ')},x:+el.dataset.x,y:+el.dataset.y,el:el})});
placed.forEach(function(p,i){placed.splice(i,1);var fits=ok(p.f,p.x,p.y);placed.splice(i,0,p);p.el.classList.toggle('miss',!fits)});
var misses=layer.querySelectorAll('.tw.miss').length;if(placed.length){var note=document.createElement('span');
note.textContent='башен из игры: '+placed.length+(misses?', правило не пускает: '+misses:', правило пускает все');pick.parentNode.after(note)}
clear.hidden=!placed.length;
svg.placeTest={fp:function(id){pick.value=id;return fp()},ok:ok,add:add}})})();
