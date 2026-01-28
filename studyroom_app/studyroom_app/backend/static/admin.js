async function refreshActive(){
  const tbody = document.querySelector("#active_table tbody");
  const msg = document.getElementById("active_msg");
  tbody.innerHTML = "";
  msg.textContent = "通信中…";
  try{
    const data = await get("/api/admin/active_sessions");
    data.sessions.forEach(s => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${s.student_no}</td><td>${s.name}</td><td>${s.nickname}</td><td>${s.checkin_at.replace('T',' ').slice(0,16)}</td>`;
      tbody.appendChild(tr);
    });
    msg.textContent = `現在入室中: ${data.sessions.length}人`;
  }catch(e){
    msg.textContent = e.message;
  }
}

document.getElementById("refresh_active").addEventListener("click", refreshActive);

document.getElementById("force_checkout_all").addEventListener("click", async ()=>{
  const msg = document.getElementById("active_msg");
  msg.textContent = "通信中…";
  try{
    const data = await post("/api/admin/force_checkout_all", {});
    msg.textContent = `全員強制退室しました（${data.count}件）`;
    await refreshActive();
  }catch(e){
    msg.textContent = e.message;
  }
});
const loginCard = document.getElementById("login_card");
const adminArea = document.getElementById("admin_area");

const loginMsg = document.getElementById("login_msg");
const createMsg = document.getElementById("create_msg");
const resetMsg = document.getElementById("reset_msg");
const forceMsg = document.getElementById("force_msg");

async function post(url, payload){
  const res = await fetch(url, {
    method:"POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data.detail ?? "エラー");
  return data;
}
async function get(url){
  const res = await fetch(url);
  const data = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data.detail ?? "エラー");
  return data;
}

async function refreshUsers(){
  const tbody = document.querySelector("#users_table tbody");
  tbody.innerHTML = "";
  const data = await get("/api/admin/users");
  data.users.forEach(u=>{
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${u.id}</td><td>${u.student_no}</td><td>${u.name}</td><td>${u.nickname}</td><td>${u.created_at}</td>`;
    tbody.appendChild(tr);
  });
}

document.getElementById("admin_login").addEventListener("click", async ()=>{
  loginMsg.textContent = "通信中…";
  try{
    const password = document.getElementById("admin_pw").value.trim();
    await post("/api/admin/login", {password});
    loginCard.style.display = "none";
    adminArea.style.display = "block";
    loginMsg.textContent = "";
    await refreshUsers();
  }catch(e){
    loginMsg.textContent = e.message;
  }
});

document.getElementById("create_user").addEventListener("click", async ()=>{
  createMsg.textContent = "通信中…";
  try{
    const student_no = document.getElementById("c_student").value.trim();
    const name = document.getElementById("c_name").value.trim();
    const nickname = document.getElementById("c_nick").value.trim();
    const pin = document.getElementById("c_pin").value.trim();
    await post("/api/admin/create_user", {student_no, name, nickname, pin});
    createMsg.textContent = "追加しました";
    await refreshUsers();
  }catch(e){
    createMsg.textContent = e.message;
  }
});

document.getElementById("reset_pin").addEventListener("click", async ()=>{
  resetMsg.textContent = "通信中…";
  try{
    const student_no = document.getElementById("r_student").value.trim();
    const new_pin = document.getElementById("r_pin").value.trim();
    await post("/api/admin/reset_pin", {student_no, new_pin});
    resetMsg.textContent = "再発行しました";
  }catch(e){
    resetMsg.textContent = e.message;
  }
});

document.getElementById("force_checkout").addEventListener("click", async ()=>{
  forceMsg.textContent = "通信中…";
  try{
    const student_no = document.getElementById("f_student").value.trim();
    const data = await post("/api/admin/force_checkout", {student_no});
    forceMsg.textContent = `強制退室しました（${Math.floor(data.duration_sec/60)}分）`;
  }catch(e){
    forceMsg.textContent = e.message;
  }
});

document.getElementById("refresh_users").addEventListener("click", async ()=>{
  try{ await refreshUsers(); }catch(e){ alert(e.message); }
});
