const conversa = document.getElementById('conversa');
const campo = document.getElementById('mensagem');
const statusEnvio = document.getElementById('status');
const token = document.querySelector('meta[name="csrf-token"]').content;
const nome = document.body.dataset.nomeAssistente;
let enviando = false;

function bolha(texto, papel) {
    const elemento = document.createElement('div');
    elemento.className = 'mensagem ' + papel;
    elemento.textContent = texto;
    conversa.appendChild(elemento);
    conversa.scrollTop = conversa.scrollHeight;
    return elemento;
}
async function enviarMensagem(evento) {
    evento.preventDefault();
    const mensagem = campo.value.trim();
    if (!mensagem || enviando) return;
    enviando = true;
    document.getElementById('enviar').disabled = true;
    bolha('Você: ' + mensagem, 'usuario');
    campo.value = '';
    statusEnvio.textContent = 'Preparando resposta…';
    try {
        const resposta = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json', 'X-CSRF-Token':token}, body:JSON.stringify({mensagem, conversa: evento.currentTarget.dataset.conversa || null})});
        if (resposta.status === 401) { window.location.assign('/entrar'); return; }
        const dados = await resposta.json();
        if (!resposta.ok) throw new Error(dados.resposta || 'Não foi possível enviar.');
        if (dados.url_conversa) {
            // The first message gives the draft a permanent URL.
            if (window.location.pathname !== dados.url_conversa) {
                window.location.replace(dados.url_conversa);
                return;
            }
        }
        bolha(dados.resposta, 'gabi');
        statusEnvio.textContent = '';
    } catch (erro) {
        bolha(nome + ': Não consegui concluir o envio. Confira sua conexão e tente novamente.', 'gabi');
        statusEnvio.textContent = erro.message;
        campo.value = mensagem;
    } finally {
        enviando = false;
        document.getElementById('enviar').disabled = false;
        campo.focus();
    }
}
document.getElementById('form-mensagem').addEventListener('submit', enviarMensagem);
conversa.scrollTop = conversa.scrollHeight;
for (const [id, valores, atributo] of [['tema',['claro','escuro'],'tema'], ['tamanho',['normal','grande'],'tamanho'], ['movimento',['ligado','reduzido'],'movimento']]) {
    const seletor = document.getElementById(id);
    try { const salvo = localStorage.getItem('chat-gabi-' + id); if (valores.includes(salvo)) seletor.value = salvo; } catch (_) {}
    document.body.dataset[atributo] = seletor.value;
    seletor.addEventListener('change', () => {
        document.body.dataset[atributo] = seletor.value;
        try { localStorage.setItem('chat-gabi-' + id, seletor.value); } catch (_) {}
    });
}
for (const sugestao of document.querySelectorAll('[data-sugestao]')) {
    sugestao.addEventListener('click', () => {
        campo.value = sugestao.dataset.sugestao;
        campo.focus();
    });
}
