/* Offline JavaScript rendering/filter smoke test; no real browser or DOM layout test. */
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const fixture=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const elements=new Map();
function el(selector){if(!elements.has(selector))elements.set(selector,{content:'test-token',innerHTML:'',textContent:'',style:{},open:false,disabled:false,value:'',classList:{toggle(){},add(){},remove(){}},showModal(){this.open=true;},close(){this.open=false;},addEventListener(){}});return elements.get(selector);}
const ctx=vm.createContext({fixture,console,assert,document:{querySelector:el,querySelectorAll:()=>[],addEventListener(){}},window:{scrollTo(){},open(){}},localStorage:{getItem:()=>null,setItem(){}},navigator:{clipboard:{writeText:async()=>{}}},setTimeout:()=>0,setInterval:()=>0,clearInterval(){},fetch:async()=>({ok:true,json:async()=>fixture,text:async()=>''}),FormData:class { *[Symbol.iterator](){} }});
const js=fs.readFileSync(path.join(__dirname,'../radar/static/app.js'),'utf8').replace(/\nload\(\)\.catch\([\s\S]*$/,'');
vm.runInContext(js,ctx);
(async()=>{
 await vm.runInContext(`(async()=>{state=fixture;
  for(const t of ['overview','mine','cfi','early','regional','longterm','pathways','briefings','employers','sources','profile']){navigate(t);assert($('#content').innerHTML.length>150,'Empty view '+t);}
  for(const j of state.items){j.read=true;j.updated_since_read=false;}
  await itemModal(state.items[0].id);assert($('#modal-body').innerHTML.includes('Published requirements'));
  requirementModal(state.items[0].id);assert($('#modal-body').innerHTML.includes('requirement-rows'));
  for(const source of state.sources){sourceModal(source.id);assert($('#modal-body').innerHTML.includes('Expected sample'));}
  employerModal(state.employers[0].id);employerModal('','Test employer');pathwayModal(state.pathways[0].id);addPathwayModal();addItemModal('longterm');pasteProfileModal();
  showProfilePreview(state.profile_imports[0]);assert($('#modal-body').innerHTML.includes('Nothing has changed yet'));
  briefingModal(state.briefings[0].id);assert($('#modal-body').innerHTML.includes('Responses remain commentary'));
  tab='early';filter().region='all';filter().group=false;
  const count=filtered().length;assert(count>=3);assert(results().includes('Qualification fit needs confirmation'));
  filter().region='surrounding';const surrounding=filtered();assert(surrounding.some(j=>j.title==='Fixture Ohio'));assert(!surrounding.some(j=>j.title==='Fixture California'));assert(surrounding.some(j=>j.title==='Fixture unknown'));
  filter().unknown=false;assert(!filtered().some(j=>j.title==='Fixture unknown'));
  filter().region='all';filter().group=true;assert(results().includes('Future opportunities'));
  tab='mine';filter().region='all';assert(filtered().every(j=>j.pinned));
  assert(!safeURL('javascript:alert(1)').startsWith('javascript:'));assert(esc('<script>').includes('&lt;script&gt;'));
 })()`,ctx);
 console.log('Dashboard JavaScript: all 11 views, dialogs, geographic filters, pinned results and escaping passed (offline DOM stub).');
})().catch(e=>{console.error(e);process.exit(1);});
