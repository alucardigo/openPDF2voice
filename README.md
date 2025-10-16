# openPDF2Voice

Aplicação simples em Python para ler arquivos PDF utilizando o modelo de voz aberto [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M). Tudo roda localmente: você escolhe o PDF, o aplicativo gera o áudio com voz em Português do Brasil e toca diretamente na interface.

## Como começar rapidamente

Escolha uma das opções abaixo:

- [Executar localmente](#execução-local)
- [Rodar em container Docker](#execução-com-docker)

O modelo Kokoro é baixado automaticamente na primeira execução, mas você pode antecipar esse passo com `python scripts/download_models.py` (detalhes abaixo).

## Execução local

### 1. Preparar ambiente Python

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou .venv\Scripts\activate no Windows
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. (Opcional) Baixar o modelo antes de abrir a interface

```bash
python scripts/download_models.py
```

O script respeita as variáveis `KOKORO_CACHE_DIR` ou `HF_HOME`. Caso queira salvar os arquivos em outro local, informe `--cache-dir /caminho/dos/modelos`.

### 3. Escolher a interface

#### Interface desktop (Tkinter)

```bash
python app.py
```

> Dica: existe um `Makefile` com alvos `make install`, `make download-models`, `make run` (Tkinter) e `make run-web` (Flask) para automatizar os passos acima.

1. Clique em **Selecionar...** e escolha o PDF desejado.
2. Selecione uma das vozes em Português do Brasil disponíveis.
3. Pressione **Ler** para iniciar. O texto será convertido em áudio e tocado em tempo real.
4. Utilize os botões **Pausar**, **Continuar** e **Parar** para controlar a reprodução.

O áudio é gerado em streaming, bloco a bloco, facilitando a leitura de documentos grandes. A fila de processamento aparece no painel de status.

#### Interface web (Flask)

```bash
python web_app.py --host 0.0.0.0 --port 7860
```

Abra `http://localhost:7860` no navegador para enviar o PDF, escolher a voz e tocar ou baixar o áudio gerado.

Os arquivos WAV gerados ficam em `generated/` (ou no diretório configurado via `GENERATED_DIR`).

## Execução com Docker

Um `Dockerfile` está incluído para facilitar a auto-hospedagem. Ele já instala dependências do sistema, Python e baixa o modelo Kokoro para `/models`. Há também um `docker-compose.yml` pronto para reproduzir a mesma configuração com um único comando.

### Construir a imagem

```bash
docker build -t openpdf2voice .
```

Ou utilize o Docker Compose para construir e executar automaticamente:

```bash
docker compose up --build
```

### Rodar a interface web (recomendado para Docker)

O container inicia a aplicação Flask por padrão. Após subir, acesse `http://localhost:7860` para utilizar a interface web.

```bash
docker run \
  --rm \
  -p 7860:7860 \
  -v "$PWD/models:/models" \
  openpdf2voice
```

### Executar com Docker Compose

```bash
docker compose up
```

O serviço já expõe a porta 7860 e persiste o cache de modelos em `./models`. Use `docker compose build` para apenas construir a imagem e `docker compose down` para encerrar/remover containers.

### Utilizar a interface desktop via Docker (opcional)

Caso ainda deseje abrir a versão Tkinter dentro do container, sobrescreva o comando e compartilhe o X11/áudio manualmente:

```bash
xhost +local:docker || true
docker run \
  --rm \
  --net=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --device /dev/snd \
  -v "$PWD/models:/models" \
  openpdf2voice python app.py
```

No Docker Compose, altere o comando do serviço para `python app.py` e adicione os mapeamentos equivalentes.

### Baixar modelos sem iniciar a UI

```bash
docker run --rm -v "$PWD/models:/models" openpdf2voice python scripts/download_models.py --cache-dir /models
```

## Variáveis de ambiente úteis

- `KOKORO_MODEL`: altera qual repositório/modelo será carregado (padrão: `hexgrad/Kokoro-82M`).
- `KOKORO_CACHE_DIR`: diretório onde os arquivos do modelo serão salvos/consultados.
- `KOKORO_OFFLINE=1`: força modo offline, falhando se os arquivos não estiverem previamente baixados.
- `HF_HOME`: diretório padrão utilizado pelo Hugging Face; é usado como fallback do cache.
- `GENERATED_DIR`: caminho onde a interface web salva os arquivos WAV gerados (padrão: `./generated`).
- `APP_SECRET_KEY`: segredo utilizado pelo Flask para sessões/flash; personalize em produção.

## Modelos e vozes

As vozes pré-configuradas foram retiradas do arquivo [`VOICES.md`](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md), com ênfase em vozes claras e naturais em Português Brasileiro. Você pode acrescentar novas vozes editando o método `_load_voices` em `tts_engine.py`.

## Licença

Este projeto é distribuído sob licença MIT. Consulte o arquivo `LICENSE` para detalhes.
