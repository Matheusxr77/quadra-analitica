const cores = ["#55b6ff", "#ffad66"];
let graficos = {};

function formatar(valor, casas = 2) {
  if (valor === null || valor === undefined) return "—";
  return Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function destruirGrafico(nome) {
  if (graficos[nome]) graficos[nome].destroy();
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
    options: { maintainAspectRatio: false, scales: { x: { ticks: { color: "#8998aa" }, grid: { display: false } }, y: { ticks: { color: "#8998aa" }, grid: { color: "#263546" }, beginAtZero: false } }, plugins: { legend: { labels: { color: "#cbd6e1" } } } },
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
  graficos.boxplot = new Chart(elemento, {
    type: "boxplot",
    data: { labels: Object.keys(selecionados), datasets: [{
      label: dados.variavel,
      backgroundColor: "#55b6ff55",
      borderColor: cores[0],
      outlierColor: "#ff7d7d",
      itemRadius: 2,
      data: Object.values(selecionados).map((item) => ({
        min: item.limite_inferior,
        q1: item.q1,
        median: item.mediana,
        q3: item.q3,
        max: item.limite_superior,
        outliers: item.outliers,
      })),
    }] },
    options: { maintainAspectRatio: false, scales: { x: { ticks: { color: "#8998aa" }, grid: { display: false } }, y: { ticks: { color: "#8998aa" }, grid: { color: "#263546" } } }, plugins: { legend: { labels: { color: "#cbd6e1" } } } },
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
  graficos.histograma = new Chart(elemento, { type: "bar", data: { datasets }, options: { maintainAspectRatio: false, parsing: false, scales: { x: { type: "linear", ticks: { color: "#8998aa" }, title: { display: true, text: "Valor observado", color: "#8998aa" }, grid: { color: "#263546" } }, y: { ticks: { color: "#8998aa" }, title: { display: true, text: "Frequência", color: "#8998aa" }, grid: { color: "#263546" } } }, plugins: { legend: { labels: { color: "#cbd6e1" } } } } });
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
  document.getElementById("texto-interpretacao").innerHTML = `<p><strong>${lider}</strong> apresenta a maior média de ${dados.variavel}, com <strong>${formatar(selecionados[lider].media)}</strong> por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.</p><p>Em regularidade relativa, <strong>${regular}</strong> tem o menor CV (${formatar(selecionados[regular].cv_percentual)}%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.</p><p>A assimetria é <strong>${dados.comparativo[lider].classificacao_assimetria}</strong>. Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.</p>`;
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
