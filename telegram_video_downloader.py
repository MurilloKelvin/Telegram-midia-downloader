import argparse
import asyncio
import os
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from telethon import TelegramClient, errors, utils


@dataclass(frozen=True)
class Configuracao:
    api_id: int
    api_hash: str
    telefone: str
    canal: str | int
    mensagem_inicial: int
    numero_inicial: int
    pasta_destino: Path
    sessao: Path
    intervalo_downloads: float
    intervalo_tentativas: float
    max_tentativas: int


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa os vídeos de um canal ou grupo do Telegram, do mais "
            "antigo para o mais novo."
        )
    )
    parser.add_argument("--api-id", type=int, help="API ID do Telegram")
    parser.add_argument("--api-hash", help="API Hash do Telegram")
    parser.add_argument("--telefone", help="Telefone com código do país")
    parser.add_argument(
        "--canal", help="Link, @username ou ID do canal/grupo"
    )
    parser.add_argument(
        "--inicio",
        help="Link ou ID da primeira mensagem (padrão: primeira mensagem)",
    )
    parser.add_argument(
        "--numero-inicial",
        type=int,
        default=1,
        help="Número do primeiro arquivo salvo (padrão: 1)",
    )
    parser.add_argument(
        "--destino",
        type=Path,
        default=Path("downloads"),
        help="Pasta de destino (padrão: ./downloads)",
    )
    parser.add_argument(
        "--sessao",
        type=Path,
        default=Path("sessao_telegram"),
        help="Nome/caminho da sessão do Telethon (padrão: sessao_telegram)",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=3,
        help="Segundos entre downloads (padrão: 3)",
    )
    parser.add_argument(
        "--intervalo-tentativas",
        type=float,
        default=5,
        help="Segundos entre novas tentativas (padrão: 5)",
    )
    parser.add_argument(
        "--tentativas",
        type=int,
        default=3,
        help="Máximo de tentativas por vídeo (padrão: 3)",
    )
    return parser


def solicitar_texto(rotulo: str, valor: str | None = None) -> str:
    if valor and valor.strip():
        return valor.strip()

    while True:
        resposta = input(f"{rotulo}: ").strip()
        if resposta:
            return resposta
        print("Este valor é obrigatório.")


def solicitar_api_id(valor: int | None) -> int:
    if valor is not None:
        return valor

    while True:
        try:
            return int(input("API ID: ").strip())
        except ValueError:
            print("Informe um API ID numérico.")


def normalizar_canal(valor: str) -> str | int:
    valor = valor.strip()

    if "://" in valor:
        url = urlparse(valor)
        fragmento = unquote(url.fragment).strip("/")

        if fragmento:
            valor = fragmento
        elif url.scheme == "tg":
            valor = parse_qs(url.query).get("domain", [valor])[0]
        elif url.netloc.lower() in {"t.me", "telegram.me", "www.t.me"}:
            partes = url.path.strip("/").split("/")
            valor = partes[0] if partes else valor

    valor = valor.removeprefix("@").strip()

    if valor.lstrip("-").isdigit():
        return int(valor)
    return valor


def extrair_id_mensagem(valor: str | None) -> int:
    if not valor:
        return 1

    valor = valor.strip()
    if valor.isdigit():
        return int(valor)

    if "://" in valor:
        partes = urlparse(valor).path.strip("/").split("/")
        if partes and partes[-1].isdigit():
            return int(partes[-1])

    raise ValueError(
        "Informe um link de mensagem válido, como "
        "https://t.me/canal/123, ou somente o ID 123."
    )


def validar_argumentos(parser: argparse.ArgumentParser, args) -> None:
    if args.numero_inicial < 1:
        parser.error("--numero-inicial deve ser maior ou igual a 1")
    if args.intervalo < 0 or args.intervalo_tentativas < 0:
        parser.error("os intervalos não podem ser negativos")
    if args.tentativas < 1:
        parser.error("--tentativas deve ser maior ou igual a 1")


def carregar_configuracao() -> Configuracao:
    parser = criar_parser()
    args = parser.parse_args()
    validar_argumentos(parser, args)

    api_id_informado = args.api_id
    if api_id_informado is None and os.environ.get("TELEGRAM_API_ID"):
        try:
            api_id_informado = int(os.environ["TELEGRAM_API_ID"])
        except ValueError:
            parser.error("TELEGRAM_API_ID deve ser numérico")
    api_id = solicitar_api_id(api_id_informado)
    api_hash = args.api_hash or os.environ.get("TELEGRAM_API_HASH")
    if not api_hash:
        api_hash = getpass("API Hash: ").strip()
    if not api_hash:
        parser.error("o API Hash é obrigatório")

    telefone = solicitar_texto(
        "Telefone com código do país (ex.: +5511999999999)",
        args.telefone or os.environ.get("TELEGRAM_PHONE"),
    )
    canal = normalizar_canal(
        solicitar_texto("Link, @username ou ID do canal/grupo", args.canal)
    )

    try:
        mensagem_inicial = extrair_id_mensagem(args.inicio)
    except ValueError as erro:
        parser.error(str(erro))

    return Configuracao(
        api_id=api_id,
        api_hash=api_hash,
        telefone=telefone,
        canal=canal,
        mensagem_inicial=mensagem_inicial,
        numero_inicial=args.numero_inicial,
        pasta_destino=args.destino.expanduser(),
        sessao=args.sessao.expanduser(),
        intervalo_downloads=args.intervalo,
        intervalo_tentativas=args.intervalo_tentativas,
        max_tentativas=args.tentativas,
    )


async def obter_entidade(cliente: TelegramClient, canal: str | int):
    try:
        return await cliente.get_entity(canal)
    except ValueError as erro:
        if not isinstance(canal, int):
            raise

        print("Procurando o ID informado nos canais e grupos da conta...")
        async for dialogo in cliente.iter_dialogs():
            if utils.get_peer_id(dialogo.entity) == canal:
                return dialogo.entity

        raise ValueError(
            "O canal não foi encontrado nesta conta. Confirme se a conta já "
            "entrou no canal e se o link ou ID está correto."
        ) from erro


async def baixar_com_tentativas(
    cliente: TelegramClient,
    mensagem,
    destino: Path,
    config: Configuracao,
) -> bool:
    for tentativa in range(1, config.max_tentativas + 1):
        print(
            f"Tentativa {tentativa}/{config.max_tentativas} para a mensagem "
            f"{mensagem.id}..."
        )

        try:
            await cliente.download_media(mensagem, file=str(destino))
            return True
        except errors.FloodWaitError as erro:
            if tentativa == config.max_tentativas:
                print(f"Falha definitiva por FloodWait: {erro}")
                break

            espera = erro.seconds + 5
            print(f"FloodWait recebido. Aguardando {espera} segundos...")
            await asyncio.sleep(espera)
        except Exception as erro:
            print(f"Falha na tentativa {tentativa}: {erro}")
            if tentativa == config.max_tentativas:
                break

            print(
                f"Nova tentativa em {config.intervalo_tentativas} segundos..."
            )
            await asyncio.sleep(config.intervalo_tentativas)

        if destino.exists():
            destino.unlink()

    return False


async def baixar_videos(config: Configuracao) -> None:
    config.pasta_destino.mkdir(parents=True, exist_ok=True)
    if config.sessao.parent != Path("."):
        config.sessao.parent.mkdir(parents=True, exist_ok=True)

    cliente = TelegramClient(
        str(config.sessao), config.api_id, config.api_hash
    )
    await cliente.start(phone=config.telefone)

    try:
        entidade = await obter_entidade(cliente, config.canal)
        titulo = getattr(entidade, "title", str(config.canal))
        numero_video = config.numero_inicial

        print(f"Canal encontrado: {titulo}")
        print(f"Começando na mensagem {config.mensagem_inicial}...")
        print("Baixando vídeos do mais antigo para o mais novo...")

        async for mensagem in cliente.iter_messages(
            entidade,
            reverse=True,
            min_id=config.mensagem_inicial - 1,
        ):
            if mensagem.video is None:
                continue

            destino = config.pasta_destino / f"{numero_video}.mp4"
            print(
                f"[{numero_video}] Baixando vídeo da mensagem "
                f"{mensagem.id}..."
            )

            if await baixar_com_tentativas(
                cliente, mensagem, destino, config
            ):
                print(f"[{numero_video}] Salvo em {destino}")
                numero_video += 1
            else:
                print(
                    f"Mensagem {mensagem.id} ignorada após "
                    f"{config.max_tentativas} tentativas."
                )

            await asyncio.sleep(config.intervalo_downloads)

        total_salvo = numero_video - config.numero_inicial
        print(f"Download concluído. Total salvo: {total_salvo} vídeo(s).")
    finally:
        await cliente.disconnect()


def main() -> None:
    config = carregar_configuracao()
    try:
        asyncio.run(baixar_videos(config))
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")


if __name__ == "__main__":
    main()
