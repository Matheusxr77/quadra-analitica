const cores = ["#55b6ff", "#ffad66"];
let graficos = {};

function formatar(valor, casas = 2) {
  if (valor === null || valor === undefined) return "—";
  return Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function destruirGrafico(nome) {
  if (graficos[nome]) graficos[nome].destroy();
}

// Padrão para todos os gráficos: título, eixos rotulados (com unidade) e legenda.
function opcoesPadrao({ titulo, eixoX, eixoY, xLinear = false, beginAtZero = false, tooltip }) {
  const cor = "#8998aa";
  const opcoes = {
    maintainAspectRatio: false,
    scales: {
      x: { ticks: { color: cor }, grid: xLinear ? { color: "#263546" } : { display: false }, title: { display: true, text: eixoX, color: cor } },
      y: { ticks: { color: cor }, grid: { color: "#263546" }, beginAtZero, title: { display: true, text: eixoY, color: cor } },
    },
    plugins: {
      title: { display: true, text: titulo, color: "#e6edf5", font: { size: 13, weight: "600" } },
      legend: { display: true, labels: { color: "#cbd6e1", usePointStyle: true } },
    },
  };
  if (xLinear) opcoes.scales.x.type = "linear";
  if (tooltip) opcoes.plugins.tooltip = tooltip;
  return opcoes;
}

function formatarModas(item) {
  if (item.amodal) return "amodal";
  return item.modas.map((valor) => formatar(valor)).join("; ");
}

function construirCartoes(dados, time) {
  const areaCartoes = document.getElementById("cartoes-resumo");
  if (!areaCartoes) {
    return;
  }
  const estatistica = dados.por_time[time];
  const itens = [
    ["Média", estatistica.media, "desempenho médio por jogo"],
    ["Mediana", estatistica.mediana, "metade dos jogos abaixo"],
    ["Desvio padrão", estatistica.desvio_padrao, "variabilidade amostral"],
    ["CV", `${formatar(estatistica.cv_percentual)}%`, "dispersão relativa"],
  ];
  areaCartoes.innerHTML = itens.map((item) =>
    `<div class="cartao"><div class="rotulo">${item[0]}</div><div class="valor">${typeof item[1] === "string" ? item[1] : formatar(item[1])}</div><div class="detalhe">${item[2]}</div></div>`
  ).join("");
}

function construirBarras(dados) {
  const elemento = document.getElementById("grafico-barras");
  if (!elemento || typeof Chart === "undefined") {
    return;
  }
  destruirGrafico("barras");
  graficos.barras = new Chart(elemento, {
    type: "bar",
    data: { labels: Object.keys(dados.comparativo), datasets: [
      { label: "Média", data: Object.values(dados.comparativo).map((item) => item.media), backgroundColor: cores[0], borderRadius: 4 },
      { label: "Mediana", data: Object.values(dados.comparativo).map((item) => item.mediana), backgroundColor: cores[1], borderRadius: 4 },
      { label: "Moda", data: Object.values(dados.comparativo).map((item) => item.moda), backgroundColor: "#8a7cff", borderRadius: 4 },
    ] },
    options: opcoesPadrao({
      titulo: `Média, mediana e moda de ${dados.variavel} por time`,
      eixoX: "Time",
      eixoY: `${dados.variavel} (${dados.unidade})`,
      beginAtZero: true,
      tooltip: { callbacks: { label: (ctx) => {
        const item = Object.values(dados.comparativo)[ctx.dataIndex];
        if (ctx.dataset.label === "Moda") return `Moda: ${formatarModas(item)} ${dados.unidade}`;
        return `${ctx.dataset.label}: ${formatar(ctx.parsed.y)} ${dados.unidade}`;
      } } },
    }),
  });
}

function construirBoxplot(dados) {
  const elemento = document.getElementById("grafico-boxplot");
  if (!elemento || typeof Chart === "undefined") {
    return;
  }
  destruirGrafico("boxplot");
  const time = document.getElementById("seletor-time").value;
  const selecionados = time === "Todos" ? dados.comparativo : dados.por_time;
  const nomes = Object.keys(selecionados);
  const itens = Object.values(selecionados);
  const unidade = dados.unidade;
  graficos.boxplot = new Chart(elemento, {
    type: "boxplot",
    data: { labels: nomes, datasets: [
      {
        label: "Caixa Q1–Q3, mediana, bigodes e outliers",
        backgroundColor: "#55b6ff55",
        borderColor: cores[0],
        outlierBackgroundColor: "#ff7d7d",
        outlierBorderColor: "#ff7d7d",
        outlierRadius: 3,
        meanRadius: 0, // a média é desenhada pelo conjunto "Média" abaixo, com legenda
        itemRadius: 0,
        data: itens.map((item) => ({
          min: item.minimo,
          q1: item.q1,
          median: item.mediana,
          q3: item.q3,
          max: item.maximo,
          // Bigodes = valor observado mais extremo dentro de Q1−1,5×IQR e Q3+1,5×IQR.
          whiskerMin: item.bigode_inferior,
          whiskerMax: item.bigode_superior,
          mean: item.media,
          outliers: item.outliers,
        })),
      },
      {
        type: "line", label: "Média", showLine: false,
        pointStyle: "crossRot", pointRadius: 8, pointBorderWidth: 2, borderColor: "#ffd166", backgroundColor: "#ffd166",
        data: nomes.map((nome, i) => ({ x: nome, y: itens[i].media })),
      },
      {
        type: "line", label: "Moda", showLine: false,
        pointStyle: "rectRot", pointRadius: 6, borderColor: "#8a7cff", backgroundColor: "#8a7cff",
        data: nomes.flatMap((nome, i) => itens[i].modas.map((moda) => ({ x: nome, y: moda }))),
      },
    ] },
    options: opcoesPadrao({
      titulo: `Distribuição de ${dados.variavel} por jogo — boxplot de Tukey (1,5×IQR)`,
      eixoX: "Time",
      eixoY: `${dados.variavel} (${unidade})`,
      tooltip: { callbacks: { label: (ctx) => {
        const item = itens[nomes.indexOf(ctx.label)] || itens[ctx.dataIndex];
        if (ctx.dataset.label === "Média") return `Média: ${formatar(ctx.parsed.y)} ${unidade}`;
        if (ctx.dataset.label === "Moda") return `Moda: ${formatar(ctx.parsed.y)} ${unidade}`;
        return [
          `Bigodes: ${formatar(item.bigode_inferior)} a ${formatar(item.bigode_superior)}`,
          `Q1: ${formatar(item.q1)} · Mediana: ${formatar(item.mediana)} · Q3: ${formatar(item.q3)}`,
          `Limites de Tukey: ${formatar(item.limite_inferior)} a ${formatar(item.limite_superior)}`,
          `Média: ${formatar(item.media)} · Moda: ${formatarModas(item)}`,
          `Outliers: ${item.quantidade_outliers}${item.quantidade_outliers ? ` (${item.outliers.map((v) => formatar(v)).join("; ")})` : ""}`,
        ];
      } } },
    }),
  });
}

function construirHistograma(dados) {
  const elemento = document.getElementById("grafico-histograma");
  if (!elemento || typeof Chart === "undefined") {
    return;
  }
  destruirGrafico("histograma");
  // Faixas (Freedman–Diaconis) e KDE (scipy.stats.gaussian_kde) vêm prontas do servidor.
  const hist = dados.histograma;
  const time = document.getElementById("seletor-time").value;
  const nomesTimes = Object.keys(hist.times);
  const exibidos = time === "Todos" ? nomesTimes : [time];
  const datasets = [];
  exibidos.forEach((nome) => {
    const cor = cores[nomesTimes.indexOf(nome)];
    const item = hist.times[nome];
    datasets.push({
      type: "bar", label: `${nome} — jogos por faixa`,
      data: hist.centros.map((x, i) => ({ x, y: item.contagens[i] })),
      backgroundColor: `${cor}66`, borderColor: cor, borderWidth: 1,
      barPercentage: 1, categoryPercentage: 1, order: 2,
    });
    datasets.push({
      type: "line", label: `${nome} — KDE (banda ${formatar(item.banda_kde)})`,
      data: item.kde_x.map((x, i) => ({ x, y: item.kde_frequencia[i] })),
      borderColor: cor, borderWidth: 2, pointRadius: 0, fill: false, tension: 0.3, order: 1,
    });
  });
  const opcoes = opcoesPadrao({
    titulo: `Histograma de ${dados.variavel} com KDE — faixas de ${hist.largura} (Freedman–Diaconis)`,
    eixoX: `${dados.variavel} (${dados.unidade})`,
    eixoY: "Frequência (nº de jogos)",
    xLinear: true,
    beginAtZero: true,
    tooltip: { callbacks: { label: (ctx) => ctx.dataset.type === "bar"
      ? `${ctx.dataset.label}: ${ctx.parsed.y} jogos em [${formatar(ctx.parsed.x - hist.largura / 2, 1)}; ${formatar(ctx.parsed.x + hist.largura / 2, 1)})`
      : `${ctx.dataset.label}: ${formatar(ctx.parsed.y)} jogos (densidade × n × largura)` } },
  });
  opcoes.parsing = false;
  opcoes.scales.x.min = hist.bordas[0];
  opcoes.scales.x.max = hist.bordas[hist.bordas.length - 1];
  graficos.histograma = new Chart(elemento, { type: "bar", data: { datasets }, options: opcoes });
}

function construirInterpretacao(dados) {
  if (!document.getElementById("texto-interpretacao")) {
    return;
  }
  const selecionados = dados.comparativo;
  const mavericks = selecionados["Dallas Mavericks"];
  const pacers = selecionados["Indiana Pacers"];
  const lider = mavericks.media >= pacers.media ? "Dallas Mavericks" : "Indiana Pacers";
  const regular = mavericks.cv <= pacers.cv ? "Dallas Mavericks" : "Indiana Pacers";
  document.getElementById("texto-interpretacao").innerHTML = `<p><strong>${lider}</strong> apresenta a maior média de ${dados.variavel}, com <strong>${formatar(selecionados[lider].media)}</strong> ${dados.unidade}. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.</p><p>Em regularidade relativa, <strong>${regular}</strong> tem o menor CV (${formatar(selecionados[regular].cv_percentual)}%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.</p><p>A assimetria é <strong>${dados.comparativo[lider].classificacao_assimetria}</strong>. Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.</p>`;
}

async function atualizarPainel() {
  const seletorTime = document.getElementById("seletor-time");
  const seletorVariavel = document.getElementById("seletor-variavel");
  if (!seletorTime || !seletorVariavel) {
    return;
  }
  const time = seletorTime.value;
  const variavel = seletorVariavel.value;
  const resposta = await fetch(`/api/estatisticas?time=${encodeURIComponent(time)}&variavel=${encodeURIComponent(variavel)}`);
  const dados = await resposta.json();
  document.getElementById("titulo-metrica").textContent = variavel;
  construirCartoes(dados, time); construirBarras(dados); construirBoxplot(dados); construirHistograma(dados); construirInterpretacao(dados);
  destacarLinhasDescritivas(variavel);
}

function destacarLinhasDescritivas(variavel) {
  document.querySelectorAll("#corpo-tabela-descritiva tr[data-variavel]").forEach((linha) => {
    linha.classList.toggle("linha-destacada", linha.dataset.variavel === variavel);
  });
}

function descreverOutliers(item) {
  if (!item.quantidade_outliers) return "—";
  return item.outliers_detalhe.map((o) => {
    const jogo = [o.data, o.confronto].filter(Boolean).map(escaparHtml).join(" · ");
    return `<span class="outlier-item"><b>${formatar(o.valor)}</b>${jogo ? ` <small>(${jogo})</small>` : ""}</span>`;
  }).join("");
}

async function carregarTabelaDescritiva() {
  const corpo = document.getElementById("corpo-tabela-descritiva");
  if (!corpo) {
    return;
  }
  const resposta = await fetch("/api/descritivas");
  const dados = await resposta.json();
  const num = (valor) => `<td class="num">${formatar(valor)}</td>`;
  corpo.innerHTML = dados.variaveis.map((grupo) => dados.times.map((time, indice) => {
    const item = grupo.times[time];
    const celulaVariavel = indice === 0
      ? `<td rowspan="${dados.times.length}" class="celula-variavel"><strong>${escaparHtml(grupo.variavel)}</strong><small>${escaparHtml(grupo.unidade)}</small></td>`
      : "";
    return `<tr data-variavel="${escaparHtml(grupo.variavel)}" class="${indice === 0 ? "inicio-grupo" : ""}">${celulaVariavel}<td>${escaparHtml(time)}</td><td class="num">${item.n}</td>${num(item.media)}${num(item.mediana)}<td class="num">${formatarModas(item)}</td>${num(item.minimo)}${num(item.maximo)}${num(item.amplitude)}${num(item.desvio_padrao)}${num(item.variancia)}${num(item.q1)}${num(item.q3)}${num(item.iqr)}<td class="num">${formatar(item.limite_inferior)} a ${formatar(item.limite_superior)}</td><td class="num">${item.quantidade_outliers}</td><td class="outliers">${descreverOutliers(item)}</td></tr>`;
  }).join("")).join("");
  const seletorVariavel = document.getElementById("seletor-variavel");
  if (seletorVariavel) destacarLinhasDescritivas(seletorVariavel.value);
}

// ---------------------------------------------------------------------------
// Página de Qualidade dos dados.
// ---------------------------------------------------------------------------

const CORES_METODOS = { zscore: "#55b6ff", iqr: "#6fd3a5", grubbs: "#ffad66", ecod: "#c49bff" };
const ROTULOS_METODOS = { zscore: "Z-score", iqr: "IQR", grubbs: "Grubbs", ecod: "ECOD", knn: "K-NN", dbscan: "DBSCAN", lof: "LOF" };

// cabecalhos: [[rótulo, numérico?]]; linhas: [{celulas: [html], classe}]
function preencherTabela(id, cabecalhos, linhas) {
  const tabela = document.getElementById(id);
  if (!tabela) return;
  tabela.innerHTML = `<thead><tr>${cabecalhos.map(([r, num]) => `<th${num ? " class=\"num\"" : ""}>${r}</th>`).join("")}</tr></thead><tbody>`
    + linhas.map((linha) => `<tr class="${linha.classe || ""}">${linha.celulas.map((c, i) => `<td${cabecalhos[i][1] ? " class=\"num\"" : ""}>${c}</td>`).join("")}</tr>`).join("")
    + "</tbody>";
}

function inteiro(valor) {
  return valor === null || valor === undefined ? "—" : Number(valor).toLocaleString("pt-BR");
}

function listaValores(valores) {
  return valores.length ? `<small>${valores.map((v) => formatar(v)).join("; ")}</small>` : "";
}

function contagemComValores(item) {
  return `<strong>${item.quantidade}</strong>${item.quantidade ? " " + listaValores(item.valores) : ""}`;
}

function etiquetaSimNao(sim, textoSim, textoNao) {
  return `<span class="etiqueta-classe ${sim ? "classe-forte" : "classe-consistente"}">${sim ? textoSim : textoNao}</span>`;
}

function cartaoTexto(titulo, subtitulo, itens) {
  return `<div class="cartao-texto"><h4>${escaparHtml(titulo)}</h4>${subtitulo ? `<p class="cartao-sub">${escaparHtml(subtitulo)}</p>` : ""}<dl>${itens.filter(([, v]) => v).map(([r, v]) => `<dt>${r}</dt><dd>${escaparHtml(v)}</dd>`).join("")}</dl></div>`;
}

async function carregarQualidade() {
  if (!document.querySelector("[data-pagina-qualidade]")) {
    return;
  }
  const resposta = await fetch("/api/qualidade");
  const dados = await resposta.json();
  const times = dados.times;

  // Cartões-resumo
  const totalAusentes = dados.ausentes.reduce((t, l) => t + (l.fonte || 0), 0);
  const dup = dados.duplicatas.fonte;
  const violacoes = dados.dominio.regras.reduce((t, r) => t + r.violacoes_fonte, 0);
  const cartoes = [
    ["Valores ausentes (fonte)", inteiro(totalAusentes), `em ${inteiro(dup.registros * dados.ausentes.length)} células`],
    ["Duplicatas (fonte bruta)", inteiro(dup.linha_inteira + dup.chave_time_jogo), `linha inteira ${dup.linha_inteira} · chave time+jogo ${dup.chave_time_jogo}`],
    ["Violações de domínio", inteiro(violacoes), `${dados.dominio.regras.length} regras verificadas na fonte`],
    ["Jogos com prorrogação", inteiro(dados.dominio.jogos_prorrogacao.length), "MIN 265 ou 290 no recorte — válidos"],
  ];
  document.getElementById("q-cartoes").innerHTML = cartoes.map(([r, v, d]) =>
    `<div class="cartao"><div class="rotulo">${r}</div><div class="valor">${v}</div><div class="detalhe">${escaparHtml(d)}</div></div>`).join("");

  // 1. Ausentes por coluna
  const celulaAusente = (q, p) => (q === null ? "—" : `${inteiro(q)} <small>(${formatar(p)}%)</small>`);
  preencherTabela("q-ausentes",
    [["Coluna"], ["Descrição"], [`Fonte completa (n = ${inteiro(dup.registros)})`, true], [`Recorte bruto (n = ${inteiro(dados.duplicatas.recorte.registros)})`, true], [`Após tratamento (n = ${inteiro(dados.duplicatas.registros_tratados)})`, true]],
    dados.ausentes.map((l) => ({ celulas: [`<code>${escaparHtml(l.coluna)}</code>`, escaparHtml(l.nome), celulaAusente(l.fonte, l.fonte_pct), celulaAusente(l.recorte, l.recorte_pct), celulaAusente(l.tratado, l.tratado_pct)] })));

  // 2. Mecanismos
  document.getElementById("q-mecanismos").innerHTML = dados.mecanismos.map((m) =>
    cartaoTexto(`${m.sigla} — ${m.nome}`, "", [["Definição", m.definicao], ["Exemplo na NBA", m.exemplo], ["Consequência", m.consequencia]])).join("");

  // 3. Testes + demonstração
  document.getElementById("q-testes").innerHTML = dados.testes_ausencia.map((t) =>
    cartaoTexto(t.nome, t.referencia, [["Hipóteses", t.hipotese], ["Como funciona", t.como], ["Estatística", t.estatistica], ["Decisão", t.decisao], ["Por que usar", t.porque], ["Limitações", t.limitacoes], ["Nesta base", t.status_base_real], ["Neste site", t.implementado ? "Implementado e aplicado na demonstração abaixo." : "Apresentado em teoria (não implementado)."]])).join("");
  const demo = dados.demonstracao;
  document.getElementById("q-demo-nota").textContent =
    `Cópias do recorte com ${demo.variavel_alvo} apagado de propósito (semente ${demo.semente}); variáveis: ${demo.variaveis.join(", ")}. Decisão com α = ${formatar(demo.alfa)}. A base real não é alterada.`;
  preencherTabela("q-demo",
    [["Cenário"], ["Como a ausência foi gerada"], ["Ausentes", true], ["Little d²", true], ["gl", true], ["p-valor", true], ["Little"], ["Fairclough LR", true], ["gl", true], ["p-valor", true], ["Fairclough"]],
    demo.cenarios.map((c) => ({ celulas: [
      `<strong>${escaparHtml(c.nome)}</strong>`, `<small>${escaparHtml(c.descricao)}</small>`, `${c.ausentes} de ${c.n}`,
      formatar(c.little.estatistica), c.little.gl, formatar(c.little.p_valor, 4), etiquetaSimNao(c.little.rejeita_mcar, "rejeita MCAR", "não rejeita MCAR"),
      formatar(c.fairclough.estatistica), c.fairclough.gl, formatar(c.fairclough.p_valor, 4), etiquetaSimNao(c.fairclough.rejeita_mcar, "rejeita MCAR", "não rejeita MCAR"),
    ] })));
  const variaveisCoef = demo.cenarios[0].fairclough.coeficientes.map((c) => c.variavel);
  preencherTabela("q-demo-coef",
    [["Fairclough: preditor (padronizado)"], ...demo.cenarios.flatMap((c) => [[`${c.nome}: razão de chances`, true], ["p (Wald)", true]])],
    variaveisCoef.map((v, i) => ({ celulas: [v, ...demo.cenarios.flatMap((c) => [formatar(c.fairclough.coeficientes[i].razao_chances), formatar(c.fairclough.coeficientes[i].p_valor, 4)])] })));

  // 4. Duplicatas
  const rec = dados.duplicatas.recorte;
  preencherTabela("q-duplicatas", [["Verificação"], ["Fonte completa", true], ["Recorte do grupo", true]], [
    { celulas: ["Registros", inteiro(dup.registros), inteiro(rec.registros)] },
    { celulas: ["Linhas inteiras repetidas", inteiro(dup.linha_inteira), inteiro(rec.linha_inteira)] },
    { celulas: ["Chave (TEAM_NAME, Game_ID) repetida", inteiro(dup.chave_time_jogo), inteiro(rec.chave_time_jogo)] },
    { celulas: ["Game_ID distintos", inteiro(dup.jogos_distintos), "—"] },
    { celulas: ["Game_ID fora do par (≠ 2 registros)", inteiro(dup.jogos_fora_do_par), "—"] },
    { celulas: ["Removidos pelo tratamento", "—", inteiro(dados.duplicatas.removidos_no_tratamento)] },
  ]);

  // 5. Zeros e negativos
  const comOcorrencia = dados.zeros_negativos.filter((z) => z.zeros || z.negativos);
  preencherTabela("q-zeros", [["Coluna"], ["Zeros", true], ["Negativos", true], ["Significado"]],
    comOcorrencia.map((z) => ({ celulas: [`<code>${escaparHtml(z.coluna)}</code><small class="unidade">${escaparHtml(z.nome)}</small>`, inteiro(z.zeros), inteiro(z.negativos), `<small>${escaparHtml(z.significado)}</small>`] }))
      .concat([{ celulas: [`<small>Demais ${dados.zeros_negativos.length - comOcorrencia.length} colunas</small>`, "0", "0", "<small>sem zeros nem negativos.</small>"] }]));

  // 6. Domínio
  preencherTabela("q-dominio", [["Regra"], ["Justificativa"], ["Violações na fonte", true], ["Violações no recorte", true]],
    dados.dominio.regras.map((r) => ({ celulas: [`<strong>${escaparHtml(r.regra)}</strong>`, `<small>${escaparHtml(r.descricao)}</small>`, inteiro(r.violacoes_fonte), inteiro(r.violacoes_recorte)] })));
  const fonteMin = Object.fromEntries(dados.dominio.minutos_fonte.map((m) => [m.minutos, m.registros]));
  preencherTabela("q-minutos", [["MIN", true], ["Prorrogações", true], ["Registros na fonte", true], ["Registros no recorte", true], ["Leitura"]],
    dados.dominio.minutos_recorte.map((m) => ({ celulas: [inteiro(m.minutos), m.prorrogacoes ?? "fora", inteiro(fonteMin[m.minutos]), inteiro(m.registros), `<small>${m.prorrogacoes === 0 ? "tempo normal: 48 min × 5 jogadores" : m.prorrogacoes ? `240 + ${m.prorrogacoes} × 25 (5 min × 5 jogadores)` : "fora do domínio 240 + 25k"}</small>`] })));
  preencherTabela("q-prorrogacao", [["Time"], ["Data"], ["Confronto"], ["MIN", true], ["Prorrogações", true], ["PTS", true]],
    dados.dominio.jogos_prorrogacao.map((j) => ({ celulas: [escaparHtml(j.time), j.data, escaparHtml(j.confronto), inteiro(j.minutos), j.prorrogacoes, inteiro(j.pontos)] })));

  // 7. Outliers por coluna
  const par = dados.parametros;
  document.getElementById("q-parametros").textContent =
    `Z-score |z| > ${formatar(par.limiar_zscore, 0)} · IQR 1,5×IQR (Tukey) · Grubbs bilateral iterativo, α = ${formatar(par.alfa_grubbs)} · ECOD (pyod), contamination = ${formatar(par.contaminacao_ecod)}`;
  const metodos = ["zscore", "iqr", "grubbs", "ecod"];
  const linhasOutliers = [];
  dados.outliers_por_coluna.forEach((col) => {
    times.forEach((time, i) => {
      const r = col.times[time];
      linhasOutliers.push({
        classe: [i === 0 ? "inicio-grupo" : "", col.analisada ? "linha-destacada" : ""].join(" "),
        celulas: [
          i === 0 ? `<code>${escaparHtml(col.coluna)}</code><small class="unidade">${escaparHtml(col.nome)}${col.variavel ? " · analisada" : ""}</small>` : "",
          escaparHtml(time), r.n,
          `${contagemComValores(r.zscore)}<small class="unidade">máx. |z| = ${formatar(r.zscore.z_maximo)}</small>`,
          `${contagemComValores(r.iqr)}<small class="unidade">[${formatar(r.iqr.limite_inferior)}; ${formatar(r.iqr.limite_superior)}]</small>`,
          contagemComValores(r.grubbs),
          r.grubbs.shapiro_p === null ? "—" : `${formatar(r.grubbs.shapiro_p, 4)}${r.grubbs.shapiro_p < 0.05 ? " <span class=\"aviso\">não normal</span>" : ""}`,
          contagemComValores(r.ecod),
        ],
      });
    });
  });
  preencherTabela("q-outliers", [["Coluna"], ["Time"], ["n", true], ["Z-score"], ["IQR / Tukey"], ["Grubbs"], ["Shapiro-Wilk p", true], ["ECOD"]], linhasOutliers);

  const canvas = document.getElementById("grafico-outliers-coluna");
  if (canvas && typeof Chart !== "undefined") {
    const labels = dados.outliers_por_coluna.map((c) => c.coluna);
    const datasets = metodos.map((m) => ({
      label: ROTULOS_METODOS[m], backgroundColor: CORES_METODOS[m], borderRadius: 3,
      data: dados.outliers_por_coluna.map((c) => times.reduce((t, time) => t + c.times[time][m].quantidade, 0)),
    }));
    const opcoes = opcoesPadrao({ titulo: "Outliers por coluna e método (soma dos dois times)", eixoX: "Coluna de box-score", eixoY: "Valores marcados (nº de jogos)", beginAtZero: true });
    opcoes.scales.y.ticks.precision = 0;
    destruirGrafico("outliersColuna");
    graficos.outliersColuna = new Chart(canvas, { type: "bar", data: { labels, datasets }, options: opcoes });
  }

  // 8. Grubbs passo a passo (7 variáveis analisadas)
  const linhasGrubbs = [];
  dados.outliers_por_coluna.filter((c) => c.analisada).forEach((col) => {
    times.forEach((time, i) => {
      col.times[time].grubbs.passos.forEach((p, k) => {
        linhasGrubbs.push({
          classe: i === 0 && k === 0 ? "inicio-grupo" : "",
          celulas: [k === 0 ? `${escaparHtml(col.variavel)} <small class="unidade">${escaparHtml(col.coluna)}</small>` : "", k === 0 ? escaparHtml(time) : "", k + 1, p.n,
            formatar(p.media), formatar(p.desvio), formatar(p.valor), formatar(p.g, 4), formatar(p.g_critico, 4),
            etiquetaSimNao(p.significativo, "outlier — removido", "não significativo — para")],
        });
      });
    });
  });
  preencherTabela("q-grubbs", [["Variável"], ["Time"], ["Passo", true], ["n", true], ["Média", true], ["DP", true], ["Valor testado", true], ["G", true], ["G crítico", true], ["Decisão"]], linhasGrubbs);

  // 9. Multivariados
  const mv = dados.outliers_multivariados;
  const linhasMv = [];
  times.forEach((time) => {
    const info = mv.times[time];
    ["ecod", "knn", "dbscan", "lof"].forEach((m, k) => {
      const jogos = info.metodos[m].jogos;
      linhasMv.push({
        classe: k === 0 ? "inicio-grupo" : "",
        celulas: [k === 0 ? `${escaparHtml(time)}<small class="unidade">${info.n} jogos · ${info.em_todos} marcados pelos 4</small>` : "", ROTULOS_METODOS[m], `<strong>${info.metodos[m].quantidade}</strong>`,
          jogos.map((j) => `<span class="outlier-item">${j.data} ${escaparHtml(j.confronto)} <small>${mv.colunas.map((c) => `${c} ${formatar(j.valores[c], 0)}`).join(" · ")}</small></span>`).join("") || "<small>nenhum</small>"],
      });
    });
  });
  preencherTabela("q-multivariados", [["Time"], ["Método"], ["Jogos", true], ["Quais (data, confronto e valores)"]], linhasMv);

  // 10. Teoria
  document.getElementById("q-metodos").innerHTML = dados.metodos.map((m) =>
    `<div class="cartao-texto"><h4>${escaparHtml(m.nome)} <span class="etiqueta-classe">${escaparHtml(m.tipo)}</span></h4><div class="formula formula-secundaria">${escaparHtml(m.formula)}</div><dl><dt>Ideia</dt><dd>${escaparHtml(m.como)}</dd><dt>Premissas</dt><dd>${escaparHtml(m.premissas)}</dd><dt>Parâmetros</dt><dd>${escaparHtml(m.parametros)}</dd></dl></div>`).join("");

  document.getElementById("interpretacao-qualidade").innerHTML = dados.secoes.map((secao, i) =>
    `<div class="secao-texto"><h4>${i + 1}. ${escaparHtml(secao.titulo)}</h4>${secao.paragrafos.map((p) => `<p>${escaparHtml(p)}</p>`).join("")}</div>`).join("");
}

async function carregarDicionario() {
  if (!document.getElementById("tabela-dicionario")) {
    return;
  }
  const resposta = await fetch("/api/dicionario"); const dados = await resposta.json();
  window.camposDicionario = dados.campos;
  const resumo = document.getElementById("resumo-dicionario");
  if (resumo) {
    resumo.textContent = `${dados.linhas} registros analisados e ${dados.colunas} campos documentados. Abaixo, explore o significado, o tratamento e a categoria de cada campo.`;
  }
  preencherFiltrosDicionario(dados.campos);
  atualizarDicionario();
}

function escaparHtml(valor) {
  return String(valor).replace(/[&<>"']/g, (caractere) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[caractere]));
}

function preencherFiltrosDicionario(campos) {
  const tipos = [...new Set(campos.map((item) => item.tipo))].sort();
  const categorias = [...new Set(campos.map((item) => item.categoria))].sort();
  document.getElementById("filtro-tipo-dicionario").innerHTML += tipos.map((tipo) => `<option value="${escaparHtml(tipo)}">${escaparHtml(tipo)}</option>`).join("");
  document.getElementById("filtro-categoria-dicionario").innerHTML += categorias.map((categoria) => `<option value="${escaparHtml(categoria)}">${escaparHtml(categoria)}</option>`).join("");
}

function atualizarDicionario() {
  const campos = window.camposDicionario || [];
  const pesquisa = (document.getElementById("pesquisa-dicionario").value || "").toLowerCase().trim();
  const tipo = document.getElementById("filtro-tipo-dicionario").value;
  const categoria = document.getElementById("filtro-categoria-dicionario").value;
  const filtrados = campos.filter((item) => {
    const texto = [item.coluna_original, item.nome_apresentacao, item.descricao, item.explicacao, item.tratamento].join(" ").toLowerCase();
    return texto.includes(pesquisa) && (!tipo || item.tipo === tipo) && (!categoria || item.categoria === categoria);
  });
  document.getElementById("contador-dicionario").textContent = `${filtrados.length} de ${campos.length} campos`;
  document.getElementById("estado-vazio-dicionario").style.display = filtrados.length ? "none" : "block";
  document.getElementById("cards-dicionario").innerHTML = criarCardsDicionario(filtrados);
  document.getElementById("tabela-dicionario").innerHTML = filtrados.map((item, indice) => `<tr class="linha-dicionario" data-indice="${indice}"><td><strong>${escaparHtml(item.coluna_original)}</strong></td><td>${escaparHtml(item.nome_apresentacao)}</td><td><span class="etiqueta-tipo">${escaparHtml(item.tipo)}</span></td><td><span class="etiqueta-categoria">${escaparHtml(item.categoria)}</span></td><td>${item.ausentes}</td><td><button class="botao-detalhes" type="button" aria-expanded="false">Ver explicação</button><div class="detalhe-campo"><strong>O que significa:</strong> ${escaparHtml(item.explicacao)}<br><strong>Tratamento:</strong> ${escaparHtml(item.tratamento)}</div></td></tr>`).join("");
  document.querySelectorAll(".botao-detalhes").forEach((botao) => botao.addEventListener("click", () => {
    const linha = botao.closest(".linha-dicionario");
    const aberto = linha.classList.toggle("aberto");
    botao.setAttribute("aria-expanded", aberto);
    botao.textContent = aberto ? "Ocultar explicação" : "Ver explicação";
  }));
}

function criarCardsDicionario(campos) {
  const categorias = {};
  campos.forEach((item) => { categorias[item.categoria] = (categorias[item.categoria] || 0) + 1; });
  return Object.entries(categorias).map(([nome, quantidade]) => `<div class="card-categoria"><span>${escaparHtml(nome)}</span><strong>${quantidade}</strong><small>campos encontrados</small></div>`).join("");
}

["pesquisa-dicionario", "filtro-tipo-dicionario", "filtro-categoria-dicionario"].forEach((id) => {
  const elemento = document.getElementById(id);
  if (elemento) elemento.addEventListener(elemento.tagName === "INPUT" ? "input" : "change", atualizarDicionario);
});

const seletorTime = document.getElementById("seletor-time");
const seletorVariavel = document.getElementById("seletor-variavel");
if (seletorTime && seletorVariavel) {
  seletorTime.addEventListener("change", atualizarPainel);
  seletorVariavel.addEventListener("change", atualizarPainel);
}
atualizarPainel();
carregarQualidade();
carregarDicionario();
carregarTabelaDescritiva();

// ---------------------------------------------------------------------------
// Páginas de Assimetria, CV e IQR: quadro-resumo, detalhe, gráfico e textos.
// ---------------------------------------------------------------------------

function pct(valor) {
  return valor === null || valor === undefined ? "—" : `${formatar(valor)}%`;
}

function linhaReferencia(rotulo, valor, labels, cor) {
  return {
    type: "line", label: rotulo, data: labels.map(() => valor),
    borderColor: cor, borderDash: [6, 4], borderWidth: 1.5, pointRadius: 0, fill: false,
  };
}

function barrasPorTime(dados, valorDe) {
  return dados.times.map((time, i) => ({
    type: "bar", label: time, backgroundColor: cores[i], borderRadius: 3,
    data: dados.quadro.map((q) => valorDe(q, time)),
  }));
}

const CONFIG_MEDIDAS = {
  assimetria: {
    quadro: (v) => formatar(v),
    cabecalhoQuadro: "Variável",
    detalhe: [
      ["Variável", (l) => escaparHtml(l.variavel)],
      ["Time", (l) => escaparHtml(l.time)],
      ["n", (l) => l.n, true],
      ["G1", (l) => formatar(l.g1), true],
      ["Direção", (l) => escaparHtml(l.direcao)],
      ["Intensidade", (l) => `<span class="etiqueta-classe classe-${l.intensidade.split(" ")[0]}">${escaparHtml(l.intensidade)}</span>`],
      ["Bowley", (l) => formatar(l.bowley), true],
      ["Média − mediana", (l) => formatar(l.media_menos_mediana), true],
      ["G1 sem outliers", (l) => formatar(l.g1_sem_outliers), true],
      ["Outliers", (l) => l.quantidade_outliers, true],
    ],
    grafico: (dados, labels) => ({
      datasets: [
        ...barrasPorTime(dados, (q, time) => q.valores[time]),
        linhaReferencia("Limite moderada (±0,5)", 0.5, labels, "#ffd166"),
        { ...linhaReferencia("", -0.5, labels, "#ffd166") },
        linhaReferencia("Limite forte (±1)", 1, labels, "#ff7d7d"),
        { ...linhaReferencia("", -1, labels, "#ff7d7d") },
      ],
      opcoes: opcoesPadrao({
        titulo: "Coeficiente de assimetria G1 por variável e time",
        eixoX: "Variável", eixoY: "G1 (adimensional)",
      }),
    }),
  },
  cv: {
    quadro: (v) => pct(v),
    cabecalhoQuadro: "Variável",
    detalhe: [
      ["Variável", (l) => escaparHtml(l.variavel)],
      ["Time", (l) => escaparHtml(l.time)],
      ["Média", (l) => formatar(l.media), true],
      ["DP (n − 1)", (l) => formatar(l.desvio_padrao), true],
      ["CV", (l) => pct(l.cv_percentual), true],
      ["Leitura", (l) => `<span class="etiqueta-classe classe-${l.classe}">${escaparHtml(l.classe)}</span>`],
      ["Validade", (l, d) => (l.cautela ? `<span class="aviso">cautela: média &lt; ${formatar(d.media_minima, 0)}</span>` : "adequado")],
      ["Piso Poisson", (l) => pct(l.cv_poisson_ref), true],
      ["CV IQR/Mediana", (l) => pct(l.cv_robusto_iqr), true],
      ["G1", (l) => formatar(l.g1), true],
    ],
    grafico: (dados, labels) => ({
      datasets: [
        ...barrasPorTime(dados, (q, time) => q.valores[time]),
        {
          type: "line", label: "Piso Poisson 100/√média (média dos times)", showLine: false,
          pointStyle: "line", pointRadius: 14, pointBorderWidth: 3, borderColor: "#ffd166", backgroundColor: "#ffd166",
          data: labels.map((rotulo) => {
            const linhas = dados.linhas.filter((l) => l.variavel === rotulo);
            return linhas.reduce((soma, l) => soma + l.cv_poisson_ref, 0) / linhas.length;
          }),
        },
        linhaReferencia(`Até ${dados.faixas[0]}%: consistente`, dados.faixas[0], labels, "#6fd3a5"),
        linhaReferencia(`Acima de ${dados.faixas[1]}%: irregular`, dados.faixas[1], labels, "#ff7d7d"),
      ],
      opcoes: opcoesPadrao({
        titulo: "Coeficiente de variação por variável e time",
        eixoX: "Variável", eixoY: "CV (%)", beginAtZero: true,
      }),
    }),
  },
  iqr: {
    quadro: (v) => formatar(v),
    cabecalhoQuadro: "Variável (unidade)",
    detalhe: [
      ["Variável", (l) => `${escaparHtml(l.variavel)}<small class="unidade">${escaparHtml(l.unidade)}</small>`],
      ["Time", (l) => escaparHtml(l.time)],
      ["Q1", (l) => formatar(l.q1), true],
      ["Q3", (l) => formatar(l.q3), true],
      ["IQR", (l) => `<strong>${formatar(l.iqr)}</strong>`, true],
      ["Amplitude", (l) => formatar(l.amplitude), true],
      ["Amp. ÷ IQR", (l) => formatar(l.razao_amplitude_iqr), true],
      ["DP", (l) => formatar(l.desvio_padrao), true],
      ["σ robusto", (l) => formatar(l.sigma_robusto), true],
      ["DP sem outliers", (l) => formatar(l.desvio_sem_outliers), true],
      ["IQR sem outliers", (l) => formatar(l.iqr_sem_outliers), true],
      ["Limites (1,5×IQR)", (l) => `${formatar(l.limite_inferior)} a ${formatar(l.limite_superior)}`, true],
      ["Outliers 1,5×", (l) => (l.quantidade_outliers ? `${l.quantidade_outliers} (${l.outliers.map((v) => formatar(v)).join("; ")})` : "0"), true],
      ["Outliers 3×", (l) => l.quantidade_outliers_3iqr, true],
    ],
    grafico: (dados, labels) => ({
      datasets: [
        ...barrasPorTime(dados, (q, time) => dados.linhas.find((l) => l.variavel === q.variavel && l.time === time).razao_amplitude_iqr),
        linhaReferencia("Referência normal (≈ 4)", 4, labels, "#ffd166"),
      ],
      opcoes: opcoesPadrao({
        titulo: "Amplitude dividida pelo IQR, por variável e time",
        eixoX: "Variável", eixoY: "Amplitude ÷ IQR (adimensional)", beginAtZero: true,
      }),
    }),
  },
};

async function carregarMedida() {
  const bloco = document.querySelector("[data-pagina-medida]");
  if (!bloco) {
    return;
  }
  const medida = bloco.dataset.paginaMedida;
  const config = CONFIG_MEDIDAS[medida];
  const resposta = await fetch(`/api/${medida}`);
  const dados = await resposta.json();

  document.getElementById("quadro-medida").innerHTML =
    `<thead><tr><th>${config.cabecalhoQuadro}</th>${dados.times.map((t) => `<th class="num">${escaparHtml(t)}</th>`).join("")}</tr></thead><tbody>`
    + dados.quadro.map((q) => `<tr><td><strong>${escaparHtml(q.variavel)}</strong><small class="unidade">${escaparHtml(q.unidade)}</small></td>${dados.times.map((t) => `<td class="num">${config.quadro(q.valores[t])}</td>`).join("")}</tr>`).join("")
    + "</tbody>";

  document.getElementById("detalhe-medida").innerHTML =
    `<thead><tr>${config.detalhe.map(([rotulo, , num]) => `<th${num ? " class=\"num\"" : ""}>${rotulo}</th>`).join("")}</tr></thead><tbody>`
    + dados.linhas.map((linha, indice) => `<tr class="${indice % dados.times.length === 0 ? "inicio-grupo" : ""}">${config.detalhe.map(([, valor, num]) => `<td${num ? " class=\"num\"" : ""}>${valor(linha, dados)}</td>`).join("")}</tr>`).join("")
    + "</tbody>";

  document.getElementById("interpretacao-medida").innerHTML = dados.secoes.map((secao, i) =>
    `<div class="secao-texto"><h4>${i + 1}. ${escaparHtml(secao.titulo)}</h4>${secao.paragrafos.map((p) => `<p>${escaparHtml(p)}</p>`).join("")}</div>`
  ).join("");

  const canvas = document.getElementById("grafico-medida");
  if (canvas && typeof Chart !== "undefined") {
    const labels = dados.quadro.map((q) => q.variavel);
    const { datasets, opcoes } = config.grafico(dados, labels);
    // Linhas de referência do lado negativo (rótulo vazio) ficam fora da legenda.
    opcoes.plugins.legend.labels.filter = (item) => item.text !== "";
    destruirGrafico("medida");
    graficos.medida = new Chart(canvas, { type: "bar", data: { labels, datasets }, options: opcoes });
  }
}

carregarMedida();
