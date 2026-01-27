const msg = document.getElementById("msg");

function show(text, danger=false){
  msg.textContent = text;
  msg.classList.remove("muted");
  msg.style.color = danger ? "var(--danger)" : "var(--text)";
}

async function post(url, payload){
  const res = await fetch(url, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(()=>({}));
  if(!res.ok){
    throw new Error(data.detail ?? "エラー");
  }
  return data;
}

document.getElementById("btn_in").addEventListener("click", async ()=>{
  show("通信中…");
  try{
    const student_no = document.getElementById("in_student").value.trim();
    const pin = document.getElementById("in_pin").value.trim();
    const data = await post("/api/checkin", {student_no, pin});
    show(data.message);
  }catch(e){
    show(e.message, true);
  }
});

document.getElementById("btn_out").addEventListener("click", async ()=>{
  show("通信中…");
  try{
    const student_no = document.getElementById("out_student").value.trim();
    const pin = document.getElementById("out_pin").value.trim();
    const data = await post("/api/checkout", {student_no, pin});
    show(data.message);
  }catch(e){
    show(e.message, true);
  }
});
