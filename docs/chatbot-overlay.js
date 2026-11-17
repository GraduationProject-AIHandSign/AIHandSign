(function () {
  const API_BASE_URL = "https://antler-bulldog-puppet.ngrok-free.dev";
  const NGROK_HEADERS = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true",
  };
  // 로그인 상태가 아니면 오버레이 표시하지 않음
  const userId = localStorage.getItem("user_id");
  if (!userId) return;

  // ── 스타일 주입 ──────────────────────────────────
  const style = document.createElement("style");
  style.textContent = `
    .co-fab {
      position: fixed; bottom: 28px; right: 28px;
      width: 56px; height: 56px;
      background: linear-gradient(135deg, #3b82f6, #6366f1);
      border-radius: 50%;
      box-shadow: 0 8px 24px rgba(59,130,246,0.45);
      display: flex; align-items: center; justify-content: center;
      font-size: 24px; cursor: pointer; border: none;
      transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
      z-index: 9000;
    }
    .co-fab:hover { transform: scale(1.08); box-shadow: 0 12px 32px rgba(59,130,246,0.55); }

    .co-panel {
      position: fixed; bottom: 96px; right: 28px;
      width: 360px; height: 500px;
      background: rgba(255,255,255,0.97);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255,255,255,0.8);
      border-radius: 24px;
      box-shadow: 0 24px 64px rgba(0,0,0,0.14);
      display: flex; flex-direction: column;
      z-index: 8999; overflow: hidden;
      transform: scale(0.85) translateY(20px);
      opacity: 0; pointer-events: none;
      transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
      transform-origin: bottom right;
      font-family: "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
    }
    .co-panel.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }

    .co-header {
      padding: 14px 18px;
      background: linear-gradient(135deg, #3b82f6, #6366f1);
      display: flex; align-items: center; justify-content: space-between;
      flex-shrink: 0;
    }
    .co-header-left { display: flex; align-items: center; gap: 10px; }
    .co-avatar {
      width: 34px; height: 34px;
      background: rgba(255,255,255,0.25);
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
    }
    .co-name { font-size: 14px; font-weight: 800; color: white; }
    .co-status {
      font-size: 11px; color: rgba(255,255,255,0.75);
      display: flex; align-items: center; gap: 4px;
    }
    .co-dot {
      width: 6px; height: 6px; border-radius: 50%; background: #4ade80;
      animation: co-pulse 1.5s infinite;
    }
    @keyframes co-pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

    .co-header-right { display: flex; align-items: center; gap: 6px; }
    .co-fullpage {
      background: rgba(255,255,255,0.15);
      border: none; border-radius: 8px;
      padding: 5px 10px;
      color: white; font-size: 11px; font-weight: 700;
      cursor: pointer; text-decoration: none;
      display: flex; align-items: center;
      transition: background 0.2s;
      font-family: inherit;
    }
    .co-fullpage:hover { background: rgba(255,255,255,0.3); }
    .co-close {
      background: rgba(255,255,255,0.2);
      border: none; border-radius: 8px;
      width: 28px; height: 28px;
      color: white; font-size: 14px;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      transition: background 0.2s;
    }
    .co-close:hover { background: rgba(255,255,255,0.35); }

    .co-messages {
      flex: 1; overflow-y: auto; padding: 14px;
      display: flex; flex-direction: column; gap: 10px;
    }
    .co-messages::-webkit-scrollbar { width: 4px; }
    .co-messages::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }

    .co-msg { display: flex; gap: 8px; align-items: flex-end; }
    .co-msg.user { flex-direction: row-reverse; }
    .co-msg-av {
      width: 26px; height: 26px; border-radius: 50%;
      background: linear-gradient(135deg,#3b82f6,#6366f1);
      display: flex; align-items: center; justify-content: center;
      font-size: 12px; flex-shrink: 0;
    }
    .co-msg.user .co-msg-av { background: #f1f5f9; }
    .co-bubble {
      max-width: 78%; padding: 9px 13px;
      border-radius: 18px; font-size: 13px; line-height: 1.6;
      word-break: break-word;
      overflow-wrap: break-word;
    }
    .co-msg.bot .co-bubble {
      background: #f1f5f9; color: #1e293b;
      border-bottom-left-radius: 4px;
    }
    .co-msg.user .co-bubble {
      background: linear-gradient(135deg,#3b82f6,#6366f1);
      color: white; border-bottom-right-radius: 4px;
    }
    .co-time { font-size: 10px; color: #94a3b8; margin-top: 3px; }

    .co-typing {
      display: flex; gap: 4px; padding: 10px 13px;
      background: #f1f5f9; border-radius: 18px;
      border-bottom-left-radius: 4px; width: fit-content;
    }
    .co-typing span {
      width: 6px; height: 6px; background: #94a3b8; border-radius: 50%;
      animation: co-bounce 1.2s infinite;
    }
    .co-typing span:nth-child(2) { animation-delay: 0.2s; }
    .co-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes co-bounce {
      0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-6px)}
    }

    .co-chips {
      padding: 0 14px 10px;
      display: flex; gap: 6px; flex-wrap: wrap; flex-shrink: 0;
    }
    .co-chip {
      padding: 5px 11px;
      background: #eff6ff; border: 1px solid #dbeafe;
      border-radius: 100px; font-size: 11px; font-weight: 700;
      color: #3b82f6; cursor: pointer;
      transition: background 0.2s; white-space: nowrap;
      font-family: inherit;
    }
    .co-chip:hover { background: #dbeafe; }

    .co-input-area {
      padding: 10px 14px; border-top: 1px solid #f1f5f9;
      display: flex; gap: 8px; flex-shrink: 0;
    }
    .co-input {
      flex: 1; padding: 9px 13px;
      border: 1.5px solid #e2e8f0; border-radius: 14px;
      font-size: 13px; font-family: inherit; outline: none;
      transition: border-color 0.2s; background: #f8fafc; color: #1e293b;
    }
    .co-input:focus { border-color: #3b82f6; background: white; }
    .co-send {
      width: 38px; height: 38px;
      background: linear-gradient(135deg,#3b82f6,#6366f1);
      border: none; border-radius: 12px;
      color: white; font-size: 15px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s; flex-shrink: 0;
    }
    .co-send:hover { transform: scale(1.05); box-shadow: 0 4px 12px rgba(59,130,246,0.4); }
    .co-send:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }

    @media (max-width: 480px) {
      .co-panel { width: calc(100vw - 24px); right: 12px; bottom: 84px; }
      .co-fab { bottom: 16px; right: 16px; }
    }
  `;
  document.head.appendChild(style);

  // ── HTML 삽입 ─────────────────────────────────────
  const html = `
    <button class="co-fab" id="coFab"><img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M18 8h1a4 4 0 0 1 0 8h-1'/%3E%3Cpath d='M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z'/%3E%3Cline x1='6' y1='1' x2='6' y2='4'/%3E%3Cline x1='10' y1='1' x2='10' y2='4'/%3E%3Cline x1='14' y1='1' x2='14' y2='4'/%3E%3C/svg%3E" width="28" height="28" alt="SORI" style="display:block;pointer-events:none"></button>
    <div class="co-panel" id="coPanel">
      <div class="co-header">
        <div class="co-header-left">
          <div class="co-avatar"><img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M18 8h1a4 4 0 0 1 0 8h-1'/%3E%3Cpath d='M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z'/%3E%3Cline x1='6' y1='1' x2='6' y2='4'/%3E%3Cline x1='10' y1='1' x2='10' y2='4'/%3E%3Cline x1='14' y1='1' x2='14' y2='4'/%3E%3C/svg%3E" width="18" height="18" alt="SORI" style="display:block;pointer-events:none"></div>
          <div>
            <div class="co-name">수어 AI 튜터</div>
            <div class="co-status"><div class="co-dot"></div>학습 데이터 연동됨</div>
          </div>
        </div>
        <div class="co-header-right">
          <a class="co-fullpage" href="chatbot.html">전체 화면 ↗</a>
          <button class="co-close" id="coClose">✕</button>
        </div>
      </div>
      <div class="co-messages" id="coMessages"></div>
      <div class="co-chips">
        <div class="co-chip" data-q="오늘의 단어가 뭐야?">오늘의 단어</div>
        <div class="co-chip" data-q="내 약점 카테고리가 뭐야?">내 약점</div>
        <div class="co-chip" data-q="다음 뱃지까지 얼마나 남았어?">뱃지 현황</div>
        <div class="co-chip" data-q="퀴즈에서 틀린 단어 알려줘">오답 단어</div>
      </div>
      <div class="co-input-area">
        <input class="co-input" id="coInput" placeholder="궁금한 점을 물어보세요!" />
        <button class="co-send" id="coSend">▶</button>
      </div>
    </div>
  `;
  const wrapper = document.createElement("div");
  wrapper.innerHTML = html;
  document.body.appendChild(wrapper);

  // ── 상태 ─────────────────────────────────────────
  let isOpen = false;
  let isLoading = false;
  let conversationHistory = [];
  let systemPrompt = buildBasePrompt();

  function buildBasePrompt() {
    return `당신은 AI 수어 학습 플랫폼의 AI 튜터입니다.

[플랫폼 기능]
- 교육: 커리큘럼 순서대로 수어 단어를 영상으로 학습
- 번역: 카메라로 수어를 실시간 인식해 텍스트로 변환
- 퀴즈: 학습한 단어를 퀴즈로 복습하고 점수 기록
- 사전: 단어 검색 후 3D 아바타로 동작 확인
- 오늘의 단어: 매일 5개의 단어가 커리큘럼 순서대로 배정

[역할]
사용자의 학습 현황과 플랫폼 기능을 바탕으로 맞춤 조언을 한국어로 친절하게 제공하세요.
아래 [사용자 학습 현황]이 제공된 경우 반드시 해당 데이터를 기반으로 답변하세요.`;
  }

  async function loadLearningContext() {
    if (!userId) return;
    try {
      // 홈 화면과 동일한 진도 일차 기준 (localStorage)
      const progressDay = parseInt(localStorage.getItem(`progress_day_${userId}`) || '1');
      const doneKey  = (() => { const d = new Date(); return `daily_done_${userId}_${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}`; })();
      const doneSet  = new Set(JSON.parse(localStorage.getItem(doneKey) || '[]'));

      const [statsRes, wrongRes, dailyRes] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/learning/${userId}/stats`, { headers: NGROK_HEADERS }),
        fetch(`${API_BASE_URL}/learning/${userId}/wrong`, { headers: NGROK_HEADERS }),
        fetch(`${API_BASE_URL}/daily/curriculum/${progressDay}`, { headers: NGROK_HEADERS }),
      ]);
      const stats = (statsRes.status === 'fulfilled' && statsRes.value.ok) ? await statsRes.value.json() : null;
      const wrong = (wrongRes.status === 'fulfilled' && wrongRes.value.ok) ? await wrongRes.value.json() : [];
      const daily = (dailyRes.status === 'fulfilled' && dailyRes.value.ok) ? await dailyRes.value.json() : [];

      // localStorage 기반 퀴즈/뱃지 데이터 (백엔드 무관하게 항상 계산)
      const qs     = JSON.parse(localStorage.getItem('quiz_stats')    || '{"correct":0,"total":0}');
      const qw     = JSON.parse(localStorage.getItem('quiz_word_ids') || '[]');
      const qTotal = qs.total || 0;
      const qAcc   = qTotal > 0 ? Math.round(qs.correct / qs.total * 100) : 0;
      const qWords = qw.length;

      const RANKS = [
        { emoji: '🌱', grade: '비기너',   name: '수어 입문자',  minCount: 0,  minAcc: 0   },
        { emoji: '🥉', grade: '브론즈',   name: '수어 도전자',  minCount: 5,  minAcc: 40  },
        { emoji: '🥈', grade: '실버',     name: '수어 학습자',  minCount: 10, minAcc: 60  },
        { emoji: '🥇', grade: '골드',     name: '수어 마스터',  minCount: 15, minAcc: 80  },
        { emoji: '💎', grade: '플래티넘', name: '수어 챔피언',  minCount: 20, minAcc: 95  },
        { emoji: '👑', grade: '퍼펙트',   name: '수어 천재',    minCount: 20, minAcc: 100 },
      ];
      let rankIdx = 0;
      for (let i = RANKS.length - 1; i >= 0; i--) {
        if (qTotal >= RANKS[i].minCount && qAcc >= RANKS[i].minAcc) { rankIdx = i; break; }
      }
      const curRank  = RANKS[rankIdx];
      const nextRank = RANKS[rankIdx + 1] || null;
      const rankStr  = `${curRank.emoji} ${curRank.grade} — ${curRank.name}`;
      const nextStr  = nextRank
        ? `다음 등급: ${nextRank.emoji} ${nextRank.name} (응시 ${nextRank.minCount}회↑, 정답률 ${nextRank.minAcc}%↑ 필요)`
        : '최고 등급 달성';

      // 백엔드 데이터 (실패 시 기본값)
      if (!stats && !daily.length) {
        systemPrompt = `${buildBasePrompt()}

[사용자 학습 현황]
- 현재 진행 일차: ${progressDay}일차
- 퀴즈 응시 횟수: ${qTotal}회 | 퀴즈 정답률: ${qAcc}% | 퀴즈로 학습한 단어 수: ${qWords}개
- 현재 등급: ${rankStr}
- ${nextStr}`;
        return;
      }

      const dailySummary = daily.length
        ? daily.map(w => `${w.word_name}(${w.category ?? '일상'}, ${doneSet.has(String(w.word_id)) ? "학습 완료" : "미학습"})`).join(", ")
        : "없음";
      const wrongSummary = wrong.length
        ? wrong.slice(0, 5).map(w => `${w.word_name}(${w.category})`).join(", ")
        : "없음";

      systemPrompt = `${buildBasePrompt()}

[사용자 학습 현황]
- 현재 진행 일차: ${progressDay}일차
- 오늘의 단어(${progressDay}일차): ${dailySummary}
- 퀴즈 응시 횟수: ${qTotal}회 | 퀴즈 정답률: ${qAcc}% | 퀴즈로 학습한 단어 수: ${qWords}개
- 최근 틀린 단어: ${wrongSummary}
- 현재 등급: ${rankStr}
- ${nextStr}`;
    } catch (e) {
      console.warn("[오버레이] 학습 컨텍스트 로드 실패:", e.message);
      // API 실패해도 localStorage 기반 데이터로 최소 프롬프트 구성
      try {
        const progressDay = parseInt(localStorage.getItem(`progress_day_${userId}`) || '1');
        const qs     = JSON.parse(localStorage.getItem('quiz_stats')    || '{"correct":0,"total":0}');
        const qw     = JSON.parse(localStorage.getItem('quiz_word_ids') || '[]');
        const qTotal = qs.total || 0;
        const qAcc   = qTotal > 0 ? Math.round(qs.correct / qs.total * 100) : 0;
        const qWords = qw.length;
        systemPrompt = `${buildBasePrompt()}

[사용자 학습 현황]
- 현재 진행 일차: ${progressDay}일차
- 퀴즈 응시 횟수: ${qTotal}회 | 퀴즈 정답률: ${qAcc}% | 퀴즈로 학습한 단어 수: ${qWords}개`;
      } catch (_) {}
    }
  }

  loadLearningContext();

  const fab      = document.getElementById("coFab");
  const panel    = document.getElementById("coPanel");
  const closeBtn = document.getElementById("coClose");
  const messages = document.getElementById("coMessages");
  const input    = document.getElementById("coInput");
  const sendBtn  = document.getElementById("coSend");

  // ── 이벤트 ───────────────────────────────────────
  fab.addEventListener("click", toggle);
  closeBtn.addEventListener("click", toggle);
  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) send(); });
  document.querySelectorAll(".co-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      input.value = chip.dataset.q;
      send();
    });
  });

  function toggle() {
    isOpen = !isOpen;
    panel.classList.toggle("open", isOpen);
    if (isOpen) {
      loadLearningContext(); // 패널 열 때마다 최신 학습 데이터 갱신
      if (messages.children.length === 0) showWelcome();
    }
  }

  // ── 환영 메시지 ───────────────────────────────────
  function showWelcome() {
    const name = localStorage.getItem("user_name") || "학습자";
    addMsg("bot", `안녕하세요, ${name}님! 🤟<br>궁금한 점이 있으면 무엇이든 물어보세요~`);
  }

  // ── 메시지 전송 ───────────────────────────────────
  async function send() {
    const text = input.value.trim();
    if (!text || isLoading) return;

    addMsg("user", text);
    input.value = "";
    isLoading = true;
    sendBtn.disabled = true;

    const priorHistory = conversationHistory.slice();
    conversationHistory.push({ role: "user", text });

    const typingId = showTyping();

    try {
      // 백엔드 /chat/ 경유 호출 (Gemini 키는 서버에만 존재)
      const chatRes = await fetch(`${API_BASE_URL}/chat/`, {
        method: "POST",
        headers: NGROK_HEADERS,
        body: JSON.stringify({
          user_id: userId ? parseInt(userId) : null,
          message: text,
          system_prompt: systemPrompt,
          history: priorHistory,
        }),
      });
      const chatData = await chatRes.json();
      if (!chatRes.ok) throw new Error(typeof chatData.detail === "string" ? chatData.detail : "챗봇 오류");
      const answer = chatData.answer;

      conversationHistory.push({ role: "model", text: answer });
      removeTyping(typingId);
      addMsg("bot", answer
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/\n/g, "<br>"));


    } catch (e) {
      removeTyping(typingId);
      addMsg("bot", `⚠️ 오류: ${e.message}`);
    } finally {
      isLoading = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // ── UI 헬퍼 ──────────────────────────────────────
  function addMsg(role, html) {
    const now = new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
    const div = document.createElement("div");
    div.className = `co-msg ${role}`;
    div.innerHTML = `
      ${role === "bot" ? '<div class="co-msg-av">🤟</div>' : ""}
      <div>
        <div class="co-bubble">${html}</div>
        <div class="co-time">${now}</div>
      </div>
      ${role === "user" ? '<div class="co-msg-av">👤</div>' : ""}
    `;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function showTyping() {
    const id = "co-typing-" + Date.now();
    const div = document.createElement("div");
    div.id = id;
    div.className = "co-msg bot";
    div.innerHTML = `
      <div class="co-msg-av">🤟</div>
      <div class="co-typing"><span></span><span></span><span></span></div>
    `;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return id;
  }

  function removeTyping(id) {
    document.getElementById(id)?.remove();
  }
})();
