const app = document.querySelector("#app");
const apiStatus = document.querySelector("#apiStatus");
let directoryCache = null;

const BRL = new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"});

async function getJSON(url){
  const r = await fetch(url,{headers:{"Accept":"application/json"}});
  const data = await r.json().catch(()=>({erro:"Resposta inválida do servidor."}));
  if(!r.ok) throw new Error(data.erro || `Erro ${r.status}`);
  apiStatus.className="api-status ok";
  apiStatus.innerHTML='<span class="pulse"></span> Câmara: online';
  return data;
}
function loading(text="Consultando fonte oficial…"){
  app.innerHTML=`<div class="loading"><div class="spinner"></div><div>${text}</div></div>`;
}
function errorView(message){
  apiStatus.className="api-status error";
  apiStatus.innerHTML='<span class="pulse"></span> Câmara: indisponível';
  app.innerHTML=`<section class="card"><h2>Não foi possível carregar os dados</h2><p class="muted">${escapeHtml(message)}</p><p class="small">A v0.3 consulta os Dados Abertos da Câmara em tempo real. Tente novamente em instantes.</p></section>`;
}
function escapeHtml(v=""){
  return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
}
function initials(name=""){
  return name.split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join("").toUpperCase();
}
function photo(src,name,cls="photo"){
  const safe=escapeHtml(src||"");
  return safe ? `<img class="${cls}" src="${safe}" alt="Foto de ${escapeHtml(name)}" loading="lazy" onerror="this.style.visibility='hidden'">` : `<div class="${cls}">${initials(name)}</div>`;
}

async function router(){
  const hash=location.hash||"#home";
  try{
    if(hash.startsWith("#deputado/")){
      const [,id,section="visao-geral"]=hash.split("/");
      return renderProfile(id,section);
    }
    if(hash==="#deputados") return renderDirectory();
    if(hash==="#metodologia") return renderMethod();
    return renderHome();
  }catch(e){ errorView(e.message); }
}
window.addEventListener("hashchange",router);

async function getDirectory(){
  if(directoryCache) return directoryCache;
  directoryCache=await getJSON("/api/deputados");
  return directoryCache;
}

async function renderHome(){
  loading();
  const data=await getDirectory();
  const meta=data.meta||{};
  const parties=(meta.partidos||[]).length;
  const ufs=(meta.ufs||[]).length;
  app.innerHTML=`
    <section class="hero">
      <div>
        <div class="eyebrow">Ficha Pública · MVP nacional</div>
        <h1>O histórico público de quem representa você.</h1>
        <p>Começamos pelos deputados federais. Os perfis abaixo são carregados diretamente dos Dados Abertos da Câmara e agora incluem uma amostra de votações nominais reais recentes.</p>
        <div class="kpis">
          <div class="kpi"><span>Deputados retornados agora</span><strong>${meta.totalAtual ?? data.dados.length}</strong></div>
          <div class="kpi"><span>Partidos representados</span><strong>${parties}</strong></div>
          <div class="kpi"><span>UFs representadas</span><strong>${ufs}</strong></div>
        </div>
      </div>
      <div class="card searchbox">
        <h2>Encontre um deputado</h2>
        <input id="homeSearch" placeholder="Digite nome, partido ou UF" autocomplete="off">
        <div id="homeMatches"></div>
        <div class="notice"><strong>Fonte ao vivo:</strong> Câmara dos Deputados. Cada perfil mantém o link da fonte oficial para conferência.</div>
      </div>
    </section>
    <section>
      <div class="section-head"><div><div class="eyebrow">Começar explorando</div><h2>Alguns deputados da base atual</h2></div><a class="source-link small" href="#deputados">Ver todos →</a></div>
      <div class="deputy-grid">${data.dados.slice(0,8).map(deputyCard).join("")}</div>
    </section>`;
  bindDeputies();
  const input=document.querySelector("#homeSearch");
  const matches=document.querySelector("#homeMatches");
  input.addEventListener("input",()=>{
    const q=input.value.trim().toLowerCase();
    if(q.length<2){matches.innerHTML="";return;}
    const found=data.dados.filter(d=>`${d.nome} ${d.siglaPartido} ${d.siglaUf}`.toLowerCase().includes(q)).slice(0,6);
    matches.innerHTML=`<div style="display:grid;gap:7px">${found.map(d=>`<a class="deputy" href="#deputado/${d.id}">${photo(d.urlFoto,d.nome,"photo")}<div><h3>${escapeHtml(d.nome)}</h3><div class="tagrow"><span class="tag party">${escapeHtml(d.siglaPartido)}</span><span class="tag uf">${escapeHtml(d.siglaUf)}</span></div></div></a>`).join("")}</div>`;
  });
}

function deputyCard(d){
  return `<a class="deputy" href="#deputado/${d.id}">
    ${photo(d.urlFoto,d.nome)}
    <div><h3>${escapeHtml(d.nome)}</h3><div class="tagrow"><span class="tag party">${escapeHtml(d.siglaPartido)}</span><span class="tag uf">${escapeHtml(d.siglaUf)}</span></div></div>
  </a>`;
}
function bindDeputies(){}

async function renderDirectory(){
  loading("Carregando deputados federais…");
  const data=await getDirectory();
  const deps=data.dados;
  app.innerHTML=`
    <div class="section-head"><div><div class="eyebrow">Câmara dos Deputados</div><h1>Deputados federais</h1></div><a class="source-link small" href="${escapeHtml(data.meta.urlFonte)}" target="_blank" rel="noopener">Fonte oficial ↗</a></div>
    <div class="filters">
      <input id="q" placeholder="Nome, partido ou UF">
      <select id="uf"><option value="">Todas as UFs</option>${data.meta.ufs.map(x=>`<option>${escapeHtml(x)}</option>`).join("")}</select>
      <select id="party"><option value="">Todos os partidos</option>${data.meta.partidos.map(x=>`<option>${escapeHtml(x)}</option>`).join("")}</select>
    </div>
    <div class="directory-meta"><span id="count">${deps.length} deputados</span><span>Atualização via API oficial · cache temporário de ${Math.round(data.meta.cacheSegundos/60)} min</span></div>
    <div class="deputy-grid" id="grid">${deps.map(deputyCard).join("")}</div>`;
  bindDeputies();
  const q=document.querySelector("#q"),uf=document.querySelector("#uf"),party=document.querySelector("#party"),grid=document.querySelector("#grid"),count=document.querySelector("#count");
  function apply(){
    const term=q.value.trim().toLowerCase(), u=uf.value, p=party.value;
    const filtered=deps.filter(d=>(!term||`${d.nome} ${d.siglaPartido} ${d.siglaUf}`.toLowerCase().includes(term))&&(!u||d.siglaUf===u)&&(!p||d.siglaPartido===p));
    count.textContent=`${filtered.length} deputados`;
    grid.innerHTML=filtered.map(deputyCard).join("");
    bindDeputies();
  }
  [q,uf,party].forEach(x=>x.addEventListener("input",apply));
}

async function renderProfile(id,activeSection="visao-geral"){
  loading("Montando ficha oficial do deputado…");
  const [profile, expenses, career, votes, contradictions] = await Promise.all([
    getJSON(`/api/deputados/${id}`),
    getJSON(`/api/deputados/${id}/despesas?ano=2026`).catch(()=>null),
    getJSON(`/api/deputados/${id}/carreira`).catch(()=>null),
    getJSON(`/api/deputados/${id}/votacoes?limite=8`).catch(()=>null),
    getJSON(`/api/deputados/${id}/contradicoes?demonstracao=1`).catch(()=>null)
  ]);
  const d=profile.dados||{};
  const s=d.ultimoStatus||{};
  const name=s.nomeEleitoral||d.nomeCivil||"Deputado";
  const exp=expenses?.dados;
  const history=career?.dados;
  const topCategories=(exp?.categorias||[]).slice(0,5);
  const maxCat=topCategories[0]?.valor||1;
  const mandates=history?.mandatosExternos||[];
  const camHistory=history?.historicoCamara||[];
  const recentVotes=votes?.dados||[];
  const demo=contradictions?.demonstracao;

  app.innerHTML=`
    <section class="profile-top" id="secao-visao-geral">
      <div>${photo(s.urlFoto,name,"profile-photo")}</div>
      <div class="identity">
        <div>
          <h1>${escapeHtml(name)}</h1>
          <div class="badges">
            <span class="badge blue">Deputado Federal</span>
            <span class="badge green"><span class="party-logo">${escapeHtml((s.siglaPartido||"?").slice(0,3))}</span>${escapeHtml(s.siglaPartido||"—")}</span>
            <span class="badge">🇧🇷 Brasil</span>
            <span class="badge">${escapeHtml(s.siglaUf||"UF")}</span>
          </div>
          <div class="metadata">
            Nome civil: <strong>${escapeHtml(d.nomeCivil||"—")}</strong><br>
            Situação na Câmara: <strong>${escapeHtml(s.situacao||"—")}</strong> · Condição eleitoral: <strong>${escapeHtml(s.condicaoEleitoral||"—")}</strong><br>
            Gabinete: <strong>${escapeHtml(s.gabinete?.nome||"—")}</strong> · Legislatura: <strong>${escapeHtml(s.idLegislatura||"—")}</strong>
          </div>
          <p class="small"><a class="source-link" href="${escapeHtml(profile.meta.urlFonte)}" target="_blank" rel="noopener">Abrir cadastro original na API da Câmara ↗</a></p>
        </div>
        <aside class="status-box">
          <h3>Status eleitoral</h3>
          <div class="status-current">
            <strong>Em construção</strong>
            <span>Esta etapa ainda não infere inelegibilidade a partir da Câmara. O status “já esteve inelegível” só será exibido após integração documental com TSE/Justiça Eleitoral.</span>
          </div>
        </aside>
      </div>
    </section>

    <section class="stats">
      <div class="stat"><label>Partido atual</label><strong>${escapeHtml(s.siglaPartido||"—")}</strong><small>${escapeHtml(s.siglaUf||"")}</small></div>
      <div class="stat"><label>Despesas 2026</label><strong>${exp?BRL.format(exp.total):"—"}</strong><small>${exp?`${exp.quantidadeLancamentos} lançamentos`:"não carregado"}</small></div>
      <div class="stat"><label>Mandatos externos</label><strong>${mandates.length}</strong><small>registrados pela Câmara</small></div>
      <div class="stat"><label>Histórico na Câmara</label><strong>${camHistory.length}</strong><small>mudanças registradas</small></div>
      <div class="stat"><label>Votos recentes</label><strong>${votes?recentVotes.length:"—"}</strong><small>nominais na amostra</small></div>
      <div class="stat"><label>ID oficial</label><strong>${escapeHtml(d.id||id)}</strong><small>Câmara dos Deputados</small></div>
    </section>

    <nav class="tabs" aria-label="Seções da ficha">
      ${profileTab(id,"visao-geral","Visão geral",activeSection)}
      ${profileTab(id,"votacoes","Votações",activeSection)}
      ${profileTab(id,"despesas","Despesas",activeSection)}
      ${profileTab(id,"historico","Histórico",activeSection)}
      ${profileTab(id,"contradicoes","Contradições",activeSection)}
      ${profileTab(id,"justica","Justiça",activeSection)}
      ${profileTab(id,"eleicoes","Eleições",activeSection)}
    </nav>

    <section class="profile-grid">
      <article class="panel" id="secao-cadastro">
        <h2>1. Cadastro oficial</h2>
        <div class="detail-list">
          ${detail("Nome civil",d.nomeCivil)}
          ${detail("Nome eleitoral",s.nomeEleitoral)}
          ${detail("CPF",d.cpf ? "Informação disponível na fonte oficial" : "—")}
          ${detail("Sexo",d.sexo)}
          ${detail("Escolaridade",d.escolaridade)}
          ${detail("Data de nascimento",formatDate(d.dataNascimento))}
          ${detail("Município de nascimento",d.municipioNascimento ? `${d.municipioNascimento} / ${d.ufNascimento||""}` : "—")}
        </div>
      </article>

      <article class="panel" id="secao-despesas">
        <h2>2. Despesas parlamentares · 2026</h2>
        ${exp?`<div class="expense-total">${BRL.format(exp.total)}</div><div class="small muted">${exp.quantidadeLancamentos} lançamentos consultados</div>
        <div class="expense-bars">${topCategories.map(c=>`<div class="expense-item"><span class="small">${escapeHtml(c.tipo)}</span><strong class="small">${BRL.format(c.valor)}</strong><div class="bar"><span style="width:${Math.max(3,(c.valor/maxCat)*100)}%"></span></div></div>`).join("")}</div>
        <p class="tiny"><a class="source-link" href="${escapeHtml(expenses.meta.urlFonte)}" target="_blank" rel="noopener">Ver endpoint oficial ↗</a></p>`:
        `<div class="notice">Não foi possível carregar as despesas neste acesso.</div>`}
      </article>

      <article class="panel" id="secao-historico">
        <h2>3. Histórico político</h2>
        ${mandates.length?`<div class="timeline">${mandates.slice(0,6).map(m=>`<div class="timeline-item"><strong>${escapeHtml(m.cargo||"Mandato externo")}</strong><p>${escapeHtml([m.entidade,m.uf].filter(Boolean).join(" · "))}</p><p>${escapeHtml([m.anoInicio,m.anoFim].filter(Boolean).join(" – "))}</p></div>`).join("")}</div>`:
        `<p class="small muted">Nenhum mandato externo retornado pela fonte oficial para este perfil.</p>`}
        ${career?.meta?.urlMandatos?`<p class="tiny"><a class="source-link" href="${escapeHtml(career.meta.urlMandatos)}" target="_blank" rel="noopener">Fonte: mandatos externos ↗</a></p>`:`<p class="tiny muted">Fonte temporariamente indisponível neste acesso.</p>`}
      </article>

      <article class="panel votes-panel" id="secao-votacoes">
        <h2>4. Votações nominais recentes</h2>
        ${votes?`${recentVotes.length?`<div class="vote-list">${recentVotes.map(voteCard).join("")}</div>`:`<div class="notice">Nenhum voto nominal foi localizado na janela recente analisada.</div>`}
        <p class="tiny muted vote-note">${escapeHtml(votes.meta?.nota||"")}</p>`:
        `<div class="notice">Não foi possível consultar as votações neste acesso.</div>`}
      </article>

      <article class="panel" id="secao-contradicoes">
        <h2>5. Contradições</h2>
        <div class="notice"><strong>Nenhuma contradição publicada.</strong> O motor inicial já cruza posições opostas sobre um mesmo tema, mas declarações reais ainda dependem de fonte estruturada, contexto e revisão humana.</div>
        ${demo?`<details class="demo-box"><summary>Ver exemplo puramente demonstrativo</summary>
          <div class="demo-warning">${escapeHtml(demo.rotulo)}</div>
          <p class="small"><strong>Declaração fictícia:</strong> ${escapeHtml(demo.posicoes?.[0]?.texto||"")}</p>
          <p class="small"><strong>Ato fictício:</strong> ${escapeHtml(demo.atos?.[0]?.texto||"")}</p>
          <p class="small"><strong>Saída:</strong> possível contradição · requer revisão humana · não publicável.</p>
        </details>`:""}
      </article>

      <article class="panel" id="secao-justica">
        <h2>6. Justiça e elegibilidade</h2>
        <div class="notice"><strong>Não automatizado.</strong> Estes campos permanecem vazios até a integração oficial com TSE/Justiça Eleitoral. Um campo vazio não significa “sem processos” nem “elegível”.</div>
      </article>

      <article class="panel" id="secao-eleicoes">
        <h2>7. Eleições</h2>
        <div class="notice"><strong>Próxima integração oficial.</strong> Candidaturas, resultados, patrimônio declarado e períodos de inelegibilidade só serão preenchidos depois da integração documental com o TSE.</div>
      </article>

      <article class="panel" id="secao-fontes">
        <h2>8. Fontes</h2>
        <div class="detail-list">
          ${detailLink("Cadastro do deputado",profile.meta.urlFonte)}
          ${expenses?detailLink("Despesas de 2026",expenses.meta.urlFonte):""}
          ${career?detailLink("Histórico parlamentar",career.meta.urlHistorico):""}
          ${career?detailLink("Mandatos externos",career.meta.urlMandatos):""}
          ${recentVotes.length?detailLink("Voto nominal mais recente",recentVotes[0].urlFonte):""}
        </div>
      </article>
    </section>`;
  const target=document.querySelector(`#secao-${sectionSlug(activeSection)}`);
  if(activeSection!=="visao-geral"&&target){requestAnimationFrame(()=>target.scrollIntoView({behavior:"smooth",block:"start"}));}
}
function sectionSlug(section){return ({"visao-geral":"visao-geral",votacoes:"votacoes",despesas:"despesas",historico:"historico",contradicoes:"contradicoes",justica:"justica",eleicoes:"eleicoes"})[section]||"visao-geral"}
function profileTab(id,section,label,active){return `<a class="tab ${sectionSlug(active)===section?"active":""}" href="#deputado/${escapeHtml(id)}/${section}" aria-current="${sectionSlug(active)===section?"page":"false"}">${escapeHtml(label)}</a>`}
function detail(label,value){return `<div class="detail-row"><label>${escapeHtml(label)}</label><strong>${escapeHtml(value||"—")}</strong></div>`}
function detailLink(label,url){return `<div class="detail-row"><label>${escapeHtml(label)}</label><strong><a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener">Abrir fonte oficial ↗</a></strong></div>`}
function formatDate(v){if(!v)return"—";const [y,m,d]=String(v).split("-");return y&&m&&d?`${d}/${m}/${y}`:v}
function voteCard(v){
  const vote=String(v.voto||"—");
  const cls=vote.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z]/g,"");
  return `<div class="vote-item">
    <span class="vote-value ${escapeHtml(cls)}">${escapeHtml(vote)}</span>
    <div><strong>${escapeHtml(v.descricao||"Votação nominal")}</strong>
    <p>${escapeHtml(v.resultado||v.descricaoUltimaAberturaVotacao||"Resultado não descrito")}</p>
    <div class="vote-meta">${escapeHtml(formatDate(v.data))} · <a class="source-link" href="${escapeHtml(v.urlFonte)}" target="_blank" rel="noopener">conferir voto oficial ↗</a></div></div>
  </div>`;
}

function renderMethod(){
  app.innerHTML=`
    <div class="section-head"><div><div class="eyebrow">Metodologia do produto</div><h1>Separar coleta de julgamento</h1></div></div>
    <section class="card method">
      <div class="method-item"><div><h3>Dados objetivos primeiro</h3><p>Nome, partido, UF, cadastro, despesas e histórico vêm diretamente das APIs e documentos oficiais.</p></div></div>
      <div class="method-item"><div><h3>Votos nominais reais</h3><p>A ficha cruza uma janela recente de votações com o registro individual de cada parlamentar. Ausência na amostra não é tratada como ausência à sessão.</p></div></div>
      <div class="method-item"><div><h3>IA encontra relações</h3><p>Falas, votos e atos são normalizados por tema. Um agente propõe uma possível contradição.</p></div></div>
      <div class="method-item"><div><h3>IA tenta refutar</h3><p>Um segundo agente procura mudança de contexto, alteração de texto legislativo, declaração explicativa ou outro motivo que enfraqueça a conclusão.</p></div></div>
      <div class="method-item"><div><h3>Risco editorial</h3><p>Registros sensíveis de Justiça, crime, inelegibilidade e acusações exigem fonte apropriada e revisão humana. Esses campos não são automatizados na v0.3.</p></div></div>
      <div class="method-item"><div><h3>Leitor confere</h3><p>Cada ficha mantém links para as fontes de origem. O produto não dá uma nota geral de “honestidade”.</p></div></div>
    </section>`;
}

router();
