const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
function element() {
  return {children: [], value: '', textContent: '', disabled: false, dataset: {}, attributes: {},
    style: {}, offsetWidth: 180, offsetHeight: 100,
    classList: {toggle() {}, remove() {}, add() {}},
    addEventListener(name, fn) {this[`on_${name}`] = fn; if(name!=='close') this[name] = fn;}, setAttribute(k,v) {this.attributes[k]=v;},
    focus() {}, showModal() {this.open=true;}, close() {this.open=false;this.on_close?.();},
    contains() {return false;}, getBoundingClientRect() {return {left:0,right:32,top:0,bottom:32};},
    append(...nodes) {this.children.push(...nodes);}, replaceChildren(...nodes) {this.children=[...nodes];},
    scrollIntoView() {}, querySelectorAll() {return this.children;}};
}
const response = (payload, status=200) => ({ok:status<400, status, json:async()=>payload});
async function setup({anon=false, chat, history, override, confirmDelete=true}={}) {
  const ids = {};
  const get = id => ids[id] ||= element();
  const button = element(); get('ask-form').querySelector = ()=>button;
  const pill=element(); pill.dataset.prompt='What is a deductible?';
  const calls=[]; let messages=history || []; let counter=0;
  const storage=new Map();
  const context=vm.createContext({document:{getElementById:get, querySelector:()=>element(), querySelectorAll:()=>[pill], createElement:()=>element(), addEventListener(){}},
    window:{innerWidth:1280,innerHeight:900},
    crypto:{randomUUID:()=>`request-${++counter}`}, localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    confirm:()=>confirmDelete, AbortController,setTimeout,clearTimeout,
    fetch: async(url,options={})=>{calls.push({url,options});
      if(override) {const result=await override(url,options); if(result!==undefined) return result;}
      if(url==='/api/health') return response({status:'ok',services:Object.fromEntries(['concierge','policy','research'].map(k=>[k,{status:'available'}]))});
      if(url==='/api/auth/me') return anon?response({},401):response({user:{id:'u1',email:'one@example.com'},csrf_token:'csrf'});
      if(url==='/api/auth/login'||url==='/api/auth/register') return response({user:{id:'u1',email:'one@example.com'},csrf_token:'csrf'});
      if(url==='/api/auth/logout') return response(null,204);
      if(url==='/api/conversations') return response(options.method==='POST'?{id:'c1',title:'New conversation'}:{conversations:[{id:'c1',title:'First',title_ready:true}]});
      if(url.endsWith('/messages')) return response({messages});
      if(options.method==='PATCH') return response({id:'c1',title:JSON.parse(options.body).title});
      if(options.method==='DELETE') return response(null,204);
      if(url==='/api/chat') {const body=JSON.parse(options.body); if(chat) return chat(body); messages=[...messages,{role:'user',content:body.message,status:'complete'},{role:'assistant',content:'Safe <script>answer</script>',status:'complete'}]; return response({answer:'Safe <script>answer</script>'});}
      throw Error(url);
    }});
  vm.runInContext(readFileSync('frontend/app.js','utf8'),context);
  await new Promise(setImmediate);
  return {ids,button,pill,calls,storage,submit:async value=>{get('medical-input').value=value;await get('ask-form').submit({preventDefault(){}});}};
}
test('requires authentication before sending chat',async()=>{const ui=await setup({anon:true});await ui.submit('hi');assert.equal(ui.calls.filter(c=>c.url==='/api/chat').length,0);assert.equal(ui.button.disabled,true);});
test('sends conversation, idempotency and CSRF identifiers and renders stored messages',async()=>{const ui=await setup();await ui.submit('  benefits? ');const call=ui.calls.find(c=>c.url==='/api/chat');assert.deepEqual(JSON.parse(call.options.body),{message:'benefits?',conversation_id:'c1',request_id:'request-1'});assert.equal(call.options.headers['X-CSRF-Token'],'csrf');assert.equal(call.options.headers['X-Requested-With'],'fetch');assert.equal(ui.ids.conversation.children.length,2);assert.equal(ui.ids.conversation.children[1].children[1].textContent,'Safe <script>answer</script>');});
test('refreshes the first chat title after background generation',async()=>{
  let sent=false; let reads=0;
  const ui=await setup({override:async(url,options={})=>{
    if(url==='/api/chat') {sent=true; return undefined;}
    if(url==='/api/conversations' && options.method!=='POST' && sent) {
      reads+=1;
      return response({conversations:[{id:'c1',title:reads===1?'First question':'Insurance deductible',title_ready:reads>1}]});
    }
  }});
  await ui.submit('What is my deductible?');
  assert.equal(ui.ids['conversation-list'].children[0].children[0].textContent,'First question');
  await new Promise(resolve=>setTimeout(resolve,1100));
  assert.equal(ui.ids['conversation-list'].children[0].children[0].textContent,'Insurance deductible');
});
test('uncertain retry reuses request identifier',async()=>{const ui=await setup({chat:async()=>{throw new TypeError('offline');}});await ui.submit('hello');await ui.submit('hello');const requests=ui.calls.filter(c=>c.url==='/api/chat').map(c=>JSON.parse(c.options.body));assert.equal(requests[0].request_id,requests[1].request_id);assert.match(ui.ids['composer-error'].textContent,/connection/i);});
test('logout clears rendered history and disables chat',async()=>{const ui=await setup();await ui.submit('private');await ui.ids.logout.click();assert.equal(ui.ids.conversation.children.length,0);assert.equal(ui.ids['account-email'].textContent,'');assert.equal(ui.button.disabled,true);});
test('blank and overlong inputs never send',async()=>{const ui=await setup();await ui.submit(' ');await ui.submit('x'.repeat(8001));assert.equal(ui.calls.filter(c=>c.url==='/api/chat').length,0);});
test('example prompt and green connection remain',async()=>{const ui=await setup();ui.pill.click();assert.equal(ui.ids['medical-input'].value,'What is a deductible?');assert.equal(ui.ids['check-connection'].dataset.state,'connected');});
test('registration sends credentials without browser persistence',async()=>{const ui=await setup({anon:true});ui.ids['auth-toggle'].click();ui.ids['auth-email'].value='one@example.com';ui.ids['auth-password'].value='long-password';await ui.ids['auth-form'].submit({preventDefault(){}});assert.ok(ui.calls.some(c=>c.url==='/api/auth/register'));assert.equal(ui.ids['auth-password'].value,'');assert.equal([...ui.storage.values()].includes('long-password'),false);});

test('pending submission blocks duplicate model calls',async()=>{
  let finish; const ui=await setup({chat:()=>new Promise(resolve=>{finish=resolve;})});
  const pending=ui.submit('hello'); await new Promise(setImmediate);
  await ui.submit('again'); assert.equal(ui.calls.filter(c=>c.url==='/api/chat').length,1);
  finish(response({answer:'done'})); await pending; assert.equal(ui.button.disabled,false);
});
test('late chat response cannot restore history after logout',async()=>{
  let finish; const ui=await setup({chat:()=>new Promise(resolve=>{finish=resolve;})});
  const pending=ui.submit('private'); await new Promise(setImmediate);
  await ui.ids.logout.click(); finish(response({answer:'private answer'})); await pending;
  assert.equal(ui.ids.conversation.children.length,0); assert.equal(ui.button.disabled,true);
});
test('new conversation clears view and creates a server conversation on send',async()=>{
  const ui=await setup(); await ui.submit('first'); await ui.ids['new-conversation'].click();
  assert.equal(ui.ids.conversation.children.length,0); await ui.submit('second');
  assert.ok(ui.calls.some(c=>c.url==='/api/conversations'&&c.options.method==='POST'));
});
test('delete requires confirmation and clears current messages',async()=>{
  const cancelled=await setup({confirmDelete:false});
  cancelled.ids['conversation-list'].children[0].children[1].click({stopPropagation(){}});
  await cancelled.ids['delete-conversation'].click();
  assert.equal(cancelled.calls.filter(c=>c.options.method==='DELETE').length,0);
  const ui=await setup(); await ui.submit('history');
  ui.ids['conversation-list'].children[0].children[1].click({stopPropagation(){}});
  await ui.ids['delete-conversation'].click();
  assert.equal(ui.calls.filter(c=>c.options.method==='DELETE').length,1);
  assert.equal(ui.ids.conversation.children.length,0);
});
test('session expiry hides history and asks user to sign in',async()=>{
  const ui=await setup({chat:async()=>response({detail:'Please sign in.'},401)});
  await ui.submit('private'); assert.equal(ui.ids.conversation.children.length,0); assert.equal(ui.button.disabled,true);
});
test('failed persisted turn restores its request id for retry',async()=>{
  const ui=await setup({history:[{role:'user',content:'retry me',status:'failed',request_id:'prior-request'}]});
  await ui.submit('retry me'); const call=ui.calls.find(c=>c.url==='/api/chat');
  assert.equal(JSON.parse(call.options.body).request_id,'prior-request');
});
test('health failure becomes offline without leaking internal error',async()=>{
  const ui=await setup({override:async url=>{if(url==='/api/health')throw new TypeError('private');}});
  assert.equal(ui.ids['check-connection'].dataset.state,'offline');
  assert.equal(ui.ids['connection-status'].textContent,'Offline');
});
test('auth error is visible and never saves the password',async()=>{
  const ui=await setup({anon:true,override:async url=>url==='/api/auth/login'?response({detail:'Wrong credentials'},401):undefined});
  ui.ids['auth-email'].value='one@example.com'; ui.ids['auth-password'].value='wrong-password';
  await ui.ids['auth-form'].submit({preventDefault(){}});
  assert.equal(ui.ids['auth-error'].textContent,'Wrong credentials');
  assert.equal(ui.ids['auth-submit'].disabled,false); assert.equal(ui.storage.size,0);
});
test('logout failure preserves session and reports failure',async()=>{
  const ui=await setup({override:async url=>url==='/api/auth/logout'?response({detail:'Server unavailable'},503):undefined});
  await ui.submit('question'); await ui.ids.logout.click();
  assert.match(ui.ids['composer-error'].textContent,/Sign out failed/);
  assert.equal(ui.ids.conversation.children.length,2);
});
