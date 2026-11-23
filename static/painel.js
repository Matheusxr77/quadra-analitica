const cores = ["#55b6ff", "#ffad66"];
let graficos = {};

function formatar(valor, casas = 2) {
  if (valor === null || valor === undefined) return "—";
  return Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function destruirGrafico(nome) {
  if (graficos[nome]) graficos[nome].destroy();
}

// Todo gráfico: título, eixos com unidade e legenda.
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
        const linha = `${ctx.dataset.label}: ${formatar(ctx.parsed.y)} ${dados.unidade}`;
        // z da média do time (mesma referência do gráfico padronizado).
        const perfil = window.perfilZ && window.perfilZ.variaveis.find((v) => v.variavel === dados.variavel);
        const time = Object.keys(dados.comparativo)[ctx.dataIndex];
        if (ctx.dataset.label === "Média" && perfil && perfil.times[time]) return [linha, `z da média = ${formatar(perfil.times[time].z)}`];
        return linha;
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
          // Bigodes: valor observado mais extremo dentro dos limites de Tukey.
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
  // Faixas e KDE calculadas no servidor.
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

// Seções de texto do servidor: interpretação e, à parte, a metodologia.
function renderizarSecoes(secoes, numerar = true) {
  return secoes.map((secao, i) => {
    const titulo = `<h4>${numerar ? `${i + 1}. ` : ""}${escaparHtml(secao.titulo)}</h4>`;
    const paragrafos = (secao.paragrafos || []).map((p) => `<p>${escaparHtml(p)}</p>`).join("");
    const metodo = (secao.metodologia || []).map((m) => `<p class="nota-metodo"><span>Método</span> ${escaparHtml(m)}</p>`).join("");
    return `<div class="secao-texto">${titulo}${paragrafos}${metodo}</div>`;
  }).join("");
}

function construirInterpretacao(dados) {
  const area = document.getElementById("texto-interpretacao");
  if (!area) {
    return;
  }
  area.innerHTML = renderizarSecoes(dados.interpretacao || [], false);
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
// Qualidade dos dados
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

// Frase-resumo antes da tabela; sem ocorrências, a tabela completa fica recolhida em <details>.
function aplicarVerificacao(id, verificacao) {
  const tabela = document.getElementById(id);
  if (!tabela || !verificacao) return;
  const bloco = tabela.closest(".tabela-rolavel") || tabela;
  const anterior = bloco.closest("details.verificacoes");
  const alvo = anterior || bloco;
  if (alvo.previousElementSibling?.classList.contains("resumo-verificacao")) alvo.previousElementSibling.remove();
  if (anterior) anterior.replaceWith(bloco);
  const frase = document.createElement("p");
  frase.className = `resumo-verificacao ${verificacao.sem_ocorrencias ? "sem-ocorrencias" : "com-ocorrencias"}`;
  frase.textContent = verificacao.frase;
  bloco.before(frase);
  if (verificacao.sem_ocorrencias) {
    const detalhes = document.createElement("details");
    detalhes.className = "verificacoes";
    detalhes.innerHTML = "<summary>Ver todas as verificações</summary>";
    bloco.replaceWith(detalhes);
    detalhes.appendChild(bloco);
  }
}

function classes(...nomes) {
  return nomes.filter(Boolean).join(" ");
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

  // Ausentes por coluna
  const celulaAusente = (q, p) => (q === null ? "—" : `${inteiro(q)} <small>(${formatar(p)}%)</small>`);
  preencherTabela("q-ausentes",
    [["Coluna"], ["Descrição"], [`Fonte completa (n = ${inteiro(dup.registros)})`, true], [`Recorte bruto (n = ${inteiro(dados.duplicatas.recorte.registros)})`, true], [`Após tratamento (n = ${inteiro(dados.duplicatas.registros_tratados)})`, true]],
    dados.ausentes.map((l) => ({ classe: l.fonte || l.recorte || l.tratado ? "linha-ocorrencia" : "", celulas: [`<code>${escaparHtml(l.coluna)}</code>`, escaparHtml(l.nome), celulaAusente(l.fonte, l.fonte_pct), celulaAusente(l.recorte, l.recorte_pct), celulaAusente(l.tratado, l.tratado_pct)] })));
  aplicarVerificacao("q-ausentes", dados.verificacoes?.ausentes);

  // Mecanismos de ausência
  document.getElementById("q-mecanismos").innerHTML = dados.mecanismos.map((m) =>
    cartaoTexto(`${m.sigla} — ${m.nome}`, "", [["Definição", m.definicao], ["Exemplo na NBA", m.exemplo], ["Consequência", m.consequencia]])).join("");

  // Testes de mecanismo e exemplo didático
  const motivo = document.getElementById("q-motivo-testes");
  if (motivo) motivo.textContent = dados.motivo_testes;
  document.getElementById("q-testes").innerHTML = dados.testes_ausencia.map((t) =>
    `<div class="cartao-texto"><h4>${escaparHtml(t.nome)}</h4><p class="cartao-sub">${escaparHtml(t.referencia)}</p>${t.paragrafos.map((p) => `<p class="cartao-paragrafo">${escaparHtml(p)}</p>`).join("")}<dl>${[["Hipóteses", t.hipotese], ["Estatística", t.estatistica], ["Decisão", t.decisao], ["Limitações", t.limitacoes], ["Neste site", t.implementado ? "Implementado; usado apenas no exemplo didático abaixo." : "Apresentado em teoria (não implementado)."]].map(([r, v]) => `<dt>${r}</dt><dd>${escaparHtml(v)}</dd>`).join("")}</dl></div>`).join("");
  const demo = dados.demonstracao;
  document.getElementById("q-demo-nota").textContent =
    `Exemplo didático: cópias do recorte com ${demo.variavel_alvo} apagado de propósito (semente ${demo.semente}); variáveis: ${demo.variaveis.join(", ")}. Decisão com α = ${formatar(demo.alfa)}. A base real não é alterada e continua com 0 ausentes; os números abaixo só ilustram como os testes seriam lidos.`;
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

  // Duplicatas
  const rec = dados.duplicatas.recorte;
  const ocorre = (...v) => (v.some((x) => x > 0) ? "linha-ocorrencia" : "");
  preencherTabela("q-duplicatas", [["Verificação"], ["Fonte completa", true], ["Recorte do grupo", true]], [
    { celulas: ["Registros", inteiro(dup.registros), inteiro(rec.registros)] },
    { classe: ocorre(dup.linha_inteira, rec.linha_inteira), celulas: ["Linhas inteiras repetidas", inteiro(dup.linha_inteira), inteiro(rec.linha_inteira)] },
    { classe: ocorre(dup.chave_time_jogo, rec.chave_time_jogo), celulas: ["Chave (TEAM_NAME, Game_ID) repetida", inteiro(dup.chave_time_jogo), inteiro(rec.chave_time_jogo)] },
    { celulas: ["Game_ID distintos", inteiro(dup.jogos_distintos), "—"] },
    { classe: ocorre(dup.jogos_fora_do_par), celulas: ["Game_ID fora do par (≠ 2 registros)", inteiro(dup.jogos_fora_do_par), "—"] },
    { classe: ocorre(dados.duplicatas.removidos_no_tratamento), celulas: ["Removidos pelo tratamento", "—", inteiro(dados.duplicatas.removidos_no_tratamento)] },
  ]);
  aplicarVerificacao("q-duplicatas", dados.verificacoes?.duplicatas);

  // Zeros e negativos
  const comOcorrencia = dados.zeros_negativos.filter((z) => z.zeros || z.negativos);
  preencherTabela("q-zeros", [["Coluna"], ["Zeros", true], ["Negativos", true], ["Significado"]],
    comOcorrencia.map((z) => ({ classe: "linha-ocorrencia", celulas: [`<code>${escaparHtml(z.coluna)}</code><small class="unidade">${escaparHtml(z.nome)}</small>`, inteiro(z.zeros), inteiro(z.negativos), `<small>${escaparHtml(z.significado)}</small>`] }))
      .concat([{ celulas: [`<small>Demais ${dados.zeros_negativos.length - comOcorrencia.length} colunas</small>`, "0", "0", "<small>sem zeros nem negativos.</small>"] }]));
  aplicarVerificacao("q-zeros", dados.verificacoes?.zeros);

  // Fora de domínio
  const regrasOrdenadas = [...dados.dominio.regras].sort((a, b) => a.coluna.localeCompare(b.coluna));
  preencherTabela("q-dominio", [["Coluna"], ["Regra"], ["Justificativa"], [`Fora do domínio — fonte (n = ${inteiro(dup.registros)})`, true], [`Fora do domínio — recorte bruto (n = ${inteiro(rec.registros)})`, true]],
    regrasOrdenadas.map((r, i) => ({
      classe: classes(i === 0 || regrasOrdenadas[i - 1].coluna !== r.coluna ? "inicio-grupo" : "", r.violacoes_fonte || r.violacoes_recorte ? "linha-ocorrencia" : ""),
      celulas: [i === 0 || regrasOrdenadas[i - 1].coluna !== r.coluna ? `<code>${escaparHtml(r.coluna)}</code>` : "", `<strong>${escaparHtml(r.regra)}</strong>`, `<small>${escaparHtml(r.descricao)}</small>`, inteiro(r.violacoes_fonte), inteiro(r.violacoes_recorte)],
    })));
  aplicarVerificacao("q-dominio", dados.verificacoes?.dominio);
  const fonteMin = Object.fromEntries(dados.dominio.minutos_fonte.map((m) => [m.minutos, m.registros]));
  preencherTabela("q-minutos", [["MIN", true], ["Prorrogações", true], ["Registros na fonte", true], ["Registros no recorte", true], ["Leitura"]],
    dados.dominio.minutos_recorte.map((m) => ({ celulas: [inteiro(m.minutos), m.prorrogacoes ?? "fora", inteiro(fonteMin[m.minutos]), inteiro(m.registros), `<small>${m.prorrogacoes === 0 ? "tempo normal: 48 min × 5 jogadores" : m.prorrogacoes ? `240 + ${m.prorrogacoes} × 25 (5 min × 5 jogadores)` : "fora do domínio 240 + 25k"}</small>`] })));
  preencherTabela("q-prorrogacao", [["Time"], ["Data"], ["Confronto"], ["MIN", true], ["Prorrogações", true], ["PTS", true]],
    dados.dominio.jogos_prorrogacao.map((j) => ({ celulas: [escaparHtml(j.time), j.data, escaparHtml(j.confronto), inteiro(j.minutos), j.prorrogacoes, inteiro(j.pontos)] })));
  aplicarVerificacao("q-prorrogacao", dados.verificacoes?.prorrogacao);

  // Outliers por variável (7 métodos) e concordância
  const par = dados.parametros;
  const pv = dados.outliers_por_variavel;
  document.getElementById("q-parametros").textContent =
    `Z-score |z| > ${formatar(par.limiar_zscore, 0)} · IQR 1,5×IQR (Tukey) · Grubbs bilateral iterativo, α = ${formatar(par.alfa_grubbs)} · ECOD, K-NN, DBSCAN e LOF com limiares calibrados para a taxa de referência de ${formatar(par.taxa_referencia * 100)}% (a da regra de Tukey numa normal). Parâmetros por tamanho de amostra: `
    + Object.values(pv.parametros_por_n).map((c) => `n = ${c.n}: k = ${c.knn_k}, corte K-NN ${formatar(c.knn_corte)} σ; DBSCAN ε = ${formatar(c.dbscan_eps)} σ, min_samples = ${c.dbscan_min_samples}; LOF > ${formatar(c.lof_corte)} (n_neighbors = ${c.lof_vizinhos})`).join(" · ");
  const marcaJogo = (j) => `<span class="outlier-item">${formatar(j.valor, 0)} <small>${j.data} vs ${escaparHtml(j.adversario || "?")}</small></span>`;
  preencherTabela("q-por-variavel",
    [["Variável (unidade)"], ["Time"], ...pv.metodos.map((m) => [ROTULOS_METODOS[m]])],
    pv.detalhes.map((d, i) => ({
      classe: i % times.length === 0 ? "inicio-grupo" : "",
      celulas: [
        i % times.length === 0 ? `<strong>${escaparHtml(d.variavel)}</strong><small class="unidade">${escaparHtml(d.unidade)}</small>` : "",
        escaparHtml(d.time),
        ...pv.metodos.map((m) => `<strong>${d.metodos[m].quantidade}</strong>${d.metodos[m].jogos.map(marcaJogo).join("")}`),
      ],
    })));
  const linhasConcordancia = pv.detalhes.flatMap((d) => d.concordancia.map((j) => ({
    classe: j.total >= 4 ? "linha-destacada" : "",
    celulas: [escaparHtml(d.variavel), escaparHtml(d.time), j.data, `${escaparHtml(j.adversario || "?")} <small>(${j.mando || "—"})</small>`, formatar(j.valor), formatar(j.z),
      ...pv.metodos.map((m) => (j.metodos[m] ? "<span class=\"marca-sim\">✓</span>" : "<span class=\"marca-nao\">·</span>")), `<strong>${j.total} de ${pv.metodos.length}</strong>`],
  })));
  preencherTabela("q-concordancia",
    [["Variável"], ["Time"], ["Data"], ["Adversário"], ["Valor", true], ["z", true], ...pv.metodos.map((m) => [ROTULOS_METODOS[m]]), ["Métodos"]],
    linhasConcordancia.length ? linhasConcordancia : [{ celulas: ["Nenhum jogo marcado."] }]);
  preencherTabela("q-matriz", [["Método"], ...pv.metodos.map((m) => [ROTULOS_METODOS[m], true])],
    pv.metodos.map((a) => ({ celulas: [`<strong>${ROTULOS_METODOS[a]}</strong>`, ...pv.metodos.map((b) => (a === b ? `<strong>${pv.matriz_concordancia[a][b]}</strong>` : pv.matriz_concordancia[a][b]))] })));

  // Resumo nas 18 colunas
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

  // Grubbs passo a passo
  const linhasGrubbs = [];
  dados.outliers_por_coluna.filter((c) => c.analisada).forEach((col) => {
    times.forEach((time, i) => {
      col.times[time].grubbs.passos.forEach((p, k) => {
        linhasGrubbs.push({
          classe: classes(i === 0 && k === 0 ? "inicio-grupo" : "", p.significativo ? "linha-ocorrencia" : ""),
          celulas: [k === 0 ? `${escaparHtml(col.variavel)} <small class="unidade">${escaparHtml(col.coluna)}</small>` : "", k === 0 ? escaparHtml(time) : "", k + 1, p.n,
            formatar(p.media), formatar(p.desvio), formatar(p.valor), formatar(p.g, 4), formatar(p.g_critico, 4),
            etiquetaSimNao(p.significativo, "outlier — removido", "não significativo — para")],
        });
      });
    });
  });
  preencherTabela("q-grubbs", [["Variável"], ["Time"], ["Passo", true], ["n", true], ["Média", true], ["DP", true], ["Valor testado", true], ["G", true], ["G crítico", true], ["Decisão"]], linhasGrubbs);
  aplicarVerificacao("q-grubbs", dados.verificacoes?.grubbs);

  // Outliers multivariados
  const mv = dados.outliers_multivariados;
  document.getElementById("q-parametros-mv").textContent = "Variáveis em σ robusto ((x − mediana) ÷ (IQR/1,349)), por time. Cortes calibrados em normais de 7 dimensões: "
    + times.map((time) => { const c = mv.times[time].parametros; return `${time} (n = ${c.n}): K-NN k = ${c.knn_k}, corte ${formatar(c.knn_corte)}; DBSCAN ε = ${formatar(c.dbscan_eps)}, min_samples = ${c.dbscan_min_samples}; LOF > ${formatar(c.lof_corte)}; ECOD > ${formatar(c.ecod_corte)}`; }).join(" · ");
  const linhasMv = [];
  times.forEach((time) => {
    const info = mv.times[time];
    ["ecod", "knn", "dbscan", "lof"].forEach((m, k) => {
      const jogos = info.metodos[m].jogos;
      linhasMv.push({
        classe: classes(k === 0 ? "inicio-grupo" : "", info.metodos[m].quantidade ? "linha-ocorrencia" : ""),
        celulas: [k === 0 ? `${escaparHtml(time)}<small class="unidade">${info.n} jogos · ${info.em_todos} marcados pelos 4</small>` : "", ROTULOS_METODOS[m], `<strong>${info.metodos[m].quantidade}</strong>`,
          jogos.map((j) => `<span class="outlier-item">${j.data} ${escaparHtml(j.confronto)} <small>${mv.colunas.map((c) => `${c} ${formatar(j.valores[c], 0)}`).join(" · ")}</small></span>`).join("") || "<small>nenhum</small>"],
      });
    });
  });
  preencherTabela("q-multivariados", [["Time"], ["Método"], ["Jogos", true], ["Quais (data, confronto e valores)"]], linhasMv);
  aplicarVerificacao("q-multivariados", dados.verificacoes?.multivariados);

  // Teoria dos métodos
  document.getElementById("q-metodos").innerHTML = dados.metodos.map((m) =>
    `<div class="cartao-texto"><h4>${escaparHtml(m.nome)} <span class="etiqueta-classe">${escaparHtml(m.tipo)}</span></h4><div class="formula formula-secundaria">${escaparHtml(m.formula)}</div><dl><dt>Ideia</dt><dd>${escaparHtml(m.como)}</dd><dt>Premissas</dt><dd>${escaparHtml(m.premissas)}</dd><dt>Parâmetros</dt><dd>${escaparHtml(m.parametros)}</dd></dl></div>`).join("");

  document.getElementById("interpretacao-qualidade").innerHTML = renderizarSecoes(dados.secoes);
}

async function carregarDicionario() {
  if (!document.getElementById("tabela-dicionario")) {
    return;
  }
  const resposta = await fetch("/api/dicionario"); const dados = await resposta.json();
  window.camposDicionario = dados.campos;
  const resumo = document.getElementById("resumo-dicionario");
  if (resumo) {
    resumo.textContent = `${dados.linhas} registros analisados e ${dados.colunas} campos documentados. Abaixo, explore o tipo, o uso em modelos, o significado e o tratamento de cada campo.`;
  }
  const exemplos = {
    "numérica": "contagens e proporções do jogo",
    "categórica": "rótulos sem ordem nem aritmética",
    "texto": "texto livre",
    "data": "data convertida para datetime",
    "binária": "apenas 0 ou 1",
  };
  const cardsTipos = document.getElementById("cards-tipos");
  if (cardsTipos) {
    cardsTipos.innerHTML = Object.entries(dados.tipos).map(([tipo, quantidade]) => {
      const colunas = dados.campos.filter((c) => c.tipo === tipo).map((c) => c.coluna_original);
      return `<div class="card-categoria"><span>${escaparHtml(tipo)}</span><strong>${quantidade}</strong><small>${escaparHtml(exemplos[tipo] || "")}</small><small class="lista-colunas">${escaparHtml(colunas.length > 6 ? `${colunas.slice(0, 6).join(", ")}…` : colunas.join(", "))}</small></div>`;
    }).join("");
  }
  const resumoExclusoes = document.getElementById("resumo-exclusoes");
  if (resumoExclusoes) {
    resumoExclusoes.textContent = `${dados.exclusoes.length} colunas excluídas, WL como alvo e ${dados.features} colunas mantidas como variáveis explicativas`;
    preencherTabela("tabela-exclusoes", [["Coluna"], ["Tipo"], ["Por que é excluída"]],
      dados.exclusoes.map((e) => ({ celulas: [`<code>${escaparHtml(e.coluna)}</code>`, `<span class="etiqueta-tipo">${escaparHtml(e.tipo)}</span>`, escaparHtml(e.motivo)] })));
    const v = dados.vazamento;
    document.getElementById("texto-vazamento").innerHTML = [
      `<strong>Evidência do vazamento em W, L e W_PCT.</strong> Ordenando os jogos de cada time pela data, a variação de W de um jogo para o seguinte é igual ao resultado WL em <strong>${v.variacao_w_igual_wl} de ${v.jogos_com_anterior}</strong> jogos com jogo anterior, a variação de L é igual à derrota (1 − WL) em <strong>${v.variacao_l_igual_derrota} de ${v.jogos_com_anterior}</strong>, e W + L é exatamente o número do jogo em <strong>${v.w_mais_l_igual_numero_do_jogo} de ${v.jogos}</strong>. Ou seja, os acumulados são registrados depois do jogo e já contêm o resultado que se quer prever.`,
      `<strong>MATCHUP.</strong> A coluna bruta sai, mas o mando de quadra pode ser derivado dela: ${dados.mando.casa} jogos em casa ("vs.") e ${dados.mando.fora} fora ("@").`,
    ].map((p) => `<p>${p}</p>`).join("");
  }
  preencherFiltrosDicionario(dados.campos, Object.keys(dados.tipos));
  atualizarDicionario();
}

function escaparHtml(valor) {
  return String(valor).replace(/[&<>"']/g, (caractere) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[caractere]));
}

function preencherFiltrosDicionario(campos, ordemTipos) {
  const presentes = new Set(campos.map((item) => item.tipo));
  const tipos = (ordemTipos || [...presentes].sort()).filter((tipo) => presentes.has(tipo));
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
    const texto = [item.coluna_original, item.nome_apresentacao, item.descricao, item.explicacao, item.tratamento, item.subtipo, item.uso_ml].join(" ").toLowerCase();
    return texto.includes(pesquisa) && (!tipo || item.tipo === tipo) && (!categoria || item.categoria === categoria);
  });
  document.getElementById("contador-dicionario").textContent = `${filtrados.length} de ${campos.length} campos`;
  document.getElementById("estado-vazio-dicionario").style.display = filtrados.length ? "none" : "block";
  document.getElementById("cards-dicionario").innerHTML = criarCardsDicionario(filtrados);
  document.getElementById("tabela-dicionario").innerHTML = filtrados.map((item, indice) => `<tr class="linha-dicionario" data-indice="${indice}"><td><strong>${escaparHtml(item.coluna_original)}</strong></td><td>${escaparHtml(item.nome_apresentacao)}</td><td><span class="etiqueta-tipo">${escaparHtml(item.tipo)}</span><small class="unidade">${escaparHtml(item.subtipo)}</small></td><td><code>${escaparHtml(item.armazenamento)}</code></td><td><span class="etiqueta-classe ${item.uso_ml === "excluída" ? "classe-forte" : item.uso_ml === "alvo" ? "classe-moderada" : "classe-consistente"}">${escaparHtml(item.uso_ml)}</span></td><td><span class="etiqueta-categoria">${escaparHtml(item.categoria)}</span></td><td>${item.ausentes}</td><td><button class="botao-detalhes" type="button" aria-expanded="false">Ver explicação</button><div class="detalhe-campo"><strong>O que significa:</strong> ${escaparHtml(item.explicacao)}<br><strong>Tratamento:</strong> ${escaparHtml(item.tratamento)}<br><strong>Uso em ML:</strong> ${escaparHtml(item.justificativa_ml)}</div></td></tr>`).join("");
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
// Assimetria, CV e IQR
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
      ["Leitura", (l) => `<span class="etiqueta-classe classe-${l.classe.split(" ")[0]}">${escaparHtml(l.classe)}</span>`],
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

  document.getElementById("interpretacao-medida").innerHTML = renderizarSecoes(dados.secoes);

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

// ---------------------------------------------------------------------------
// Comparativo: gráfico em z-score
// ---------------------------------------------------------------------------

async function carregarPerfilZ() {
  const canvas = document.getElementById("grafico-zscore");
  if (!canvas) {
    return;
  }
  const resposta = await fetch("/api/perfil-z");
  const dados = await resposta.json();
  window.perfilZ = dados;
  const labels = dados.variaveis.map((v) => v.variavel);
  const datasets = dados.times.map((time, i) => ({
    type: "bar", label: time, backgroundColor: cores[i], borderRadius: 3,
    data: dados.variaveis.map((v) => v.times[time].z),
  }));
  datasets.push(linhaReferencia("Média dos 149 jogos (z = 0)", 0, labels, "#8998aa"));
  const opcoes = opcoesPadrao({
    titulo: "Médias dos times em z-score (referência: 149 jogos dos dois times)",
    eixoX: "Variável",
    eixoY: "z (desvios padrão em relação à média conjunta)",
    tooltip: { callbacks: { label: (ctx) => {
      const v = dados.variaveis[ctx.dataIndex];
      if (ctx.dataset.type === "line") return `Média conjunta: ${formatar(v.media_referencia)} ${v.unidade} (DP ${formatar(v.desvio_referencia)})`;
      const t = v.times[ctx.dataset.label];
      return `${ctx.dataset.label}: z = ${formatar(t.z)} (média ${formatar(t.media)} ${v.unidade})`;
    } } },
  });
  destruirGrafico("zscore");
  graficos.zscore = new Chart(canvas, { type: "bar", data: { labels, datasets }, options: opcoes });
  document.getElementById("texto-zscore").innerHTML = dados.paragrafos.map((p) => `<p>${escaparHtml(p)}</p>`).join("")
    + dados.metodologia.map((m) => `<p class="nota-metodo"><span>Método</span> ${escaparHtml(m)}</p>`).join("");
}

// ---------------------------------------------------------------------------
// Síntese
// ---------------------------------------------------------------------------

async function carregarSintese() {
  if (!document.querySelector("[data-pagina-sintese]")) {
    return;
  }
  const resposta = await fetch("/api/sintese");
  const dados = await resposta.json();
  preencherTabela("s-quadro",
    [["Variável (unidade)"], ["Time"], ["Média", true], ["Mediana", true], ["DP", true], ["CV (%)", true], ["G1", true], ["Forma"], ["IQR", true], ["Outliers", true], ["z", true]],
    dados.quadro.map((l, i) => ({
      classe: i % dados.times.length === 0 ? "inicio-grupo" : "",
      celulas: [
        i % dados.times.length === 0 ? `<strong>${escaparHtml(l.variavel)}</strong><small class="unidade">${escaparHtml(l.unidade)}</small>` : "",
        escaparHtml(l.time), formatar(l.media), formatar(l.mediana), formatar(l.desvio_padrao),
        `${formatar(l.cv_percentual)} <span class="etiqueta-classe classe-${l.classe_cv.split(" ")[0]}">${escaparHtml(l.classe_cv)}</span>`,
        formatar(l.assimetria), `<span class="etiqueta-classe classe-${l.intensidade_assimetria.split(" ")[0]}">${escaparHtml(l.intensidade_assimetria)}</span>`,
        formatar(l.iqr), l.quantidade_outliers, formatar(l.z),
      ],
    })));
  document.getElementById("interpretacao-sintese").innerHTML = renderizarSecoes(dados.secoes);
}

carregarPerfilZ();
carregarSintese();

// ===========================================================================
// PROJETO 2: NAVEGAÇÃO SEGREGADA E MÓDULOS DE CLUSTERING
// ===========================================================================

function configurarFiltroMenuProjetos() {
  const botoes = document.querySelectorAll(".btn-filtro-proj");
  const menuP1 = document.getElementById("menu-projeto-1");
  const menuP2 = document.getElementById("menu-projeto-2");
  if (!botoes.length || !menuP1 || !menuP2) return;

  function aplicarFiltro(alvo, salvar = true) {
    botoes.forEach((btn) => {
      btn.classList.toggle("ativo", btn.getAttribute("data-alvo") === alvo);
    });

    if (alvo === "p1") {
      menuP1.classList.remove("ocultar-bloco-menu");
      menuP2.classList.add("ocultar-bloco-menu");
    } else if (alvo === "p2") {
      menuP1.classList.add("ocultar-bloco-menu");
      menuP2.classList.remove("ocultar-bloco-menu");
    } else {
      menuP1.classList.remove("ocultar-bloco-menu");
      menuP2.classList.remove("ocultar-bloco-menu");
    }

    if (salvar) {
      try { localStorage.setItem("quadra_filtro_projeto", alvo); } catch (e) {}
    }
  }

  botoes.forEach((btn) => {
    btn.addEventListener("click", () => {
      aplicarFiltro(btn.getAttribute("data-alvo"));
    });
  });

  // Estado inicial inteligente
  let salvo = null;
  try { salvo = localStorage.getItem("quadra_filtro_projeto"); } catch (e) {}

  if (window.location.pathname.startsWith("/projeto2")) {
    aplicarFiltro(salvo === "todos" ? "todos" : "p2", false);
  } else if (salvo) {
    aplicarFiltro(salvo, false);
  }
}

// ---------------------------------------------------------------------------
// Projeto 2 - Parte 1: K-Means Interativo
// ---------------------------------------------------------------------------

let dadosP1Cache = null;

async function carregarProjeto2Parte1() {
  const seletorTime = document.getElementById("seletor-p1-time");
  const seletorK = document.getElementById("seletor-p1-k");
  const seletorVar = document.getElementById("seletor-p1-var");
  if (!seletorTime || !seletorK) return;

  async function atualizar() {
    const time = seletorTime.value;
    const k = seletorK.value;
    const varAtiva = seletorVar ? seletorVar.value : "PTS";

    document.querySelectorAll(".rotulo-var-ativa").forEach((el) => el.textContent = varAtiva);

    const [resP1, resComp] = await Promise.all([
      fetch(`/api/projeto2/parte1?time=${encodeURIComponent(time)}&k=${k}`).then((r) => r.json()),
      fetch(`/api/projeto2/comparar-k?time=${encodeURIComponent(time)}`).then((r) => r.json()),
    ]);
    dadosP1Cache = resP1;

    // 1. Atualizar métricas nos cards
    const elSil = document.getElementById("val-silhueta");
    if (elSil) elSil.textContent = formatar(resP1.score_silhueta, 3);
    const elIne = document.getElementById("val-inercia");
    if (elIne) elIne.textContent = formatar(resP1.inercia, 1);
    const elDb = document.getElementById("val-db");
    if (elDb) elDb.textContent = formatar(resP1.davies_bouldin, 3);
    const elCh = document.getElementById("val-ch");
    if (elCh) elCh.textContent = formatar(resP1.calinski_harabasz, 1);

    // 2. Renderizar Destaques Táticos do Enunciado
    const containerDestaques = document.getElementById("container-destaques-enunciado");
    if (containerDestaques && resP1.destaques_enunciado) {
      const d = resP1.destaques_enunciado;
      const cardsHtml = [
        ["Maior Pontuação", d.maior_pontuacao.cluster, `${formatar(d.maior_pontuacao.valor)} pts`, d.maior_pontuacao.descricao],
        ["Maior Assistências", d.maior_assistencias.cluster, `${formatar(d.maior_assistencias.valor)} ast`, d.maior_assistencias.descricao],
        ["Maior Rebotes", d.maior_rebotes.cluster, `${formatar(d.maior_rebotes.valor)} reb`, d.maior_rebotes.descricao],
        ["Mais Cestas de 3P", d.maior_tres_pontos.cluster, `${formatar(d.maior_tres_pontos.valor)} 3P`, d.maior_tres_pontos.descricao],
        ["Mais Faltas", d.maior_faltas.cluster, `${formatar(d.maior_faltas.valor)} faltas`, d.maior_faltas.descricao],
        ["Características Equilibradas", d.equilibrado.cluster, `${formatar(d.equilibrado.valor)} pts`, d.equilibrado.descricao],
      ];
      containerDestaques.innerHTML = cardsHtml.map((c) => `
        <article class="destaque-tatico-item">
          <div class="rotulo-item">${escaparHtml(c[0])}</div>
          <div class="cluster-nome">${escaparHtml(c[1])}</div>
          <div class="cluster-val">${escaparHtml(c[2])}</div>
          <p class="cluster-desc">${escaparHtml(c[3])}</p>
        </article>
      `).join("");
    }

    // 3. Gráfico 1: Scatter Plot 2D (PCA)
    const elScatter = document.getElementById("grafico-p1-scatter");
    if (elScatter && typeof Chart !== "undefined") {
      destruirGrafico("p1_scatter");
      const datasetsScatter = [];
      const coresClusters = ["#55b6ff", "#ffad66", "#64d9a0", "#b388ff", "#ff7597"];

      resP1.clusters.forEach((c) => {
        const pts = resP1.pontos_scatter.filter((p) => p.cluster === c.id);
        datasetsScatter.push({
          label: `${c.nome}: ${c.destaque}`,
          data: pts.map((p) => ({ x: p.x, y: p.y, pts: p.pts, ast: p.ast, reb: p.reb, time: p.time, data: p.data })),
          backgroundColor: c.cor,
          pointRadius: 5,
          pointHoverRadius: 8,
        });
      });

      // Adicionar centroides destacados
      datasetsScatter.push({
        label: "Centroides (Projetados)",
        data: resP1.centroides_scatter.map((ct) => ({ x: ct.x, y: ct.y })),
        backgroundColor: "#ffffff",
        borderColor: "#ffd166",
        borderWidth: 2,
        pointStyle: "crossRot",
        pointRadius: 10,
        pointHoverRadius: 13,
      });

      graficos.p1_scatter = new Chart(elScatter, {
        type: "scatter",
        data: { datasets: datasetsScatter },
        options: opcoesPadrao({
          titulo: `Projeção 2D das Partidas (PCA: ${resP1.pca_variancia_explicada[0]}% e ${resP1.pca_variancia_explicada[1]}% da variância)`,
          eixoX: "Componente Principal 1 (Ritmo / Produção Ofensiva)",
          eixoY: "Componente Principal 2 (Disputa Física / Garrafão)",
          xLinear: true,
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const p = ctx.raw;
                if (!p.time) return "Centroide de Cluster";
                return `${p.time} (${p.data}): ${formatar(p.pts)} PTS, ${formatar(p.ast)} AST, ${formatar(p.reb)} REB`;
              },
            },
          },
        }),
      });
    }

    // 4. Gráfico 2: Radar Chart
    const elRadar = document.getElementById("grafico-p1-radar");
    if (elRadar && typeof Chart !== "undefined") {
      destruirGrafico("p1_radar");
      graficos.p1_radar = new Chart(elRadar, {
        type: "radar",
        data: resP1.radar,
        options: {
          maintainAspectRatio: false,
          elements: { line: { borderWidth: 2 } },
          scales: {
            r: {
              angleLines: { color: "#263546" },
              grid: { color: "#263546" },
              pointLabels: { color: "#cbd6e1", font: { size: 11, weight: "600" } },
              ticks: { display: false, stepSize: 1 },
            },
          },
          plugins: {
            title: { display: true, text: "Assinatura Tática Normalizada dos Clusters (Z-Score)", color: "#e6edf5", font: { size: 13, weight: "600" } },
            legend: { display: true, labels: { color: "#cbd6e1", usePointStyle: true } },
          },
        },
      });
    }

    // 5. Gráfico 3: BoxPlot por Cluster
    const elBoxplot = document.getElementById("grafico-p1-boxplot");
    if (elBoxplot && typeof Chart !== "undefined" && resP1.boxplots[varAtiva]) {
      destruirGrafico("p1_boxplot");
      const boxData = resP1.boxplots[varAtiva];
      graficos.p1_boxplot = new Chart(elBoxplot, {
        type: "boxplot",
        data: {
          labels: boxData.map((b) => b.cluster_nome),
          datasets: [{
            label: `Distribuição de ${varAtiva}`,
            data: boxData.map((b) => ({
              min: b.min,
              q1: b.q1,
              median: b.mediana,
              q3: b.q3,
              max: b.max,
              outliers: b.outliers,
            })),
            backgroundColor: boxData.map((b) => b.cor + "40"),
            borderColor: boxData.map((b) => b.cor),
            borderWidth: 1.5,
            itemRadius: 3,
          }],
        },
        options: opcoesPadrao({
          titulo: `Boxplot de ${varAtiva} por Cluster`,
          eixoX: "Cluster",
          eixoY: `${varAtiva} (unidade por jogo)`,
        }),
      });
    }

    // 6. Gráfico 4: Histograma por Cluster
    const elHist = document.getElementById("grafico-p1-histograma");
    if (elHist && typeof Chart !== "undefined" && resP1.histogramas[varAtiva]) {
      destruirGrafico("p1_hist");
      const hData = resP1.histogramas[varAtiva];
      graficos.p1_hist = new Chart(elHist, {
        type: "bar",
        data: {
          labels: hData.bins,
          datasets: hData.datasets,
        },
        options: opcoesPadrao({
          titulo: `Distribuição das Partidas por Faixa de ${varAtiva}`,
          eixoX: `${varAtiva} (${hData.unidade})`,
          eixoY: "Número de Partidas",
          beginAtZero: true,
        }),
      });
    }

    // 7. Gráfico 5: Linha de Evolução Temporal
    const elLinha = document.getElementById("grafico-p1-linha");
    if (elLinha && typeof Chart !== "undefined") {
      destruirGrafico("p1_linha");
      const ev = resP1.evolucao_temporal;
      graficos.p1_linha = new Chart(elLinha, {
        type: "line",
        data: {
          labels: ev.rotulos,
          datasets: [
            {
              label: "Cluster Atribuído (0 a K-1)",
              data: ev.clusters_atribuidos.map((c) => c + 1),
              borderColor: "#55b6ff",
              backgroundColor: "#55b6ff20",
              stepped: true,
              yAxisID: "yCluster",
            },
            {
              label: "Pontos (PTS)",
              data: ev.pts,
              borderColor: "#ffad66",
              backgroundColor: "transparent",
              borderDash: [4, 4],
              yAxisID: "yPts",
            },
          ],
        },
        options: {
          maintainAspectRatio: false,
          scales: {
            x: { ticks: { color: "#8998aa", maxTicksLimit: 12 }, grid: { display: false } },
            yCluster: {
              type: "linear",
              position: "left",
              min: 1,
              max: resP1.k,
              ticks: { color: "#55b6ff", stepSize: 1 },
              title: { display: true, text: "Cluster (1 a K)", color: "#55b6ff" },
            },
            yPts: {
              type: "linear",
              position: "right",
              ticks: { color: "#ffad66" },
              grid: { color: "#263546" },
              title: { display: true, text: "PTS (pontos)", color: "#ffad66" },
            },
          },
          plugins: {
            title: { display: true, text: "Evolução Temporal dos Clusters ao Longo da Temporada", color: "#e6edf5", font: { size: 13, weight: "600" } },
            legend: { display: true, labels: { color: "#cbd6e1" } },
          },
        },
      });
    }

    // 8. Gráfico 6: Quantidade de Jogos por Cluster (Barras)
    const elBarras = document.getElementById("grafico-p1-barras");
    if (elBarras && typeof Chart !== "undefined") {
      destruirGrafico("p1_barras");
      const bData = resP1.barras_quantidade;
      graficos.p1_barras = new Chart(elBarras, {
        type: "bar",
        data: {
          labels: bData.labels,
          datasets: [{
            label: "Quantidade de Jogos",
            data: bData.contagens,
            backgroundColor: bData.cores,
            borderRadius: 6,
          }],
        },
        options: opcoesPadrao({
          titulo: "Volume de Jogos por Cluster e Proporção",
          eixoX: "Cluster",
          eixoY: "Jogos Observados (n)",
          beginAtZero: true,
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.parsed.y} partidas (${bData.proporcoes[ctx.dataIndex]}% do total)`,
            },
          },
        }),
      });
    }

    // 9. Gráfico 7: Comparação entre K=2, 3 e 4
    const elCompK = document.getElementById("grafico-p1-comparacao-k");
    if (elCompK && typeof Chart !== "undefined" && resComp.grafico_comparacao) {
      destruirGrafico("p1_comp_k");
      const gK = resComp.grafico_comparacao;
      graficos.p1_comp_k = new Chart(elCompK, {
        type: "bar",
        data: {
          labels: gK.labels,
          datasets: [
            {
              type: "bar",
              label: "Silhouette Score",
              data: gK.silhuetas,
              backgroundColor: "#55b6ff",
              yAxisID: "ySil",
              borderRadius: 4,
            },
            {
              type: "line",
              label: "Inércia (WCSS / 100)",
              data: gK.inercias.map((v) => v / 100),
              borderColor: "#ffad66",
              backgroundColor: "#ffad66",
              yAxisID: "yIne",
              tension: 0.2,
            },
          ],
        },
        options: {
          maintainAspectRatio: false,
          scales: {
            x: { ticks: { color: "#8998aa" }, grid: { display: false } },
            ySil: {
              type: "linear",
              position: "left",
              ticks: { color: "#55b6ff" },
              title: { display: true, text: "Silhouette Score (maior é melhor)", color: "#55b6ff" },
            },
            yIne: {
              type: "linear",
              position: "right",
              ticks: { color: "#ffad66" },
              grid: { color: "#263546" },
              title: { display: true, text: "Inércia / 100 (menor é melhor)", color: "#ffad66" },
            },
          },
          plugins: {
            title: { display: true, text: "Comparação de Métricas de K=2, K=3 e K=4", color: "#e6edf5", font: { size: 13, weight: "600" } },
            legend: { display: true, labels: { color: "#cbd6e1" } },
          },
        },
      });
    }

    // 10. Justificativa de K
    const elJust = document.getElementById("texto-justificativa-k");
    if (elJust && resComp.justificativa_escolha) {
      elJust.innerHTML = `
        <p><strong>Configuração Escolhida: K = ${resComp.k_recomendado}</strong></p>
        <p>${escaparHtml(resComp.justificativa_escolha)}</p>
      `;
    }

    // 11. Tabela Padronizada de Médias por Cluster
    const corpoTabela = document.getElementById("corpo-tabela-medias-clusters");
    if (corpoTabela && resP1.clusters) {
      corpoTabela.innerHTML = resP1.clusters.map((c) => `
        <tr>
          <td><strong style="color: ${c.cor};">${escaparHtml(c.nome)}</strong></td>
          <td>${escaparHtml(c.destaque)}</td>
          <td class="num">${c.contagem} (${c.proporcao}%)</td>
          <td class="num">${formatar(c.medias.PTS)}</td>
          <td class="num">${formatar(c.medias.REB)}</td>
          <td class="num">${formatar(c.medias.AST)}</td>
          <td class="num">${formatar(c.medias.STL)}</td>
          <td class="num">${formatar(c.medias.BLK)}</td>
          <td class="num">${formatar(c.medias.PF)}</td>
          <td class="num">${formatar(c.medias.FG3M)}</td>
        </tr>
      `).join("");
    }
  }

  seletorTime.addEventListener("change", atualizar);
  seletorK.addEventListener("change", atualizar);
  if (seletorVar) seletorVar.addEventListener("change", atualizar);

  atualizar();
}

// ---------------------------------------------------------------------------
// Projeto 2 - Parte 2: Múltiplos Algoritmos
// ---------------------------------------------------------------------------

async function carregarProjeto2Parte2() {
  const seletorAlgo = document.getElementById("seletor-p2-algoritmo");
  const seletorK = document.getElementById("seletor-p2-k");
  if (!seletorAlgo || !seletorK) return;

  async function atualizar() {
    const k = seletorK.value;
    const algoEscolhido = seletorAlgo.value;

    const res = await fetch(`/api/projeto2/parte2?k=${k}`).then((r) => r.json());

    // 1. Tabela comparativa dos 5 algoritmos
    const corpoTabela = document.getElementById("corpo-tabela-algoritmos");
    if (corpoTabela && res.comparativo) {
      corpoTabela.innerHTML = res.comparativo.map((item) => `
        <tr class="${item.algoritmo === algoEscolhido ? 'linha-destacada' : ''}">
          <td><strong>${escaparHtml(item.algoritmo)}</strong></td>
          <td>${escaparHtml(item.paradigma)}</td>
          <td class="num">${item.clusters_identificados}</td>
          <td class="num">${item.ruido_outliers > 0 ? `<span style="color: var(--laranja); font-weight: 700;">${item.ruido_outliers}</span>` : '0'}</td>
          <td class="num"><strong>${formatar(item.silhouette, 4)}</strong></td>
          <td class="num">${formatar(item.davies_bouldin, 4)}</td>
          <td class="num">${formatar(item.calinski_harabasz, 1)}</td>
          <td>${escaparHtml(item.geometria)}</td>
          <td><code>${escaparHtml(item.complexidade)}</code></td>
        </tr>
      `).join("");
    }

    // 2. Gráfico Scatter 2D do algoritmo selecionado
    const elScatter = document.getElementById("grafico-p2-scatter");
    if (elScatter && typeof Chart !== "undefined" && res.scatter[algoEscolhido]) {
      destruirGrafico("p2_scatter");
      const pontos = res.scatter[algoEscolhido];
      const clustersUnicos = [...new Set(pontos.map((p) => p.cluster))].sort((a, b) => a - b);
      const cores = ["#55b6ff", "#ffad66", "#64d9a0", "#b388ff", "#ffd166", "#ff7597"];

      const datasets = clustersUnicos.map((cId) => {
        const sub = pontos.filter((p) => p.cluster === cId);
        const ehRuido = cId === -1;
        return {
          label: ehRuido ? "Ruído / Outlier (DBSCAN)" : `Cluster ${cId + 1}`,
          data: sub.map((p) => ({ x: p.x, y: p.y, pts: p.pts, time: p.time })),
          backgroundColor: ehRuido ? "#ff6b6b" : cores[(cId >= 0 ? cId : 0) % cores.length],
          pointRadius: ehRuido ? 6 : 4.5,
          pointStyle: ehRuido ? "triangle" : "circle",
        };
      });

      const elTitulo = document.getElementById("titulo-scatter-algoritmo");
      if (elTitulo) elTitulo.textContent = `Projeção 2D — ${algoEscolhido}`;

      graficos.p2_scatter = new Chart(elScatter, {
        type: "scatter",
        data: { datasets },
        options: opcoesPadrao({
          titulo: `Agrupamento Resultante: ${algoEscolhido}`,
          eixoX: "Componente Principal 1",
          eixoY: "Componente Principal 2",
          xLinear: true,
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw.time}: ${formatar(ctx.raw.pts)} PTS`,
            },
          },
        }),
      });
    }

    // 3. Gráfico de Barras: Silhouette Score dos 5 Modelos
    const elBarrasSil = document.getElementById("grafico-p2-barras-silhueta");
    if (elBarrasSil && typeof Chart !== "undefined" && res.comparativo) {
      destruirGrafico("p2_barras_sil");
      graficos.p2_barras_sil = new Chart(elBarrasSil, {
        type: "bar",
        data: {
          labels: res.comparativo.map((c) => c.algoritmo),
          datasets: [{
            label: "Silhouette Score (Validação Intrínseca)",
            data: res.comparativo.map((c) => c.silhouette),
            backgroundColor: ["#55b6ff", "#64d9a0", "#ffad66", "#b388ff", "#ffd166"],
            borderRadius: 4,
          }],
        },
        options: opcoesPadrao({
          titulo: "Comparação de Silhouette Score entre os 5 Algoritmos",
          eixoX: "Algoritmo de Clustering",
          eixoY: "Silhouette Score",
          beginAtZero: true,
        }),
      });
    }
  }

  seletorAlgo.addEventListener("change", atualizar);
  seletorK.addEventListener("change", atualizar);

  atualizar();
}

// ---------------------------------------------------------------------------
// Projeto 2 - Parte 3: Análise Global da Liga NBA
// ---------------------------------------------------------------------------

async function carregarProjeto2Parte3() {
  const seletorK = document.getElementById("seletor-p3-k");
  if (!seletorK) return;

  async function atualizar() {
    const k = seletorK.value;
    const res = await fetch(`/api/projeto2/parte3?k=${k}`).then((r) => r.json());

    // 1. Respostas estruturadas às 6 questões do professor
    const containerRespostas = document.getElementById("container-respostas-p3");
    if (containerRespostas && res.perguntas_respostas) {
      containerRespostas.innerHTML = res.perguntas_respostas.map((p) => `
        <article class="cartao-texto">
          <h4>Pergunta ${p.id}: ${escaparHtml(p.pergunta)}</h4>
          <p class="cartao-paragrafo">${escaparHtml(p.resposta)}</p>
          ${p.detalhes.length > 0 ? `
            <ul style="margin: 8px 0; padding-left: 18px; font-size: 11.5px; color: #a0b3c6;">
              ${p.detalhes.map((d) => `<li>${escaparHtml(d)}</li>`).join("")}
            </ul>
          ` : ""}
        </article>
      `).join("");
    }

    // 2. Gráfico 2D das 30 Equipes (PCA)
    const elScatter = document.getElementById("grafico-p3-scatter-times");
    if (elScatter && typeof Chart !== "undefined" && res.scatter_times) {
      destruirGrafico("p3_scatter");
      const cores = ["#55b6ff", "#ffad66", "#64d9a0", "#b388ff", "#ffd166"];
      const clustersUnicos = [...new Set(res.scatter_times.map((p) => p.cluster))].sort((a, b) => a - b);

      const datasets = clustersUnicos.map((cId) => {
        const sub = res.scatter_times.filter((p) => p.cluster === cId);
        return {
          label: `Grupo ${cId + 1}`,
          data: sub.map((p) => ({ x: p.x, y: p.y, time: p.time, pts: p.pts, ast: p.ast, reb: p.reb })),
          backgroundColor: cores[cId % cores.length],
          pointRadius: 6,
          pointHoverRadius: 9,
        };
      });

      graficos.p3_scatter = new Chart(elScatter, {
        type: "scatter",
        data: { datasets },
        options: opcoesPadrao({
          titulo: "Distribuição Multivariada das 30 Equipes da NBA",
          eixoX: "Componente Principal 1 (Eficiência Ofensiva)",
          eixoY: "Componente Principal 2 (Estilo de Jogo / Garrafão)",
          xLinear: true,
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw.time}: ${formatar(ctx.raw.pts)} PTS, ${formatar(ctx.raw.ast)} AST, ${formatar(ctx.raw.reb)} REB`,
            },
          },
        }),
      });
    }

    // 3. Gráfico PTS vs AST das 30 Equipes
    const elPtsAst = document.getElementById("grafico-p3-pts-ast");
    if (elPtsAst && typeof Chart !== "undefined" && res.scatter_times) {
      destruirGrafico("p3_pts_ast");
      graficos.p3_pts_ast = new Chart(elPtsAst, {
        type: "scatter",
        data: {
          datasets: [{
            label: "30 Franquias da NBA",
            data: res.scatter_times.map((t) => ({ x: t.ast, y: t.pts, time: t.time })),
            backgroundColor: "#55b6ff",
            pointRadius: 6,
          }],
        },
        options: opcoesPadrao({
          titulo: "Relação Linear: Assistências vs. Pontos (r = 0,55)",
          eixoX: "Assistências Médias por Jogo (AST)",
          eixoY: "Pontos Médios por Jogo (PTS)",
          xLinear: true,
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw.time}: ${formatar(ctx.raw.x)} AST, ${formatar(ctx.raw.y)} PTS`,
            },
          },
        }),
      });
    }

    // 4. Tabela de Classificação das 30 Equipes
    const corpoTabela = document.getElementById("corpo-tabela-p3-times");
    if (corpoTabela && res.tabela_times) {
      corpoTabela.innerHTML = res.tabela_times.map((t) => `
        <tr>
          <td><strong>${escaparHtml(t.time)}</strong></td>
          <td><span class="etiqueta-categoria">${escaparHtml(t.cluster_nome)}</span></td>
          <td class="num">${formatar(t.pts)}</td>
          <td class="num">${formatar(t.reb)}</td>
          <td class="num">${formatar(t.ast)}</td>
          <td class="num">${formatar(t.stl)}</td>
          <td class="num">${formatar(t.blk)}</td>
          <td class="num">${formatar(t.pf)}</td>
          <td class="num">${formatar(t.fg3m)}</td>
        </tr>
      `).join("");
    }
  }

  seletorK.addEventListener("change", atualizar);
  atualizar();
}

// Inicializações do Projeto 2
configurarFiltroMenuProjetos();
carregarProjeto2Parte1();
carregarProjeto2Parte2();
carregarProjeto2Parte3();
