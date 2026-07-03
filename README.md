# ScriptTelegram

[English](#english) | [Português](#português)

## English

Downloads videos from a Telegram channel or group in chronological order.

### Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create your Telegram API credentials at <https://my.telegram.org/apps>.

### Interactive usage

```powershell
python telegram_video_downloader.py
```

The program will ask for your credentials, phone number, and target channel.
By default, files are saved in `./downloads`, starting from the first message.

### Command-line arguments

```powershell
python telegram_video_downloader.py `
  --canal https://t.me/channel_name `
  --inicio 123 `
  --destino D:\Videos `
  --numero-inicial 1
```

Run `python telegram_video_downloader.py --help` to see all available options.
Credentials can also be provided through the `TELEGRAM_API_ID`,
`TELEGRAM_API_HASH`, and `TELEGRAM_PHONE` environment variables.

The generated `.session` file authenticates your Telegram account and must
never be published.

## Português

Baixa vídeos de um canal ou grupo do Telegram, em ordem cronológica.

### Instalação

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Crie suas credenciais em <https://my.telegram.org/apps>.

### Uso interativo

```powershell
python telegram_video_downloader.py
```

O programa solicitará as credenciais, o telefone e o canal. Por padrão, os
arquivos são salvos em `./downloads`, começando pela primeira mensagem.

### Uso com argumentos

```powershell
python telegram_video_downloader.py `
  --canal https://t.me/nome_do_canal `
  --inicio 123 `
  --destino D:\Videos `
  --numero-inicial 1
```

Use `python telegram_video_downloader.py --help` para consultar todas as opções.
As credenciais também podem ser informadas pelas variáveis
`TELEGRAM_API_ID`, `TELEGRAM_API_HASH` e `TELEGRAM_PHONE`.

O arquivo `.session` gerado autentica sua conta e nunca deve ser publicado.
