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
  const time = document.getElementById("seletor-time").value;
  const selecionados = time === "Todos" ? dados.comparativo : dados.por_time;
  const datasets = [];
  Object.entries(selecionados).forEach(([nome, item], indice) => {
    const frequencias = {};
    item.valores.forEach((valor) => { const faixa = Math.round(valor / 5) * 5; frequencias[faixa] = (frequencias[faixa] || 0) + 1; });
    datasets.push({ label: nome, data: Object.entries(frequencias).map(([x, y]) => ({ x: Number(x), y })), backgroundColor: `${cores[indice]}99`, borderColor: cores[indice], borderWidth: 1 });
  });
  const opcoes = opcoesPadrao({
    titulo: `Histograma de ${dados.variavel} por jogo (faixas centradas em múltiplos de 5)`,
    eixoX: `${dados.variavel} (${dados.unidade})`,
    eixoY: "Frequência (nº de jogos)",
    xLinear: true,
    beginAtZero: true,
  });
  opcoes.parsing = false;
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

async function carregarQualidade() {
  if (!document.getElementById("qualidade-conteudo")) {
    return;
  }
  const resposta = await fetch("/api/qualidade"); const dados = await resposta.json();
  const ausentes = dados.campos_ausentes.reduce((total, item) => total + item.quantidade, 0);
  document.getElementById("qualidade-conteudo").innerHTML = `<div class="qualidade-grade"><div class="qualidade-bloco"><h4>Diagnóstico da base</h4><p><strong>${ausentes}</strong> valores ausentes · <strong>${dados.duplicatas}</strong> duplicatas após deduplicação · <strong>${dados.inconsistencias.valores_negativos_nas_variaveis}</strong> valores negativos nas métricas analisadas.</p><p>As datas foram convertidas para data real e percentuais mistos foram normalizados para fração. O dataset final tem 149 jogos dos dois times.</p><h4>Por que os testes de missing não foram aplicados?</h4><p>Little, Jamshidian-Jalal, LS e Fairclough pressupõem campos ausentes. Como não há ausentes no recorte, aplicar esses testes produziria uma conclusão artificial; a ausência foi registrada e a metodologia fica documentada para futuras atualizações.</p></div><div class="qualidade-bloco"><h4>Detectores de valores extremos</h4>${Object.entries(dados.outliers_por_metodo).map(([nome, valor]) => `<div class="metodo"><span>${nome}</span><b>${valor} jogos</b></div>`).join("")}<ul>${dados.metodologia.slice(0, 5).map((texto) => `<li>${texto}</li>`).join("")}</ul></div></div>`;
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
