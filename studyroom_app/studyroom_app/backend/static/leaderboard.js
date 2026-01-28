
const rangeSel = document.getElementById("range");
const viewSel = document.getElementById("viewmode");
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
  const view = viewSel.value;
  let top = 50;
  if(view === "top") top = 15;
  if(view === "all") top = 100;
  if(view === "anon") top = 100;
  const res = await fetch(`/api/leaderboard?range=${encodeURIComponent(range)}&top=${top}`);
  const data = await res.json().catch(()=>({}));
  if(!res.ok){
    meta.textContent = data.detail ?? "エラー";
    return;
  }
  meta.textContent = `在室 ${data.occupancy}人 / ユーザー ${data.total_users}人`;
  data.items.forEach((it, idx)=>{
    const tr = document.createElement("tr");
    let name = it.nickname;
    if(view === "anon") name = "匿名" + (idx+1);
    tr.innerHTML = `<td>${idx+1}</td><td>${name}</td><td>${fmt(it.total_sec)}</td>`;
    tbody.appendChild(tr);
  });
}


document.getElementById("refresh").addEventListener("click", load);
rangeSel.addEventListener("change", load);
viewSel.addEventListener("change", load);

load();
setInterval(load, 30_000);
