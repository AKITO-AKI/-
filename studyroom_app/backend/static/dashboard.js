const title = document.getElementById("title");
const t_today = document.getElementById("t_today");
const t_week = document.getElementById("t_week");
const t_month = document.getElementById("t_month");
const t_all = document.getElementById("t_all");

const r_today = document.getElementById("r_today");
const r_week = document.getElementById("r_week");
const r_month = document.getElementById("r_month");
const r_all = document.getElementById("r_all");

const tbody = document.querySelector("#table tbody");

function fmt(sec){
  sec = Number(sec||0);
  const h = Math.floor(sec/3600);
  const m = Math.floor((sec%3600)/60);
  if(h<=0) return `${m}分`;
  return `${h}時間${m}分`;
}

function drawLineChart(canvas, labels, values, opts={}){
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0,0,w,h);

  const pad = 34;
  const innerW = w - pad*2;
  const innerH = h - pad*2;

  // background
  ctx.fillStyle = "rgba(255,255,255,0.02)";
  ctx.fillRect(0,0,w,h);

  // axes
  ctx.strokeStyle = "rgba(255,255,255,0.18)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad, pad);
  ctx.lineTo(pad, h-pad);
  ctx.lineTo(w-pad, h-pad);
  ctx.stroke();

  const minV = opts.min !== undefined ? opts.min : Math.min(...values);
  const maxV = opts.max !== undefined ? opts.max : Math.max(...values);
  const span = (maxV - minV) || 1;

  function x(i){
    if(values.length === 1) return pad;
    return pad + (innerW * (i/(values.length-1)));
  }
  function y(v){
    const t = (v - minV) / span;
    return (h - pad) - innerH * t;
  }

  // grid lines (3)
  ctx.strokeStyle = "rgba(255,255,255,0.08)";
  for(let i=1;i<=3;i++){
    const gy = pad + (innerH * (i/4));
    ctx.beginPath();
    ctx.moveTo(pad, gy);
    ctx.lineTo(w-pad, gy);
    ctx.stroke();
  }

  // line
  ctx.strokeStyle = "rgba(255,255,255,0.85)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((v,i)=>{
    const px = x(i), py = y(v);
    if(i===0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.stroke();

  // points
  ctx.fillStyle = "rgba(255,255,255,0.9)";
  values.forEach((v,i)=>{
    const px = x(i), py = y(v);
    ctx.beginPath();
    ctx.arc(px, py, 3, 0, Math.PI*2);
    ctx.fill();
  });

  // title
  if(opts.title){
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.font = "14px system-ui, sans-serif";
    ctx.fillText(opts.title, pad, 20);
  }

  // min/max labels
  ctx.fillStyle = "rgba(255,255,255,0.6)";
  ctx.font = "12px system-ui, sans-serif";
  const fmtY = opts.fmtY || ((v)=>String(v));
  ctx.fillText(fmtY(maxV), 6, pad+6);
  ctx.fillText(fmtY(minV), 6, h-pad);

  // x labels (start/end)
  if(labels.length){
    ctx.fillText(labels[0], pad, h-10);
    ctx.fillText(labels[labels.length-1], w-pad-70, h-10);
  }
}

async function load(){
  const res = await fetch("/api/me");
  const data = await res.json().catch(()=>({}));
  if(!res.ok){
    location.href = "/login";
    return;
  }

  title.textContent = `ダッシュボード（${data.user.nickname}）`;

  t_today.textContent = fmt(data.totals.today);
  t_week.textContent = fmt(data.totals.week);
  t_month.textContent = fmt(data.totals.month);
  t_all.textContent = fmt(data.totals.all);

  r_today.textContent = `順位: ${data.ranks.today.rank} / ${data.ranks.today.total_users}`;
  r_week.textContent = `順位: ${data.ranks.week.rank} / ${data.ranks.week.total_users}`;
  r_month.textContent = `順位: ${data.ranks.month.rank} / ${data.ranks.month.total_users}`;
  r_all.textContent = `順位: ${data.ranks.all.rank} / ${data.ranks.all.total_users}`;

  // sessions table
  tbody.innerHTML = "";
  data.sessions.forEach(s=>{
    const tr = document.createElement("tr");
    const st = s.is_active ? "入室中" : "完了";
    const dur = s.is_active ? "—" : fmt(s.duration_sec);
    tr.innerHTML = `<td>${s.checkin_at}</td><td>${s.checkout_at ?? "—"}</td><td>${dur}</td><td>${st}</td>`;
    tbody.appendChild(tr);
  });

  // charts
  const labels = data.daily.map(x=>x.date.slice(5)); // MM-DD
  const secs = data.daily.map(x=>x.sec/60);          // minutes
  const ranks = data.daily.map(x=>x.rank);

  drawLineChart(
    document.getElementById("chart_time"),
    labels, secs,
    {title:"分/日", min:0, fmtY:(v)=>`${Math.round(v)}分`}
  );

  // rank chart: invert so "1位" is high (visually up)
  const maxRank = Math.max(...ranks);
  const inv = ranks.map(r=> (maxRank + 1) - r);
  drawLineChart(
    document.getElementById("chart_rank"),
    labels, inv,
    {title:"順位（上に行くほど良い）", min:0, fmtY:(v)=>""}
  );
}

document.getElementById("logout").addEventListener("click", async (e)=>{
  e.preventDefault();
  await fetch("/api/logout", {method:"POST"});
  location.href = "/";
});

load();
