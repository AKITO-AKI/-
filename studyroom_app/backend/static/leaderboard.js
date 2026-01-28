
const rangeSel = document.getElementById("range");
const viewmodeSel = document.getElementById("viewmode");
const anonmodeChk = document.getElementById("anonmode");
const meta = document.getElementById("meta");
const tbody = document.querySelector("#table tbody");

function fmt(sec){
  sec = Number(sec||0);
  const h = Math.floor(sec/3600);
  const m = Math.floor((sec%3600)/60);
  if(h<=0) return `${m}分`;
  return `${h}時間${m}分`;
}


async function load(){
  tbody.innerHTML = "";
  meta.textContent = "通信中…";
  const range = rangeSel.value;
  const viewmode = viewmodeSel.value;
  const anon = anonmodeChk.checked;
  // APIパラメータ拡張（必要に応じてバックエンドも対応）
  const res = await fetch(`/api/leaderboard?range=${encodeURIComponent(range)}&top=${viewmode==='top'?50:1000}`);
  const data = await res.json().catch(()=>({}));
  if(!res.ok){
    meta.textContent = data.detail ?? "エラー";
    return;
  }
  meta.textContent = `在室 ${data.occupancy}人 / ユーザー ${data.total_users}人`;
  let items = data.items || [];
  if(viewmode==='top') items = items.slice(0, 10); // 上位のみ
  // 匿名モード
  items.forEach((it, idx)=>{
    const tr = document.createElement("tr");
    let name = it.nickname;
    if(anon) name = `ユーザー${it.id || idx+1}`;
    tr.innerHTML = `<td>${idx+1}</td><td>${name}</td><td>${fmt(it.total_sec)}</td>`;
    tbody.appendChild(tr);
  });
}


document.getElementById("refresh").addEventListener("click", load);
rangeSel.addEventListener("change", load);
viewmodeSel.addEventListener("change", load);
anonmodeChk.addEventListener("change", load);

load();
setInterval(load, 30_000);
