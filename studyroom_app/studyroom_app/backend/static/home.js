const msg = document.getElementById("msg");
const signupMsg = document.getElementById("signup_msg");
const meta = document.getElementById("meta");
const tbody = document.querySelector("#table tbody");
const rangeSel = document.getElementById("range");

function showMsg(el, text, danger=false){
  el.textContent = text;
  el.classList.remove("muted");
  el.style.color = danger ? "#b91c1c" : "var(--text)"; // still monochrome-ish (dark red only when error)
  if (!danger) el.style.color = "var(--text)";
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
  meta.textContent = `在室 ${data.occupancy}人 / 上位表示`;
  data.items.forEach((it, idx)=>{
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${idx+1}</td><td>${it.nickname}</td><td>${fmt(it.total_sec)}</td>`;
    tbody.appendChild(tr);
  });
}


// --- 入力補助・整形 ---
const studentInput = document.getElementById("student");
const pinInput = document.getElementById("pin");

// 学籍番号自動整形（大文字化・全角→半角・空白除去）
studentInput.addEventListener("input", e => {
  let v = studentInput.value;
  v = v.replace(/[Ａ-Ｚａ-ｚ０-９]/g, s => String.fromCharCode(s.charCodeAt(0) - 0xFEE0)); // 全角→半角
  v = v.toUpperCase().replace(/[^A-Z0-9]/g, "");
  studentInput.value = v;
});

// PIN入力後自動クリア
pinInput.addEventListener("input", e => {
  if(pinInput.value.length >= 4) setTimeout(()=>{ pinInput.value = ""; }, 1000);
});

// 前回値保持・ワンクリック呼び出し
const LAST_KEY = "studyroom_last_student";
studentInput.addEventListener("change", ()=>{
  if(studentInput.value.length >= 6) localStorage.setItem(LAST_KEY, studentInput.value);
});
const recallBtn = document.createElement("button");
recallBtn.textContent = "前回入力を呼び出し";
recallBtn.className = "btn btn-outline btn-sm";
recallBtn.style.marginLeft = "8px";
studentInput.parentNode.appendChild(recallBtn);
recallBtn.addEventListener("click", ()=>{
  const v = localStorage.getItem(LAST_KEY)||"";
  if(v) studentInput.value = v;
  studentInput.focus();
});

// 入室中状態表示・ガード
let isIn = false;
async function checkStatus(student_no, pin) {
  // APIで入室中か確認
  try {
    const res = await fetch("/api/status", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({student_no, pin})
    });
    const data = await res.json().catch(()=>({}));
    if(res.ok && data.status === "in") return true;
  } catch {}
  return false;
}

async function doCheck(kind){
  showMsg(msg, "通信中…");
  try{
    const student_no = studentInput.value.trim();
    const pin = pinInput.value.trim();
    // 入室時は入室中なら退室を促す
    if(kind==="in"){
      if(await checkStatus(student_no, pin)){
        showMsg(msg, "すでに入室中です。退室を先に行ってください。", true);
        return;
      }
    }
    // 退室時は未入室ならガード
    if(kind==="out"){
      if(!(await checkStatus(student_no, pin))){
        showMsg(msg, "入室記録がありません。先に入室してください。", true);
        return;
      }
    }
    const url = kind === "in" ? "/api/checkin" : "/api/checkout";
    const data = await post(url, {student_no, pin});
    showMsg(msg, data.message);
    pinInput.value = "";
    await loadLeaderboard();
  }catch(e){
    showMsg(msg, e.message, true);
  }
}

async function doSignup(){
  showMsg(signupMsg, "通信中…");
  try{
    const student_no = document.getElementById("su_student").value.trim();
    const name = document.getElementById("su_name").value.trim();
    const nickname = document.getElementById("su_nick").value.trim();
    const pin = document.getElementById("su_pin").value.trim();
    const signup_code = (document.getElementById("su_code")?.value || "").trim() || null;

    await post("/api/signup", {student_no, name, nickname, pin, signup_code});
    showMsg(signupMsg, "登録しました。すぐ下の入退室で使えます。");
    // clear
    document.getElementById("su_pin").value = "";
    await loadLeaderboard();
  }catch(e){
    showMsg(signupMsg, e.message, true);
  }
}

document.getElementById("btn_in").addEventListener("click", ()=>doCheck("in"));
document.getElementById("btn_out").addEventListener("click", ()=>doCheck("out"));
document.getElementById("btn_signup").addEventListener("click", doSignup);

document.getElementById("refresh").addEventListener("click", loadLeaderboard);
rangeSel.addEventListener("change", loadLeaderboard);

loadLeaderboard();
setInterval(loadLeaderboard, 30_000);
