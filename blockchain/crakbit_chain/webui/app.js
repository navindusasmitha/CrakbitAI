"use strict";

const $ = (id) => document.getElementById(id);
const enc = new TextEncoder();
const dec = new TextDecoder();
const VAULT_KEY = "crakbit.wallet.v1";
const PKCS8_PREFIX = hexToBytes("302e020100300506032b657004220420");
let network = null;
let services = null;
let activeWallet = null;
let walletAccount = null;
let miningActive = false;
let miningChallenge = null;

const PAGE_META = {
  overview:["Overview","Network, wallet and service status"],
  wallet:["Wallet","Client-side Ed25519 wallet and transfers"],
  explorer:["Explorer","Blocks, commits, addresses and transactions"],
  mining:["Mining Lab","Opt-in proof-of-work test reward worker"],
  validators:["Validators","Consensus validator information"],
  settings:["Settings","Gateway and local security controls"]
};

function esc(value){return String(value ?? "").replace(/[&<>'"]/g,(c)=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[c]));}
function short(value,n=12){const s=String(value||"");return s.length>n*2+3?`${s.slice(0,n)}…${s.slice(-n)}`:s||"—";}
function bytesToHex(bytes){return [...new Uint8Array(bytes)].map((b)=>b.toString(16).padStart(2,"0")).join("");}
function hexToBytes(hex){const out=new Uint8Array(hex.length/2);for(let i=0;i<out.length;i++)out[i]=parseInt(hex.slice(i*2,i*2+2),16);return out;}
function concatBytes(...parts){const size=parts.reduce((n,p)=>n+p.length,0);const out=new Uint8Array(size);let at=0;for(const p of parts){out.set(p,at);at+=p.length;}return out;}
function b64(bytes){let binary="";for(const b of new Uint8Array(bytes))binary+=String.fromCharCode(b);return btoa(binary);}
function fromB64(value){const binary=atob(value);const out=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)out[i]=binary.charCodeAt(i);return out;}
function stableStringify(value){if(value===null||typeof value!=="object")return JSON.stringify(value);if(Array.isArray(value))return `[${value.map(stableStringify).join(",")}]`;return `{${Object.keys(value).sort().map((k)=>`${JSON.stringify(k)}:${stableStringify(value[k])}`).join(",")}}`;}
function validAddress(value){return /^crk1[0-9a-f]{40}$/.test(String(value||"").trim().toLowerCase());}

async function api(path,options={}){
  const response=await fetch(path,{...options,headers:{"Content-Type":"application/json",...(options.headers||{})}});
  const text=await response.text();let body=text;try{body=text?JSON.parse(text):{};}catch{}
  if(!response.ok){const detail=body&&typeof body==="object"?(body.detail??body):body;throw new Error(typeof detail==="string"?detail:JSON.stringify(detail));}
  return body;
}
function toast(message,type="success"){$("toast").textContent=message;$('toast').className=`toast show ${type}`;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$("toast").className="toast",3500);}

function formatAtomic(value,decimals=8){
  try{const n=BigInt(value??0);const base=10n**BigInt(decimals);const whole=n/base;const frac=(n%base).toString().padStart(decimals,"0").replace(/0+$/,"");return frac?`${whole}.${frac}`:whole.toString();}catch{return "0";}
}
function decimalToAtomic(value,decimals=8){
  const text=String(value).trim();if(!/^\d+(\.\d+)?$/.test(text))throw new Error("Amount must be a positive decimal number");
  const [whole,rawFrac=""]=text.split(".");if(rawFrac.length>decimals)throw new Error(`Amount supports at most ${decimals} decimal places`);
  const frac=rawFrac.padEnd(decimals,"0");return BigInt(whole)*(10n**BigInt(decimals))+BigInt(frac||"0");
}

async function refreshNetwork(){
  network=await api("/api/network");services=await api("/api/services");
  $("sideNetwork").textContent=network.network||network.chain_id;$("sideMode").textContent=network.mode;
  $("networkBadge").textContent=`${network.symbol} · ${network.mode}`;
  $("metricNetwork").textContent=network.network||network.symbol;$("metricChain").textContent=network.chain_id;
  $("metricHeight").textContent=Number(network.height||0).toLocaleString();$("metricHash").textContent=short(network.last_hash,8);
  $("metricConsensus").textContent=network.mode==="cometbft"?"CometBFT":"Research BFT";$("metricMode").textContent=network.consensus||network.mode;
  $("serviceFaucet").textContent=services.faucet?"Available":"Not configured";$("serviceFaucet").className=services.faucet?"ok":"";
  $("serviceMining").textContent=services.mining?"Work reward lab":"Not configured";$("serviceMining").className=services.mining?"ok":"";
  $("serviceConsensus").textContent=network.mode==="cometbft"?"CometBFT":"Python research path";
  $("walletSymbol").textContent=network.symbol||"CRKBIT";
  $("sendFee").textContent=`${formatAtomic(network.min_fee_atomic,network.decimals)} ${network.symbol}`;
  $("gatewayInfo").textContent=JSON.stringify({gateway:network.gateway,mode:network.mode,chain_id:network.chain_id,consensus:network.consensus,services},null,2);
}

async function refreshBlocks(){
  const data=await api("/api/blocks?limit=20");const items=data.items||[];
  const rows=items.map((b)=>`<tr><td>${esc(b.height)}</td><td><code title="${esc(b.hash||b.consensus_block_hash)}">${esc(short(b.hash||b.consensus_block_hash,8))}</code></td><td>${esc(b.transaction_count??0)}</td><td>${b.timestamp?new Date(Number(b.timestamp)).toLocaleString():b.committed_at_ms?new Date(Number(b.committed_at_ms)).toLocaleString():"—"}</td></tr>`).join("");
  $("explorerBlocks").innerHTML=rows||`<tr><td colspan="4">No finalized history yet.</td></tr>`;
  $("overviewBlocks").innerHTML=items.slice(0,8).map((b)=>`<tr><td>${esc(b.height)}</td><td><code>${esc(short(b.hash||b.consensus_block_hash,8))}</code></td><td>${esc(b.transaction_count??0)}</td></tr>`).join("")||`<tr><td colspan="3">No finalized history yet.</td></tr>`;
}

async function deriveAddress(publicKeyRaw){const digest=new Uint8Array(await crypto.subtle.digest("SHA-256",publicKeyRaw));return `crk1${bytesToHex(digest).slice(0,40)}`;}
async function generateWallet(){
  if(!crypto.subtle)throw new Error("WebCrypto is not available in this browser");
  const pair=await crypto.subtle.generateKey({name:"Ed25519"},true,["sign","verify"]);
  const pub=new Uint8Array(await crypto.subtle.exportKey("raw",pair.publicKey));
  const pkcs8=new Uint8Array(await crypto.subtle.exportKey("pkcs8",pair.privateKey));
  if(pkcs8.length<32)throw new Error("Unexpected Ed25519 private key encoding");
  const seed=pkcs8.slice(pkcs8.length-32);const address=await deriveAddress(pub);
  return {format:"crakbit-wallet-key/1",private_key:b64(seed),public_key:b64(pub),address};
}
async function validateWallet(wallet){
  if(!wallet||!wallet.private_key||!wallet.public_key)throw new Error("Wallet file is missing key material");
  const seed=fromB64(wallet.private_key),pub=fromB64(wallet.public_key);if(seed.length!==32||pub.length!==32)throw new Error("Crakbit Ed25519 keys must be 32 raw bytes");
  const address=await deriveAddress(pub);if(wallet.address&&wallet.address.toLowerCase()!==address)throw new Error("Wallet address does not match public key");return {...wallet,address};
}
async function vaultKey(password,salt){
  const material=await crypto.subtle.importKey("raw",enc.encode(password),"PBKDF2",false,["deriveKey"]);
  return crypto.subtle.deriveKey({name:"PBKDF2",salt,iterations:250000,hash:"SHA-256"},material,{name:"AES-GCM",length:256},false,["encrypt","decrypt"]);
}
async function encryptWallet(wallet,password){
  if(password.length<10)throw new Error("Use a local wallet password with at least 10 characters");
  const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12)),key=await vaultKey(password,salt);
  const ciphertext=await crypto.subtle.encrypt({name:"AES-GCM",iv},key,enc.encode(JSON.stringify(wallet)));
  return {format:"crakbit-encrypted-wallet/1",kdf:"PBKDF2-SHA256",iterations:250000,salt:b64(salt),iv:b64(iv),ciphertext:b64(ciphertext)};
}
async function decryptVault(vault,password){
  if(!vault||vault.format!=="crakbit-encrypted-wallet/1")throw new Error("Unsupported encrypted wallet format");
  const salt=fromB64(vault.salt),iv=fromB64(vault.iv),key=await vaultKey(password,salt);
  try{const plaintext=await crypto.subtle.decrypt({name:"AES-GCM",iv},key,fromB64(vault.ciphertext));return validateWallet(JSON.parse(dec.decode(plaintext)));}catch{throw new Error("Could not decrypt wallet. Check the password and backup file.");}
}
async function saveWallet(wallet,password){const vault=await encryptWallet(await validateWallet(wallet),password);localStorage.setItem(VAULT_KEY,JSON.stringify(vault));activeWallet=wallet;await showWallet();}
async function unlockWallet(){const raw=localStorage.getItem(VAULT_KEY);if(!raw)throw new Error("No encrypted wallet is stored in this browser");activeWallet=await decryptVault(JSON.parse(raw),$("walletPassword").value);await showWallet();toast("Wallet unlocked");}
function lockWallet(){activeWallet=null;walletAccount=null;$("walletAddress").textContent="No wallet unlocked";$("walletBalance").textContent="—";$("walletNonce").textContent="Nonce —";$("metricBalance").textContent="Locked";$("metricAddress").textContent="No local wallet";$("walletActivity").innerHTML="";toast("Wallet locked");}
async function showWallet(){
  if(!activeWallet)return;$("walletAddress").textContent=activeWallet.address;$("metricAddress").textContent=short(activeWallet.address,9);await refreshWallet();
}
async function refreshWallet(){
  if(!activeWallet||!network)return;const data=await api(`/api/account/${activeWallet.address}?limit=50`);walletAccount=data.account||data;
  const formatted=formatAtomic(walletAccount.balance,network.decimals);$("walletBalance").textContent=formatted;$("walletNonce").textContent=`Nonce ${walletAccount.nonce??0}`;$("metricBalance").textContent=`${formatted} ${network.symbol}`;
  const activity=data.activity||[];$("walletActivity").innerHTML=activity.map((t)=>{const cp=t.direction==="out"?t.recipient:t.sender;return `<tr><td>${esc(t.height)}</td><td>${esc(t.direction)}</td><td>${esc(formatAtomic(t.amount,network.decimals))} ${esc(network.symbol)}</td><td><code>${esc(short(cp,8))}</code></td><td><code>${esc(short(t.txid,8))}</code></td></tr>`}).join("")||`<tr><td colspan="5">No activity returned.</td></tr>`;
}
async function privateSigningKey(wallet){const seed=fromB64(wallet.private_key);return crypto.subtle.importKey("pkcs8",concatBytes(PKCS8_PREFIX,seed),{name:"Ed25519"},false,["sign"]);}
async function signTransaction(unsigned){const key=await privateSigningKey(activeWallet);const signature=await crypto.subtle.sign("Ed25519",key,enc.encode(stableStringify(unsigned)));return b64(signature);}
async function sendTransaction(){
  if(!activeWallet)throw new Error("Unlock a wallet first");if(!network)throw new Error("Network is not ready");
  const recipient=$("sendRecipient").value.trim().toLowerCase();if(!validAddress(recipient))throw new Error("Recipient is not a valid crk1 address");
  const amount=decimalToAtomic($("sendAmount").value,network.decimals);if(amount<=0n)throw new Error("Amount must be greater than zero");
  const accountData=await api(`/api/account/${activeWallet.address}?limit=1`);const account=accountData.account||accountData;const fee=BigInt(network.min_fee_atomic||0);if(BigInt(account.balance||0)<amount+fee)throw new Error("Insufficient wallet balance including fee");
  const unsigned={chain_id:network.chain_id,sender:activeWallet.address,recipient,amount:Number(amount),fee:Number(fee),nonce:Number(account.nonce||0)+1,public_key:activeWallet.public_key,memo:$("sendMemo").value.trim()};
  const transaction={...unsigned,signature:await signTransaction(unsigned)};const result=await api("/api/transactions",{method:"POST",body:JSON.stringify({transaction})});
  $("sendResult").textContent=JSON.stringify(result,null,2);toast("Transaction accepted by gateway");setTimeout(()=>refreshWallet().catch(()=>{}),1600);
}

async function createNewWallet(){const password=$("walletPassword").value;const wallet=await generateWallet();await saveWallet(wallet,password);toast("New wallet created and encrypted locally");}
async function importWalletFile(file){
  const password=$("walletPassword").value;if(password.length<10)throw new Error("Enter a local password with at least 10 characters before importing");
  const parsed=JSON.parse(await file.text());if(parsed.format==="crakbit-encrypted-wallet/1"){const wallet=await decryptVault(parsed,password);localStorage.setItem(VAULT_KEY,JSON.stringify(parsed));activeWallet=wallet;await showWallet();toast("Encrypted wallet backup imported");return;}
  await saveWallet(await validateWallet(parsed),password);toast("Wallet key imported and encrypted locally");
}
function exportVault(){const raw=localStorage.getItem(VAULT_KEY);if(!raw)throw new Error("No encrypted wallet is stored");const blob=new Blob([raw+"\n"],{type:"application/json"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=`crakbit-wallet-vault-${Date.now()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

async function lookupAddress(){const address=$("explorerAddress").value.trim().toLowerCase();if(!validAddress(address))throw new Error("Enter a valid crk1 address");$("explorerResult").textContent=JSON.stringify(await api(`/api/account/${address}?limit=100`),null,2);}
async function lookupTx(){const txid=$("explorerTx").value.trim();if(!/^[0-9a-fA-F]{64}$/.test(txid))throw new Error("Transaction ID must be 64 hexadecimal characters");$("explorerResult").textContent=JSON.stringify(await api(`/api/transactions/${txid}`),null,2);}

async function refreshValidators(){
  const data=await api("/api/validators");let items=[];
  if(Array.isArray(data.validators))items=data.validators;
  else if(Array.isArray(data.configured_validators))items=data.configured_validators;
  $("validatorsView").innerHTML=items.map((v,i)=>`<div class="validator-card"><strong>${esc(v.name||`Validator ${i+1}`)}</strong><small>${esc(v.peer_url||data.mode||"configured")}</small><code>${esc(v.address||v.public_key||"—")}</code></div>`).join("")||`<pre class="result">${esc(JSON.stringify(data,null,2))}</pre>`;
}

async function sha256HexText(text){return bytesToHex(await crypto.subtle.digest("SHA-256",enc.encode(text)));}
async function requestMiningChallenge(){if(!activeWallet)throw new Error("Unlock a wallet before mining");return api(`/api/mining/challenge?address=${encodeURIComponent(activeWallet.address)}`);}
async function mine(){
  if(miningActive)return;if(!services?.mining)throw new Error("Mining Lab service is not configured on this gateway");if(!activeWallet)throw new Error("Unlock a wallet first");
  miningActive=true;$("miningResult").textContent="Requesting challenge…";
  try{
    const c=miningChallenge=await requestMiningChallenge();$("miningDifficulty").textContent=`${c.difficulty_bits} bits`;$("miningReward").textContent=`${formatAtomic(c.reward_atomic,network.decimals)} ${network.symbol}`;$("miningExpiry").textContent=new Date(c.expires_at_ms).toLocaleTimeString();
    const target=1n<<BigInt(256-Number(c.difficulty_bits));let nonce=0;let hashes=0;let rateStart=performance.now();let rateHashes=0;const batchSize=128;
    $("miningResult").textContent=`Challenge ${c.challenge_id}\nMining is opt-in browser CPU work; this is not block production.`;
    while(miningActive&&Date.now()<Number(c.expires_at_ms)){
      const jobs=[];for(let i=0;i<batchSize;i++){const n=nonce+i;jobs.push(sha256HexText(`${c.challenge_id}:${activeWallet.address.toLowerCase()}:${c.seed}:${n}`).then((digest)=>({n,digest})));}
      const results=await Promise.all(jobs);hashes+=results.length;rateHashes+=results.length;const found=results.find((r)=>BigInt(`0x${r.digest}`)<target);
      nonce+=batchSize;$("miningNonce").textContent=nonce.toLocaleString();
      const elapsed=performance.now()-rateStart;if(elapsed>=1000){const rate=Math.round(rateHashes/(elapsed/1000));$("hashrate").textContent=`${rate.toLocaleString()} H/s`;$("miningProgress").textContent=`${hashes.toLocaleString()} hashes · challenge ${short(c.challenge_id,6)}`;rateStart=performance.now();rateHashes=0;}
      if(found){miningActive=false;$("miningProgress").textContent=`Valid work found at nonce ${found.n.toLocaleString()}`;const result=await api("/api/mining/submit",{method:"POST",body:JSON.stringify({address:activeWallet.address,challenge_id:c.challenge_id,nonce:found.n})});$("miningResult").textContent=JSON.stringify(result,null,2);toast("Valid work submitted; testnet reward transaction created");setTimeout(()=>refreshWallet().catch(()=>{}),1800);return;}
      await new Promise((resolve)=>setTimeout(resolve,0));
    }
    if(Date.now()>=Number(c.expires_at_ms))throw new Error("Mining challenge expired before a solution was found");$("miningProgress").textContent="Stopped";
  }catch(e){$("miningResult").textContent=String(e.message||e);toast(String(e.message||e),"error");}finally{miningActive=false;}
}
function stopMining(){miningActive=false;$("miningProgress").textContent="Stopping…";}

function navigate(page){document.querySelectorAll(".nav-item").forEach((b)=>b.classList.toggle("active",b.dataset.page===page));document.querySelectorAll(".page").forEach((p)=>p.classList.toggle("active",p.id===`page-${page}`));const meta=PAGE_META[page]||PAGE_META.overview;$("pageTitle").textContent=meta[0];$("pageSubtitle").textContent=meta[1];}
async function safe(fn){try{await fn();}catch(e){toast(String(e.message||e),"error");}}
async function refreshAll(){await refreshNetwork();await Promise.allSettled([refreshBlocks(),refreshValidators()]);if(activeWallet)await refreshWallet();}

function bind(){
  document.querySelectorAll(".nav-item").forEach((b)=>b.addEventListener("click",()=>navigate(b.dataset.page)));
  $("refreshAll").onclick=()=>safe(refreshAll);$("overviewBlocksRefresh").onclick=()=>safe(refreshBlocks);$("explorerRefresh").onclick=()=>safe(refreshBlocks);$("validatorsRefresh").onclick=()=>safe(refreshValidators);$("walletRefresh").onclick=()=>safe(refreshWallet);
  $("createWallet").onclick=()=>safe(createNewWallet);$("unlockWallet").onclick=()=>safe(unlockWallet);$("lockWallet").onclick=lockWallet;$("exportVault").onclick=()=>safe(async()=>exportVault());
  $("importWallet").addEventListener("change",(e)=>{const file=e.target.files?.[0];if(file)safe(()=>importWalletFile(file));e.target.value="";});
  $("sendTransaction").onclick=()=>safe(sendTransaction);$("lookupAddress").onclick=()=>safe(lookupAddress);$("lookupTx").onclick=()=>safe(lookupTx);$("startMining").onclick=()=>safe(mine);$("stopMining").onclick=stopMining;
  $("forgetWallet").onclick=()=>{if(confirm("Forget the encrypted local Crakbit wallet vault from this browser? Keep an encrypted backup first if needed.")){localStorage.removeItem(VAULT_KEY);lockWallet();toast("Local encrypted wallet vault forgotten");}};
}

(async()=>{bind();try{await refreshAll();if(localStorage.getItem(VAULT_KEY))$("sendResult").textContent="Encrypted wallet found. Enter your local password and unlock it.";}catch(e){toast(`Gateway connection failed: ${e.message||e}`,"error");$("networkBadge").textContent="Gateway offline";}})();
