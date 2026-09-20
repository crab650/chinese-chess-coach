# 象棋陪練（Chinese Chess Coach）

[繁體中文](#繁體中文) | [English](#english)

---

<a name="繁體中文"></a>
## 繁體中文

這是一個在瀏覽器使用的象棋學習與陪練系統。你可以選擇「**大師帶走**」，每回合先看電腦對手這一步的用意，再看我方建議與後續推演；也可以選擇「**自主練習**」，自己先走，出現明顯失誤時再查看分層提示。所有的對局、答題、錯題與練習結果均保存在本機 SQLite 資料庫中。

### 核心功能

1. **大師帶走（Guided Mode）**：
   - 電腦走棋後先進行「意圖提問」（猜測對方是在將軍、吃子/捉子、還是調整位置）。
   - 答題後由系統解析原因，並在棋盤標示威脅與防守路線。
   - 標出我方推薦走法，並可「播放後續推演」檢視 2~3 回合的可能變化。
   - 提供「比較我想走的棋」，在不影響真實局面的情況下評估自己的思路與引擎推薦之差異。
2. **自主練習（Free Practice Mode）**：
   - 玩家獨立思考下棋，若出現明顯失誤會觸發「分層提示」，引導自我修正。
3. **複盤與錯題重練**：
   - 自動記錄每一局走法，可隨時回溯逐步複盤。
   - 收集失誤局面至「我的錯題」，供後續反覆強化練習。
   - 「學習概況」追蹤答題準確率與練習進度。

---

### 開始使用

#### 系統需求
- Windows（預設內附 ElephantEye Windows 引擎）
- Python 3.10 以上
- Flask

#### 安裝與啟動

於專案目錄執行：

```powershell
python -m pip install -r requirements.txt
python -m chess_coach
```

也可以直接雙擊執行 `start_coach.bat`。程式會啟動並自動開啟瀏覽器至 `http://127.0.0.1:5111/`。
結束時關閉命令視窗或在終端機按下 `Ctrl+C`。

首次啟動時會自動在 `instance/chess_coach.db` 建立 SQLite 資料庫，儲存所有對局與錯題記錄。

---

### 操作流程

1. **建立對局**：在首頁選擇執紅或執黑、難度（初級、中級、高級），以及「大師帶走」或「自主練習」。
2. **意圖解析**：大師帶走模式下，電腦走子後會先跳出問題「電腦這步想做什麼？」，選答後可查看棋盤標示與詳細說明。
3. **查看建議與推演**：點擊「看我方下一步建議」，檢視推薦著法、當前面臨問題與目的；點擊「播放後續推演」可在獨立棋盤查看可能分支。
4. **比較思路**：若有自己的想法，按「比較我想走的棋」並在棋盤點選走法，查看雙方後續分支與差異評估。
5. **實際落子**：點擊選取棋子與合法落點走棋。若被將軍，棋盤會標示應將棋子。
6. **分層提示**：若產生明顯失誤，可逐步查看分層提示並選擇重走或堅持原走法。
7. **複盤練習**：至「對局紀錄」回顧歷史對局，至「我的錯題」重練錯誤局面。

---

### 專案結構

- `chess_coach/`：Flask 應用程式、象棋規則判斷、UCCI 引擎通訊協議、SQLite 模型與前端介面。
- `chess_coach/engines/`：ElephantEye UCCI 象棋引擎及資料檔案（Windows 執行檔）。
- `tests/`：單元測試（涵蓋走法規則、意圖判斷、大師推演、資料庫遷移與 API）。
- `tools/`：輔助與健康檢測腳本（如 `smoke_eleeye.py`）。
- `CHESS_COACH_V1_PLAN.md`：功能規格設計與驗收標準說明。

---

### 開發與測試

執行單元測試：

```powershell
python -m unittest discover -s tests -v
```

#### 環境變數設定

| 變數名稱 | 預設值 | 說明 |
| :--- | :--- | :--- |
| `CHESS_COACH_DATABASE` | `instance/chess_coach.db` | SQLite 資料庫存放路徑 |
| `CHESS_COACH_ENGINE` | 內附 ElephantEye 執行檔 | UCCI 引擎路徑 |
| `CHESS_COACH_ENGINE_TIMEOUT` | `10.0` | 引擎計算超時時間（秒） |
| `CHESS_COACH_COACH_DEPTH` | `6` | 失誤判定與教練分析深度 |
| `CHESS_COACH_GUIDE_DEPTH` | `6` | 大師帶走模式推演深度 |
| `CHESS_COACH_OPEN_BROWSER` | `1` | 設為 `0` 時啟動伺服器不自動開啟瀏覽器 |

---

<a name="english"></a>
## English

**Chinese Chess Coach** is an interactive web-based Xiangqi (象棋, Chinese Chess) training system powered by a local UCCI engine (ElephantEye). Designed for players looking to sharpen their tactical intuition, it features real-time move guidance, opponent intent quizzes, layered blunder coaching, and variation comparisons.

### Key Features

1. **Master Guided Mode**:
   - **Opponent Intent Quiz**: After the AI makes a move, test your tactical awareness by predicting whether it aims to check, capture/threaten a piece, or reposition.
   - **Move Analysis**: Explains the rationale behind moves with visual annotations of attack and defense trajectories.
   - **Engine Recommendations & Rollouts**: Displays optimal next moves and lets you play through 2–3 ply rollout variations on an interactive secondary board.
   - **"Compare My Move"**: Click an alternative move on the board to compare your planned continuation against the engine's line without altering the real game state.
2. **Autonomous Practice Mode**:
   - Play independently with unobtrusive background analysis.
   - Triggers **Layered Hints** when significant blunders are detected, giving hints progressively instead of spoiling the answer immediately.
3. **Review & Mistake Bank**:
   - Step-by-step game replay with move histories saved in local SQLite.
   - Failed scenarios and blunders are recorded to **"My Mistakes"** for deliberate replay and review.
   - **Learning Overview** tracks quiz accuracy and practice consistency over time.

---

### Getting Started

#### Requirements
- Windows (bundled with ElephantEye 3.21 Windows engine)
- Python 3.10+
- Flask

#### Installation & Launch

Run the following commands in the project root directory:

```powershell
python -m pip install -r requirements.txt
python -m chess_coach
```

Or simply double-click `start_coach.bat`. The web application will launch at `http://127.0.0.1:5111/` and automatically open your default browser. Press `Ctrl+C` or close the terminal window to stop the server.

A local SQLite database will be initialized at `instance/chess_coach.db` upon the first startup.

---

### How to Use

1. **Start a Game**: Choose your side (Red / Black), difficulty level (Novice, Intermediate, Advanced), and coaching mode (Master Guided or Autonomous Practice).
2. **Decode Opponent's Intent**: In Master Guided Mode, guess the enemy's purpose ("What is the computer planning?") before seeing hints.
3. **Explore Recommendations**: View recommended moves with tactical commentary and click **Play Rollout** to preview likely branching sequences.
4. **Compare Plans**: Wondering why your move wasn't recommended? Use **Compare My Move** to pit your idea against the engine's response.
5. **Make Moves**: Select your piece and legal target destination. When checked, legal responses are highlighted.
6. **Blunder Assistance**: If you stumble into a tactical mistake, request layered hints to figure out the counterplay on your own.
7. **Replay & Practice**: Revisit past games under **Game History** and drill troubled positions in **My Mistakes**.

---

### Project Structure

- `chess_coach/`: Core Flask web application, Xiangqi rule validation, UCCI engine wrapper, SQLite models, and UI assets.
- `chess_coach/engines/`: Bundled ElephantEye UCCI engine binaries and opening book (`BOOK.DAT`, `ELEEYE.EXE`, `EVALUATE.DLL`).
- `tests/`: Automated unit tests covering board logic, intent detection, guided lines, database schema migrations, and route APIs.
- `tools/`: Diagnostic and health check utilities (e.g. `smoke_eleeye.py`).
- `CHESS_COACH_V1_PLAN.md`: Functional design specifications and roadmap documentation.

---

### Testing & Development

Run the test suite:

```powershell
python -m unittest discover -s tests -v
```

#### Configuration via Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `CHESS_COACH_DATABASE` | `instance/chess_coach.db` | Path to SQLite database file |
| `CHESS_COACH_ENGINE` | Bundled `ELEEYE.EXE` | Path to UCCI engine executable |
| `CHESS_COACH_ENGINE_TIMEOUT` | `10.0` | Engine search timeout in seconds |
| `CHESS_COACH_COACH_DEPTH` | `6` | Search depth for blunder evaluation |
| `CHESS_COACH_GUIDE_DEPTH` | `6` | Search depth for master rollout variations |
| `CHESS_COACH_OPEN_BROWSER` | `1` | Set to `0` to disable automatic browser opening |
