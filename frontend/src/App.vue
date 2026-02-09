<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { createClient } from 'genlayer-js';
import { localnet, studionet } from 'genlayer-js/chains';

const IS_LOCAL = import.meta.env.DEV; 
const CHAIN = IS_LOCAL ? localnet : studionet;
const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS;

// STATE
const account = ref<string | null>(null);
const gameState = ref("IDLE");
const currentQ = ref<any>(null);
const resultData = ref<any>(null); 
const myData = ref({ xp: 0, username: "Anon" });
const leaderboard = ref<any[]>([]);
const logMsg = ref("SYSTEM READY.");
const loading = ref(false);
const showNameModal = ref(false);
const newName = ref("");

// Client setup with explicit casting
let client = createClient({ chain: CHAIN });

// --- SOUNDS ---
const playSound = (type: 'hover'|'click'|'win'|'lose') => {
  const win = window as any;
  const AudioContext = win.AudioContext || win.webkitAudioContext;
  if (!AudioContext) return;
  
  const ctx = new AudioContext();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  
  const now = ctx.currentTime;
  if(type==='click'){
    osc.frequency.setValueAtTime(600, now);
    osc.frequency.exponentialRampToValueAtTime(300, now + 0.1);
    gain.gain.setValueAtTime(0.1, now);
    osc.start(); osc.stop(now + 0.1);
  } else if(type==='win') {
    osc.type = 'square';
    osc.frequency.setValueAtTime(400, now);
    osc.frequency.linearRampToValueAtTime(800, now + 0.1);
    gain.gain.value = 0.1;
    osc.start(); osc.stop(now + 0.3);
  } else if(type==='lose') {
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(200, now);
    osc.frequency.linearRampToValueAtTime(50, now + 0.5);
    gain.gain.value = 0.2;
    osc.start(); osc.stop(now + 0.5);
  }
};

const connect = async () => {
  // Fix TS2339: Cast window to any
  const win = window as any;
  if (!win.ethereum) return alert("Install MetaMask");
  
  try {
    const accounts = await win.ethereum.request({ method: 'eth_requestAccounts' });
    account.value = accounts[0];
    
    // Fix TS2322: Cast account string to any
    client = createClient({ chain: CHAIN, account: account.value as any });
    refresh();
  } catch (e) { alert("Connection Error"); }
};

const refresh = async () => {
  if (!CONTRACT_ADDRESS || !account.value) return;
  try {
    // Fix TS2345: Cast account to string explicitly in args
    const qRaw = await client.readContract({ 
      address: CONTRACT_ADDRESS, 
      functionName: 'get_current_state', 
      args: [account.value as string] 
    }) as string;
    
    const qData = JSON.parse(qRaw);

    if (qData.status === "IDLE") gameState.value = "IDLE";
    else if (qData.status === "WAITING") gameState.value = "WAITING";
    else if (qData.status === "FINISHED") {
      gameState.value = "FINISHED";
      resultData.value = qData;
    } else if (qData.status === "PLAYING") {
      gameState.value = "PLAYING";
      currentQ.value = qData; 
    }

    // Fix TS18047/TS2339: Cast result to any
    const pd = await client.readContract({ 
      address: CONTRACT_ADDRESS, 
      functionName: 'get_player_data', 
      args: [account.value as string] 
    }) as any;
    myData.value = { xp: Number(pd.xp), username: pd.username };

    // Fix TS18047/TS2339: Cast result to any array
    const lb = await client.readContract({ 
      address: CONTRACT_ADDRESS, 
      functionName: 'get_leaderboard', 
      args: [] 
    }) as any[];
    
    leaderboard.value = lb.sort((a:any, b:any) => Number(b.xp) - Number(a.xp)).slice(0, 10);
  } catch(e) { console.error(e); }
};

const sendTx = async (method: string, args: any[]) => {
  if (!account.value) return;
  playSound('click');
  loading.value = true;
  logMsg.value = "SUBMITTING...";
  
  try {
    const hash = await client.writeContract({ address: CONTRACT_ADDRESS, functionName: method, args, value: 0n });
    logMsg.value = "VERIFYING ANSWER...";
    
    // Fix TS2322: Cast status string to any to bypass Enum check
    await client.waitForTransactionReceipt({ hash, status: 'ACCEPTED' as any });
    
    await refresh();
    if(gameState.value === 'FINISHED') {
        playSound(resultData.value.result === 'VICTORY' ? 'win' : 'lose');
        logMsg.value = resultData.value.result;
    } else {
        playSound('win');
        logMsg.value = "CORRECT! NEXT QUESTION...";
    }
    showNameModal.value = false;
  } catch(e:any) {
    logMsg.value = "ERROR: " + e.message;
    playSound('lose');
  } finally {
    loading.value = false;
  }
};

setInterval(refresh, 2000);
onMounted(refresh);
</script>

<template>
  <div class="interface">
    <div class="scanline"></div>
    
    <header>
      <div class="logo">GENLAYER TRIVIA</div>
      <div v-if="account" class="stats" @click="showNameModal = true">
        <span>{{ myData.username }}</span>
        <span class="xp">{{ myData.xp }} XP</span>
      </div>
      <button v-else @click="connect" class="btn connect">CONNECT</button>
    </header>

    <div class="content">
      
      <div v-if="gameState === 'IDLE'" class="menu">
        <h1>BATTLE MODE</h1>
        <div class="grid">
          <div class="card" @click="sendTx('start_single_player', [])">
            <h2>SOLO RUN</h2>
            <p>Answer 5 in a row.</p>
          </div>
          <div class="card multi" @click="sendTx('join_multiplayer', [])">
            <h2>VERSUS</h2>
            <p>Challenge opponent.</p>
          </div>
        </div>
      </div>

      <div v-if="gameState === 'WAITING'" class="lobby">
        <div class="spinner"></div>
        <h2>SEARCHING LOBBY...</h2>
      </div>

      <div v-if="gameState === 'PLAYING' && currentQ" class="game">
        <div class="progress">QUESTION {{ currentQ.streak }} / 5</div>
        <div class="question-box">{{ currentQ.q }}</div>
        <div class="options">
          <button v-for="opt in currentQ.opts" :key="opt" 
                  @click="sendTx('submit_answer', [opt.charAt(0)])"
                  :disabled="loading"
                  class="btn option">
            {{ opt }}
          </button>
        </div>
      </div>

      <div v-if="gameState === 'FINISHED' && resultData" class="result">
        <h1 :class="resultData.result">
          {{ resultData.result === 'VICTORY' ? 'MISSION ACCOMPLISHED' : 'MISSION FAILED' }}
        </h1>
        <p>STREAK: {{ resultData.streak }} / 5</p>
        <p class="xp-gain">+{{ resultData.streak * 10 }} XP EARNED</p>
        <div class="grid">
          <button @click="sendTx('start_single_player', [])" class="btn">RETRY</button>
        </div>
      </div>

      <div class="logs">> {{ logMsg }}<span class="blink">_</span></div>
    </div>

    <div class="sidebar">
      <h3>LEADERBOARD</h3>
      <div v-for="(p, i) in leaderboard" :key="p.address" class="row" :class="{ me: p.address.toLowerCase() === account?.toLowerCase() }">
        <span>#{{ i+1 }} {{ p.username }}</span>
        <span class="score">{{ p.xp }}</span>
      </div>
    </div>

    <div v-if="showNameModal" class="modal-bg">
      <div class="modal">
        <h3>CALLSIGN</h3>
        <input v-model="newName" />
        <button @click="sendTx('set_username', [newName])" class="btn">SAVE</button>
        <button @click="showNameModal = false" class="btn cancel">X</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto+Mono&display=swap');

.interface {
  font-family: 'Orbitron', sans-serif;
  background: radial-gradient(circle at center, #1b2735 0%, #090a0f 100%);
  color: #fff;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 250px;
  grid-template-rows: 80px 1fr;
  overflow: hidden;
}

.scanline {
  position: absolute; top: 0; left: 0; width: 100%; height: 5px;
  background: rgba(0, 255, 255, 0.3);
  animation: scan 3s linear infinite; pointer-events: none; z-index: 10;
}
@keyframes scan { 0% { top: -5%; } 100% { top: 105%; } }

header {
  grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center;
  padding: 0 40px; border-bottom: 2px solid #00d2ff; background: rgba(0,0,0,0.5); z-index: 5;
}
.logo { font-size: 24px; font-weight: 700; color: #00d2ff; text-shadow: 0 0 10px #00d2ff; }
.stats { border: 1px solid #00d2ff; padding: 10px 20px; border-radius: 4px; cursor: pointer; display: flex; gap: 20px; }
.xp { color: #f0f; text-shadow: 0 0 5px #f0f; }

.content { padding: 40px; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; }

.progress { color: #00d2ff; margin-bottom: 10px; font-size: 1.2rem; }
.grid { display: flex; gap: 20px; margin-top: 30px; }
.card { width: 250px; padding: 40px; border: 1px solid #444; background: rgba(255,255,255,0.05); text-align: center; cursor: pointer; transition: 0.3s; }
.card:hover { border-color: #00d2ff; transform: scale(1.05); box-shadow: 0 0 20px rgba(0, 210, 255, 0.3); }

.question-box {
  font-family: 'Roboto Mono'; background: #000; border: 1px solid #fff;
  padding: 30px; width: 100%; max-width: 600px; text-align: center;
  margin-bottom: 30px; box-shadow: 5px 5px 0px #00d2ff; font-size: 1.2rem;
}
.options { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; width: 100%; max-width: 600px; }

.btn {
  background: #00d2ff; color: #000; border: none; padding: 15px 30px;
  font-family: 'Orbitron'; font-weight: bold; cursor: pointer; transition: 0.2s;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
}
.btn:hover:not(:disabled) { background: #fff; box-shadow: 0 0 20px #fff; }
.btn.option { background: #111; color: #fff; border: 1px solid #666; text-align: left; }
.btn.option:hover:not(:disabled) { background: #fff; color: #000; }

.VICTORY { color: #0f0; text-shadow: 0 0 20px #0f0; font-size: 2.5rem; }
.GAME_OVER { color: #f00; text-shadow: 0 0 20px #f00; font-size: 2.5rem; }
.xp-gain { color: #f0f; font-size: 1.5rem; margin-top: 10px; }

.sidebar { border-left: 1px solid #333; padding: 20px; background: rgba(0,0,0,0.2); }
.row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #222; font-family: 'Roboto Mono'; }
.row.me { color: #00d2ff; }

.logs { position: absolute; bottom: 20px; left: 20px; color: #00d2ff; font-family: 'Roboto Mono'; font-size: 12px; }
.blink { animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0; } }

.spinner { width: 50px; height: 50px; border: 5px solid #333; border-top: 5px solid #00d2ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.modal-bg { position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; z-index: 20; backdrop-filter: blur(5px); }
.modal { background: #000; border: 2px solid #00d2ff; padding: 40px; text-align: center; }
input { background: #111; border: 1px solid #444; padding: 10px; color: #fff; margin: 20px 0; width: 100%; font-family: 'Roboto Mono'; }

@media (max-width: 800px) { .interface { grid-template-columns: 1fr; grid-template-rows: auto 1fr auto; } .sidebar { border-top: 1px solid #333; border-left: none; } }
</style>