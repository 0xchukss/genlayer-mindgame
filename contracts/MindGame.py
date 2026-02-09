# { "Depends": "py-genlayer:test" }
from genlayer import *
import json

class MindGame(gl.Contract):
    player_xp: TreeMap[Address, u256]
    player_usernames: TreeMap[Address, str]
    active_games: TreeMap[Address, str] 
    all_players: DynArray[Address] 
    is_registered: TreeMap[Address, bool]
    
    lobby_open: bool
    waiting_player: Address
    nonce: u256

    def __init__(self):
        self.lobby_open = False
        self.waiting_player = Address("0x0000000000000000000000000000000000000000")
        self.nonce = u256(0)

    @gl.public.write
    def set_username(self, name: str):
        sender = gl.message.sender_address
        self.player_usernames[sender] = name
        if not self.is_registered.get(sender, False):
            self.all_players.append(sender)
            self.is_registered[sender] = True

    # --- GAME START ---

    @gl.public.write
    def start_single_player(self):
        self._start_new_game(gl.message.sender_address, "SINGLE")

    @gl.public.write
    def join_multiplayer(self):
        sender = gl.message.sender_address
        if self.lobby_open:
            opponent = self.waiting_player
            if opponent == sender: gl.revert("Already in lobby")
            self.lobby_open = False
            self.waiting_player = Address("0x0000000000000000000000000000000000000000")
            
            self._start_new_game(sender, "MULTI", opponent)
            self._start_new_game(opponent, "MULTI", sender)
        else:
            self.lobby_open = True
            self.waiting_player = sender
            self.active_games[sender] = json.dumps({"status": "WAITING"})

    def _start_new_game(self, player: Address, mode: str, opponent: Address = None):
        first_q = self._get_random_index()
        state = {
            "q_index": first_q,
            "mode": mode,
            "status": "ACTIVE",
            "streak": 0,
            "history": [first_q],
            "opponent": opponent.as_hex if opponent else None
        }
        self.active_games[player] = json.dumps(state)

    def _get_random_index(self) -> int:
        self.nonce += 1
        # Modulo 20 for your 20 new questions
        return abs(hash(str(gl.message.sender_address) + str(self.nonce))) % 20

    @gl.public.write
    def submit_answer(self, choice: str):
        sender = gl.message.sender_address
        game_str = self.active_games.get(sender, "")
        if game_str == "": gl.revert("No game")
        game = json.loads(game_str)
        if game['status'] != "ACTIVE": gl.revert("Not active")

        q_idx = game['q_index']
        correct = self._get_answer_key(q_idx)
        is_correct = (choice.upper() == correct)

        if is_correct:
            cur_xp = self.player_xp.get(sender, 0)
            self.player_xp[sender] = cur_xp + 10
            
            game['streak'] += 1
            
            if game['streak'] >= 5:
                game['status'] = "FINISHED"
                game['last_result'] = "VICTORY"
            else:
                next_q = self._get_next_unique_question(game['history'])
                game['q_index'] = next_q
                game['history'].append(next_q)
                
        else:
            game['status'] = "FINISHED"
            game['last_result'] = "GAME_OVER"

        self.active_games[sender] = json.dumps(game)

    def _get_next_unique_question(self, history: list) -> int:
        for _ in range(10):
            q = self._get_random_index()
            if q not in history: return q
        return (history[-1] + 1) % 20

    # --- UPDATED DATABASE ---
    def _get_answer_key(self, index: int) -> str:
        # 1-5   : B, C, D, B, B
        # 6-10  : C, C, B, B, C
        # 11-15 : B, B, B, B, C
        # 16-20 : C, B, C, B, C
        return ["B", "C", "D", "B", "B", "C", "C", "B", "B", "C", 
                "B", "B", "B", "B", "C", "C", "B", "C", "B", "C"][index]

    def _get_question_text(self, index: int) -> dict:
        qs = [
            {"q": "What is GenLayer's primary goal?", "opts": ["A) Replace lawyers", "B) Trust infra for AI Age", "C) Social crypto", "D) Central AI DB"]},
            {"q": "What are programs on GenLayer called?", "opts": ["A) Smart Scripts", "B) AI Protocols", "C) Intelligent Contracts", "D) Synthetic Agreements"]},
            {"q": "GenVM is based on which language?", "opts": ["A) Solidity", "B) C++", "C) JavaScript", "D) Python"]},
            {"q": "What is GenLayer's consensus mechanism?", "opts": ["A) Proof of Stake", "B) Optimistic Democracy", "C) Proof of Intelligence", "D) Delegated Authority"]},
            {"q": "How does GenVM handle non-deterministic ops?", "opts": ["A) Disallows them", "B) Equivalence Principle", "C) Exact seed matching", "D) User choice"]},
            {"q": "What are the two account types?", "opts": ["A) User/Bot", "B) Private/Public", "C) EOAs & Contracts", "D) Validated/Anon"]},
            {"q": "What happens to unused gas?", "opts": ["A) Burned", "B) Validator bonus", "C) Refunded to user", "D) Donated to DAO"]},
            {"q": "How do contracts access the internet?", "opts": ["A) API keys", "B) http protocol", "C) Manual entry", "D) Google only"]},
            {"q": "Role of the Leader in consensus?", "opts": ["A) Pay gas", "B) Propose execution", "C) Allow validators", "D) Write code"]},
            {"q": "Purpose of Finality Window?", "opts": ["A) LLM thinking time", "B) Cancel tx", "C) Appeal period", "D) Price stabilization"]},
            {"q": "What does Grayboxing protect against?", "opts": ["A) High costs", "B) Prompt injections", "C) Slow internet", "D) Unauthorized transfers"]},
            {"q": "How is gas priced for AI tasks?", "opts": ["A) Fixed fee", "B) Auction/Commit-Reveal", "C) Word count", "D) BTC price"]},
            {"q": "Truth without Trust removes what?", "opts": ["A) Oversight", "B) Belief (via Math/AI)", "C) Regulation", "D) Popularity"]},
            {"q": "Intelligent Contracts vs Ethereum Contracts?", "opts": ["A) Faster/Less secure", "B) NLP & Web Access", "C) No gas", "D) Solidity only"]},
            {"q": "Result of a successful appeal against a validator?", "opts": ["A) Promotion", "B) Nothing", "C) Slashing (Loss)", "D) Ban"]},
            {"q": "What is a 'True DAO'?", "opts": ["A) Intelligent Oracle", "B) World DB", "C) AI Decision Org", "D) Synthetic Bank"]},
            {"q": "What is an 'Intelligent Oracle'?", "opts": ["A) AI Prophet", "B) Web Data Contract", "C) Hardware Key", "D) Riddle Bot"]},
            {"q": "Equivalence Principle output?", "opts": ["A) Summary", "B) Score 1-100", "C) TRUE or FALSE", "D) New code"]},
            {"q": "Why Python for GenVM?", "opts": ["A) Math speed", "B) AI/ML Standard", "C) Blockchain native", "D) Easy for kids"]},
            {"q": "What determines Authority in GenLayer?", "opts": ["A) Gatekeepers", "B) Money", "C) Code", "D) Location"]}
        ]
        return qs[index]

    @gl.public.view
    def get_current_state(self, player_addr: str) -> str:
        sender = Address(player_addr)
        game_str = self.active_games.get(sender, "")
        if game_str == "": return json.dumps({"status": "IDLE"})
        game = json.loads(game_str)
        
        if game['status'] == "WAITING": return json.dumps({"status": "WAITING"})
        
        if game['status'] == "FINISHED": 
            return json.dumps({
                "status": "FINISHED", 
                "result": game['last_result'],
                "streak": game['streak']
            })
        
        q_data = self._get_question_text(game['q_index'])
        return json.dumps({
            "status": "PLAYING",
            "q": q_data['q'],
            "opts": q_data['opts'],
            "streak": game['streak'] + 1
        })

    @gl.public.view
    def get_player_data(self, player: str) -> dict:
        addr = Address(player)
        return {"xp": self.player_xp.get(addr, 0), "username": self.player_usernames.get(addr, "Anon")}

    @gl.public.view
    def get_leaderboard(self) -> list[dict]:
        board = []
        for addr in self.all_players:
            board.append({
                "address": addr.as_hex,
                "username": self.player_usernames.get(addr, "Anon"),
                "xp": self.player_xp.get(addr, 0)
            })
        return board