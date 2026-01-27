const msg = document.getElementById("msg");
const meta = document.getElementById("meta");
const tbody = document.querySelector("#table tbody");
const rangeSel = document.getElementById("range");

function show(text, danger=false){
  msg.textContent = text;
  msg.classList.remove("muted");
  msg.style.color = danger ? "var(--danger)" : "var(--text)";
}

function fmt(sec){
  sec = Number(sec||0);
  const h = Math.floor(sec/3600);
  const m = Math.floor((sec%3600)/60);
  if(h<=0) return `${m}分`;
  return `${h}時間${m}分`;
}

async function post(url, payload){
  const res = await fetch(url, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data.detail ?? "エラー");
  return data;
}

async function loadLeaderboard(){
  tbody.innerHTML = "";
  meta.textContent = "通信中…";
  const range = rangeSel.value;
  const res = await fetch(`/api/leaderboard?range=${encodeURIComponent(range)}&top=15`);
  const data = await res.json().catch(()=>({}));
  if(!res.ok){
    meta.textContent = data.detail ?? "エラー";
    return;
  }
  meta.textContent = `在室 ${data.occupancy}人 / ${range === "today" ? "今日" : range === "week" ? "今週" : "今月"} 上位`;
  data.items.forEach((it, idx)=>{
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${idx+1}</td><td>${it.nickname}</td><td>${fmt(it.total_sec)}</td>`;
    tbody.appendChild(tr);
  });
}

async function doCheck(kind){
  show("通信中…");
  try{
    const student_no = document.getElementById("student").value.trim();
    const pin = document.getElementById("pin").value.trim();
    const url = kind === "in" ? "/api/checkin" : "/api/checkout";
    const data = await post(url, {student_no, pin});
    show(data.message);
    await loadLeaderboard();
  }catch(e){
    show(e.message, true);
  }
}

document.getElementById("btn_in").addEventListener("click", ()=>doCheck("in"));
document.getElementById("btn_out").addEventListener("click", ()=>doCheck("out"));
document.getElementById("refresh").addEventListener("click", loadLeaderboard);
rangeSel.addEventListener("change", loadLeaderboard);

loadLeaderboard();
setInterval(loadLeaderboard, 30_000);
