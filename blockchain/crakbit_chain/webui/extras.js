"use strict";

async function requestFaucetCoins(){
  if(!activeWallet)throw new Error("Unlock a wallet before requesting test coins");
  if(!services?.faucet)throw new Error("Testnet faucet is not configured on this gateway");
  const result=await api("/api/faucet/request",{
    method:"POST",
    body:JSON.stringify({address:activeWallet.address})
  });
  $("sendResult").textContent=JSON.stringify(result,null,2);
  toast("Testnet faucet transaction submitted");
  setTimeout(()=>refreshWallet().catch(()=>{}),1800);
}

const faucetButton=$("requestFaucet");
if(faucetButton)faucetButton.onclick=()=>safe(requestFaucetCoins);
